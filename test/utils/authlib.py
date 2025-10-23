import os
import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


load_dotenv()
# Allow overriding the auth base via env; default to local backend
API_BASE = os.getenv("AUTH_BASE", os.getenv("API_BASE", "http://127.0.0.1:5000")) + "/api/auth"
# PRIVATE_KEY = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" 
def auth_login(private_key):
    address = Account.from_key(private_key).address
    print(f"🪪 Test address: {address}")

    print("\n[1] Get nonce...")
    res = requests.get(f"{API_BASE}/challenge", params={"address": address})
    if res.status_code != 200:
        print("❌ Get nonce Failed:", res.text)
        exit(1)

    nonce = res.json().get("message").split('Nonce:')[1].strip()
    print("✅ Get nonce:", nonce)

    print("\n[2] Sign using nonce...")
    msg = encode_defunct(text=nonce)
    signed = Account.sign_message(msg, private_key=private_key)
    signature = signed.signature.hex()
    print("✅ Signed:", signature)

    print("\n[3] Submit signature verify...")
    res = requests.post(f"{API_BASE}/login", json={
        "address": address,
        "signature": signature
    })
    if res.status_code == 200:
        print("✅ Login Success:", res.json())
    else:
        print("❌ Login Failed:", res.text)
    return res.json()
