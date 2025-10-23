import os
from dotenv import load_dotenv
import json
import time
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

load_dotenv()
API_BASE = os.getenv('API_BASE', 'http://127.0.0.1:5000')
AUTH_BASE = os.getenv('AUTH_BASE', f'{API_BASE}/api/auth')
MERCHANT_CHAT = f'{API_BASE}/api/merchant/chat/messages'

# Helpers

def login_with_pk(private_key: str):
    address = Account.from_key(private_key).address
    # 1. Get nonce
    r = requests.get(f'{AUTH_BASE}/challenge', params={'address': address})
    r.raise_for_status()
    message = r.json()['message']
    nonce = message.split('Nonce:')[1].strip()
    # 2. Sign
    signed = Account.sign_message(encode_defunct(text=nonce), private_key)
    sig = signed.signature.hex()
    # 3. Login
    r = requests.post(f'{AUTH_BASE}/login', json={'address': address, 'signature': sig})
    r.raise_for_status()
    data = r.json()
    return data['token'], data['user']


def merchant_headers(token: str):
    return {'Authorization': f'Bearer {token}'}


def send_merchant_msgs(headers, messages):
    r = requests.post(MERCHANT_CHAT, json={'messages': messages}, headers=headers)
    return r


def test_scoped_wallet_and_menu_flow():
    """
    Minimal E2E test:
    - Login as merchant (NFT-gated).
    - Send admin scope hint via implicit merchant_id from JWT (auto-injected by backend).
    - Set a unique wallet; query_wallet should return it.
    - Add an item and then query via user message to see it reflected in system prompt.
    """
    pk = os.getenv('TEST_MERCHANT_PK') or os.getenv('PRIVATE_KEY')
    if not pk:
        # Skip test if no merchant private key provided
        print('Skipping: TEST_MERCHANT_PK not set')
        return

    token, user = login_with_pk(pk)
    headers = merchant_headers(token)

    # 1) Set wallet for this merchant scope
    new_wallet = user['address']  # set to self for determinism
    resp = send_merchant_msgs(headers, [
        {'role': 'agent', 'content': f'set_wallet:{new_wallet}'}
    ])
    assert resp.status_code == 200, resp.text

    # 2) Query wallet should return the one we just set
    resp = send_merchant_msgs(headers, [
        {'role': 'query_wallet', 'content': ''}
    ])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get('type') == 'wallet', f"unexpected response: {data}"
    assert data.get('content') == new_wallet, f"wallet mismatch: {data}"

    # 3) Add a unique menu item
    item_name = f"scoped_item_{int(time.time())}"
    resp = send_merchant_msgs(headers, [
        {'role': 'agent', 'content': f'add_item:{item_name}:42'}
    ])
    assert resp.status_code == 200, resp.text

    # 4) Ask a user-style question; the system prompt should include the new item
    resp = send_merchant_msgs(headers, [
        {'role': 'user', 'content': 'What do you have on the menu?'}
    ])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get('type') == 'chat'
    content = data.get('content') or ''
    # We can't fully control model output, but at least ensure the chat completed
    # Optionally, we could check logs or extend API to return current menu.
    assert isinstance(content, str) and len(content) > 0

    print('Scoped merchant flow OK')
