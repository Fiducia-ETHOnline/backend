import requests
from utils.authlib import auth_login
from utils.sc_tools import (
    approve_address,
    approve_pyusd,
    check_a3a_allowance,
    check_a3a_balance,
    check_pyusd_allowance,
    check_pyusd_balance,
)
import json, os, sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Read wallet private keys from env (comma-separated); fallback to common Anvil defaults
env_keys = os.getenv("TEST_WALLET_PRIVATE_KEYS", "").strip()
if env_keys:
    wallet_private_keys = [k.strip() for k in env_keys.split(",") if k.strip()]
else:
    wallet_private_keys = [
        '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
        '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d',
        '0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a',
        '0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6',
        '0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a',
        '0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba',
        '0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e',
        '0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356',
        '0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97',
        '0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6'
    ]

for key in wallet_private_keys:
    print("Approve 10_000 tokens for (A3A + pyUSD): " + key)
    # Approve A3A
    approve_address(key, 10000)
    # Approve pyUSD
    approve_pyusd(key, 10000)
    # Show post-approval balances/allowances
    from_addr = os.getenv("PUBLIC_KEY")
    # If PUBLIC_KEY is not the signer, derive from key
    if not from_addr:
        from web3 import Web3
        from_addr = Web3(Web3.HTTPProvider(os.getenv("CONTRACT_URL", "http://127.0.0.1:8545"))).eth.account.from_key(key).address
    print("-- Summary --")
    try:
        print(f"A3A balance: {check_a3a_balance(from_addr)}; allowance: {check_a3a_allowance(from_addr)}")
        print(f"pyUSD balance: {check_pyusd_balance(from_addr)}; allowance: {check_pyusd_allowance(from_addr)}")
    except Exception as e:
        print(f"⚠️ Post-approval check error: {e}")