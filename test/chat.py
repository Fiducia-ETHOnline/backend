import requests
from utils.authlib import auth_login
from utils.sc_tools import *
import json,os,sys
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

ctx = []
admin_mode = False  # when True, send mutations as role='agent'
auto_sign = os.getenv('CHAT_AUTOSIGN', 'true').lower() == 'true'
TEST_WALLET = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
TEST_WALLET_PRIVATE_KEY = '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d'

#============== This should be done by frontend =======
auth_res= auth_login(TEST_WALLET_PRIVATE_KEY)
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}


# 1. Check the user's wallet has at LEAST 20 A3AToken Allowance AND Balance!
# Remeber, in frontend, before really confirm order, check pyusd balance and allowance!
# resp= requests.post('http://127.0.0.1:5000/api/user/a3atoken/allowance', headers=headers).text
# allowance = float(resp)
# resp= requests.post('http://127.0.0.1:5000/api/user/a3atoken/balance', headers=headers).text
# balance = float(resp)
# print(f'🔍 Your A3AToken allowance: {allowance}')
# print(f'🔍 Your A3AToken balance: {balance}')

# resp= requests.post('http://127.0.0.1:5000/api/user/pyusd/allowance', headers=headers).text
# allowance = float(resp)
# resp= requests.post('http://127.0.0.1:5000/api/user/pyusd/balance', headers=headers).text
# balance = float(resp)
# print(f'🔍 Your PYUSD allowance: {allowance}')
# print(f'🔍 Your PYUSD balance: {balance}')

# if balance<20:
#     print("❌ Fail to do chat! The A3AToken balance is insufficient!")
#     sys.exit(-1)
# if allowance<20:
#     # using ether.js in frontend maybe?
#     # This include private key signature
# approve_address(TEST_WALLET_PRIVATE_KEY,10000)
def _sign_and_send(tx_obj: dict) -> tuple[str, dict]:
    """Sign and broadcast a transaction using PRIVATE_KEY or TEST_WALLET_PRIVATE_KEY; return (tx_hash, receipt_dict)."""
    rpc = os.getenv('CONTRACT_URL', 'http://127.0.0.1:8545')
    w3 = Web3(Web3.HTTPProvider(rpc))
    priv = os.getenv('PRIVATE_KEY') or os.getenv('TEST_WALLET_PRIVATE_KEY')
    if not priv:
        raise RuntimeError('No PRIVATE_KEY or TEST_WALLET_PRIVATE_KEY set for signing')
    acct = w3.eth.account.from_key(priv)
    tx = dict(tx_obj)
    # Ensure from/chainId/nonce
    tx['from'] = acct.address
    if 'chainId' not in tx or not tx['chainId']:
        tx['chainId'] = w3.eth.chain_id
    if 'nonce' not in tx:
        tx['nonce'] = w3.eth.get_transaction_count(acct.address)
    signed = w3.eth.account.sign_transaction(tx, priv)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    # Convert receipt to json-serializable dict
    def _ser(o):
        if isinstance(o, (bytes, bytearray)):
            return o.hex()
        return str(o)
    rdict = {
        'transactionHash': tx_hash.hex(),
        'blockNumber': receipt.blockNumber,
        'status': receipt.status,
        'gasUsed': receipt.gasUsed,
        'from': receipt['from'] if 'from' in receipt else getattr(receipt, 'from', None),
        'to': receipt['to'] if 'to' in receipt else getattr(receipt, 'to', None),
    }
    return tx_hash.hex(), rdict


def to_admin_command(s: str) -> str | None:
    """Map slash commands to agent admin commands. Returns None if not matched."""
    parts = s.strip().split()
    if not parts:
        return None
    if parts[0] == '/set_wallet' and len(parts) == 2:
        return f"set_wallet:{parts[1]}"
    if parts[0] == '/add_item' and len(parts) >= 3:
        name = parts[1]
        price = parts[2]
        return f"add_item:{name}:{price}"
    if parts[0] == '/update_price' and len(parts) >= 3:
        name = parts[1]
        price = parts[2]
        return f"update_price:{name}:{price}"
    if parts[0] == '/remove_item' and len(parts) >= 2:
        name = parts[1]
        return f"remove_item:{name}"
    if parts[0] == '/set_desc' and len(parts) >= 2:
        return f"set_desc:{' '.join(parts[1:])}"
    if parts[0] == '/set_hours' and len(parts) >= 2:
        return f"set_hours:{' '.join(parts[1:])}"
    if parts[0] == '/set_location' and len(parts) >= 2:
        return f"set_location:{' '.join(parts[1:])}"
    if parts[0] == '/set_item_desc' and len(parts) >= 3:
        name = parts[1]
        desc = ' '.join(parts[2:])
        return f"set_item_desc:{name}:{desc}"
    return None

print("Type /admin on to enable admin mode, /admin off to disable. Use slash commands like /set_wallet, /add_item, /update_price, /remove_item, /set_desc, /set_hours, /set_location, /set_item_desc.")
print(f"Auto-sign is {'ON' if auto_sign else 'OFF'} (env CHAT_AUTOSIGN). Use /sign to manually sign the last unsigned_tx.json.")

while True:
    prompt = input("input chat message:").strip()
    # Toggle admin mode or manual sign
    if prompt.lower() == '/admin on':
        admin_mode = True
        print('🔐 Admin mode enabled. Admin commands will be sent as agent-role messages.')
        continue
    if prompt.lower() == '/admin off':
        admin_mode = False
        print('🙍 User mode enabled. Messages will be sent as user-role.')
        continue
    if prompt.lower() == '/sign':
        try:
            with open('unsigned_tx.json', 'r') as f:
                tx_obj = json.load(f)
            tx_hash, receipt = _sign_and_send(tx_obj)
            print(f"🚀 Broadcasted tx: {tx_hash}")
            with open('tx_receipt.json', 'w') as f:
                json.dump(receipt, f, indent=2)
            print('📜 Saved receipt to tx_receipt.json')
        except Exception as e:
            print(f"❌ Signing error: {e}")
        continue

    # If in admin mode and prompt is a slash command, translate to agent message
    if admin_mode and prompt.startswith('/'):
        cmd = to_admin_command(prompt)
        if cmd:
            ctx.append({'role': 'agent', 'content': cmd})
        else:
            print('⚠️ Unknown admin command.');
            continue
    else:
        ctx.append({'role': 'user', 'content': prompt})

    # Route: admin mode → merchant admin endpoint; user mode → customer chat endpoint
    url = 'http://127.0.0.1:5000/api/merchant/chat/messages' if admin_mode else 'http://127.0.0.1:5000/api/chat/messages'
    # Debug info for clarity
    # print(f"Mode={'ADMIN' if admin_mode else 'USER'} → {url}")
    r = requests.post(url, json={'messages':ctx}, headers=headers)
    # Handle non-200s (e.g., 403 when not merchant in admin mode)
    if r.status_code != 200:
        print(f"❌ API error {r.status_code}: {r.text}")
        # Roll back the last ctx entry to avoid polluting the conversation with failed admin/user messages
        if ctx:
            ctx.pop()
        continue
    resp = r.json()
    # Gracefully handle responses without 'type' (e.g., backend detail-only errors)
    if 'type' not in resp:
        print('ℹ️ Response:', resp)
        continue
    msg_type = resp.get('type')
    if msg_type == 'chat':
        print('📋 ' + str(resp.get('content', '')))
        ctx.append({'role': 'assistant', 'content': resp.get('content', '')})
    elif msg_type == 'order':
        print('✅ Order created')
        content = resp.get('content', {})
        try:
            order_id = content.get('orderId')
            price = content.get('price')
            desc = content.get('desc')
            cid = content.get('cid')
            tx_raw = content.get('transaction')
            print(f"Order ID: {order_id}")
            print(f"Description: {desc}")
            print(f"Price: {price}")
            print(f"CID: {cid}")
            # Parse and pretty print unsigned transaction, and save to file for convenience
            tx_obj = None
            if isinstance(tx_raw, str):
                try:
                    tx_obj = json.loads(tx_raw)
                except Exception:
                    tx_obj = tx_raw
            else:
                tx_obj = tx_raw
            print("Unsigned transaction:")
            print(json.dumps(tx_obj, indent=2) if isinstance(tx_obj, dict) else str(tx_obj))
            try:
                with open('unsigned_tx.json', 'w') as f:
                    json.dump(tx_obj, f, indent=2)
                print('💾 Saved unsigned transaction to unsigned_tx.json')
            except Exception as e:
                print(f"⚠️ Could not save unsigned transaction: {e}")
            # Auto-sign and broadcast if enabled
            if auto_sign and isinstance(tx_obj, dict):
                try:
                    tx_hash, receipt = _sign_and_send(tx_obj)
                    print(f"🚀 Broadcasted tx: {tx_hash}")
                    with open('tx_receipt.json', 'w') as f:
                        json.dump(receipt, f, indent=2)
                    print('📜 Saved receipt to tx_receipt.json')
                except Exception as e:
                    print(f"❌ Auto-signing failed: {e}")
        except Exception:
            # Fallback to raw print
            print(content)
    else:
        print('❌')
        print(resp.get('content', ''))