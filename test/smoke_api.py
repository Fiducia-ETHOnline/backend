import os
import json
import time
import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct

load_dotenv()
API_BASE = os.getenv('API_BASE', 'http://127.0.0.1:5000')
AUTH_BASE = f'{API_BASE}/api/auth'
MERCHANT_CHAT = f'{API_BASE}/api/merchant/chat/messages'
CUSTOMER_CHAT = f'{API_BASE}/api/chat/messages'

PRIVATE_KEY = os.getenv('PRIVATE_KEY')


def login_with_pk(private_key: str):
    address = Account.from_key(private_key).address
    r = requests.get(f'{AUTH_BASE}/challenge', params={'address': address})
    r.raise_for_status()
    message = r.json()['message']
    nonce = message.split('Nonce:')[1].strip()
    signed = Account.sign_message(encode_defunct(text=nonce), private_key)
    sig = signed.signature.hex()
    r = requests.post(f'{AUTH_BASE}/login', json={'address': address, 'signature': sig})
    r.raise_for_status()
    data = r.json()
    return data['token'], data['user']


def main():
    assert PRIVATE_KEY, 'PRIVATE_KEY not set in .env'
    token, user = login_with_pk(PRIVATE_KEY)
    headers = {'Authorization': f'Bearer {token}'}

    # 1) Merchant chat (user mode)
    r = requests.post(MERCHANT_CHAT, json={
        'messages': [{'role': 'user', 'content': 'Hi, what do you serve?'}]
    }, headers=headers)
    print('Merchant chat (user) status:', r.status_code)
    print('Response:', r.text)

    # 1b) Merchant admin action to trigger verification banner (dev mode allows this)
    r = requests.post(MERCHANT_CHAT, json={
        'messages': [{'role': 'agent', 'content': 'set_desc:Smoke test desc'}]
    }, headers=headers)
    print('Merchant admin (set_desc) status:', r.status_code)
    try:
        data = r.json()
        if isinstance(data, dict) and data.get('type') == 'chat':
            content = data.get('content', '')
            if isinstance(content, str) and 'Merchant verified; managing merchant_id=' in content:
                print('✅ Merchant verification banner present')
            else:
                print('ℹ️ Admin response:', content)
        else:
            print('ℹ️ Admin raw response:', r.text)
    except Exception:
        print('ℹ️ Admin raw response:', r.text)

    # 2) Merchant query_wallet
    r = requests.post(MERCHANT_CHAT, json={
        'messages': [{'role': 'query_wallet', 'content': ''}]
    }, headers=headers)
    print('Merchant query_wallet status:', r.status_code)
    print('Response:', r.text)

    # 3) Customer chat basic
    r = requests.post(CUSTOMER_CHAT, json={
        'messages': [{'role': 'user', 'content': 'I want to order a pizza.'}]
    }, headers=headers)
    print('Customer chat status:', r.status_code)
    print('Response:', r.text)

if __name__ == '__main__':
    main()
