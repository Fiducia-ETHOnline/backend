import os
import json
import time
import requests
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# Local helpers from existing tests
from utils.authlib import auth_login

load_dotenv()

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:5000")
API = f"{API_BASE}/api"
RPC = os.getenv('CONTRACT_URL', 'http://127.0.0.1:8545')
AUTO_SIGN = os.getenv('AUTO_SIGN', 'true').lower() == 'true'

# Test identities
CUSTOMER_PK = os.getenv('CUSTOMER_PRIVATE_KEY') or os.getenv('TEST_WALLET_PRIVATE_KEY') or '0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba'
MERCHANT_PK = os.getenv('MERCHANT_PRIVATE_KEY')  # optional for admin updates

# Merchant scoping
MERCHANT_ID = os.getenv('MERCHANT_ID')  # optional explicit scoping
SEARCH_QUERY = os.getenv('MERCHANT_QUERY', 'pizza')  # used if MERCHANT_ID not given

# Order intent
ITEM_NAME = os.getenv('ORDER_ITEM', 'pepperoni pizza')
ORDER_PRICE = os.getenv('ORDER_PRICE', '6')  # pyUSD, string for prompt


def _addr_from_pk(pk: str) -> str:
    return Account.from_key(pk).address


def _sign_and_send(tx_obj: dict) -> tuple[str, dict]:
    """Sign and broadcast a transaction using CUSTOMER_PK; return (tx_hash, receipt_dict)."""
    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = w3.eth.account.from_key(CUSTOMER_PK)
    tx = dict(tx_obj)
    tx['from'] = acct.address
    if 'chainId' not in tx or not tx['chainId']:
        tx['chainId'] = w3.eth.chain_id
    if 'nonce' not in tx:
        tx['nonce'] = w3.eth.get_transaction_count(acct.address)
    signed = w3.eth.account.sign_transaction(tx, CUSTOMER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    rdict = {
        'transactionHash': tx_hash.hex(),
        'blockNumber': receipt.blockNumber,
        'status': receipt.status,
        'gasUsed': receipt.gasUsed,
        'from': getattr(receipt, 'from', None) if hasattr(receipt, 'from') else None,
        'to': getattr(receipt, 'to', None) if hasattr(receipt, 'to') else None,
    }
    return tx_hash.hex(), rdict


def _merchant_admin(headers: dict, messages: list[dict]) -> dict:
    url = f"{API}/merchant/chat/messages"
    r = requests.post(url, json={'messages': messages}, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Merchant admin API error {r.status_code}: {r.text}")
    return r.json()


def _customer_chat(headers: dict, messages: list[dict], merchant_id: str | None) -> dict:
    url = f"{API}/chat/messages"
    body = {'messages': messages}
    if merchant_id:
        body['merchantId'] = merchant_id
    r = requests.post(url, json=body, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Customer chat API error {r.status_code}: {r.text}")
    return r.json()


def _get_details(headers: dict, order_id: str) -> dict:
    url = f"{API}/orders/{order_id}/details"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Details error {r.status_code}: {r.text}")
    return r.json()


def _get_profile(headers: dict, merchant_id: str) -> dict:
    url = f"{API}/merchant/{merchant_id}/profile"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Profile error {r.status_code}: {r.text}")
    return r.json()


def _search_merchants(headers: dict, q: str) -> dict:
    url = f"{API}/merchant/search"
    r = requests.get(url, params={'q': q}, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Search error {r.status_code}: {r.text}")
    return r.json()


def main():
    print("=== E2E: dynamic merchant wallet + order flow ===")

    # 1) Optional merchant admin: set wallet/add item
    if MERCHANT_PK and MERCHANT_ID:
        print("[admin] logging in as merchant and ensuring profile/menu...")
        merchant_auth = auth_login(MERCHANT_PK)
        m_headers = {'Authorization': f"Bearer {merchant_auth['token']}"}
        # Inject merchant_id hint by including it as an agent message
        cmds = [
            {'role': 'agent', 'content': f'merchant_id:{MERCHANT_ID}'}
        ]
        mw = os.getenv('MERCHANT_WALLET')
        if mw:
            cmds.append({'role': 'agent', 'content': f"set_wallet:{mw}"})
        cmds.append({'role': 'agent', 'content': f"add_item:{ITEM_NAME}:{ORDER_PRICE}"})
        try:
            resp = _merchant_admin(m_headers, cmds)
            print("[admin] response:", json.dumps(resp, indent=2))
        except Exception as e:
            print(f"[admin] warning: {e}")

    # 2) Customer login
    print("[customer] logging in…")
    cust_auth = auth_login(CUSTOMER_PK)
    headers = {'Authorization': f"Bearer {cust_auth['token']}"}

    # 3) Merchant selection: explicit or search
    merchant_id = MERCHANT_ID
    if not merchant_id:
        print(f"[search] finding merchants for query='{SEARCH_QUERY}'…")
        search = _search_merchants(headers, SEARCH_QUERY)
        results = search.get('results', [])
        if not results:
            raise RuntimeError("No merchants found via search; set MERCHANT_ID or adjust MERCHANT_QUERY")
        # pick the first candidate
        merchant_id = str(results[0].get('merchant_id') or results[0].get('id') or results[0])
        print(f"[search] selected merchant_id={merchant_id}")

    # 4) Read profile and expected seller wallet
    print(f"[profile] fetching merchant profile for id={merchant_id}…")
    profile = _get_profile(headers, merchant_id)
    expected_wallet = (profile.get('wallet') or '').lower()
    print("[profile] wallet:", expected_wallet)
    # If requested item isn't on the menu, automatically pick the first available item
    try:
        menu = profile.get('menu') or []
        names = {str(i.get('name', '')).strip().lower(): str(i.get('price', '')).strip() for i in menu}
        req_name_l = str(ITEM_NAME).strip().lower()
        chosen_name = ITEM_NAME
        chosen_price = ORDER_PRICE
        if names and req_name_l not in names:
            first_name = next(iter(names.keys()))
            chosen_name = first_name
            chosen_price = names[first_name]
            print(f"[profile] requested item not found; switching to menu item '{chosen_name}' at {chosen_price} pyUSD")
    except Exception:
        chosen_name = ITEM_NAME
        chosen_price = ORDER_PRICE

    # 5) Ask to order an item; pass merchantId for deterministic scoping
    print("[order] requesting an order via chat…")
    ctx = [
        {'role': 'user', 'content': f"I'd like to order a {chosen_name} for {chosen_price} pyUSD."}
    ]
    resp = _customer_chat(headers, ctx, merchant_id)

    # The agent should return either a chat or an order; handle both
    if resp.get('type') == 'chat':
        print('[chat] assistant:', resp.get('content'))
        # Try one more message to encourage order creation
        ctx.append({'role': 'assistant', 'content': resp.get('content', '')})
        ctx.append({'role': 'user', 'content': f"Please create the order now for {chosen_price} pyUSD."})
        resp = _customer_chat(headers, ctx, merchant_id)

    if resp.get('type') != 'order':
        print('⚠️ Did not receive an order from agent. Full response:')
        print(json.dumps(resp, indent=2))
        return

    content = resp.get('content', {})
    order_id = content.get('orderId')
    price = content.get('price')
    tx_raw = content.get('transaction')

    print(f"[order] orderId={order_id}, price={price}")

    # Parse unsigned transaction
    tx_obj = None
    if isinstance(tx_raw, str):
        try:
            tx_obj = json.loads(tx_raw)
        except Exception:
            tx_obj = tx_raw
    else:
        tx_obj = tx_raw

    if isinstance(tx_obj, dict):
        with open('unsigned_tx.json', 'w') as f:
            json.dump(tx_obj, f, indent=2)
        print('[order] saved unsigned_tx.json')

    # Optionally sign & broadcast
    if AUTO_SIGN and isinstance(tx_obj, dict):
        try:
            tx_hash, receipt = _sign_and_send(tx_obj)
            with open('tx_receipt.json', 'w') as f:
                json.dump(receipt, f, indent=2)
            print(f"[tx] broadcasted: {tx_hash}")
        except Exception as e:
            print(f"[tx] signing failed: {e}")

    # 6) Verify on-chain details
    print("[verify] fetching on-chain order details…")
    details = _get_details(headers, order_id)
    print(json.dumps(details, indent=2))

    # Check seller vs expected wallet when available
    seller = (details.get('seller') or '').lower()
    if expected_wallet:
        if seller == expected_wallet:
            print('✅ Seller wallet matches merchant profile wallet')
        else:
            print('❌ Seller wallet DOES NOT match profile wallet')
            print('expected:', expected_wallet)
            print('actual  :', seller)
    else:
        print('ℹ️ No wallet in profile; seller likely resolved from NFT ownerOf')

    print('🎉 E2E flow completed')


if __name__ == '__main__':
    main()
