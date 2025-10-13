import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


API_BASE = "http://127.0.0.1:5000/api/auth"
PRIVATE_KEY = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" 
def auth_login():
    address = Account.from_key(PRIVATE_KEY).address
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
    signed = Account.sign_message(msg, private_key=PRIVATE_KEY)
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
