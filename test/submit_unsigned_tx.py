import json
import os
from pathlib import Path
from web3 import Web3


def main():
    rpc_url = os.getenv("CONTRACT_URL", "http://127.0.0.1:8545")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    # Load unsigned transaction saved by test/chat.py
    tx_path = Path("unsigned_tx.json")
    if not tx_path.exists():
        print("❌ unsigned_tx.json not found. Run test/chat.py and confirm an order first.")
        return
    with tx_path.open() as f:
        tx = json.load(f)

    # Ensure chainId present
    if "chainId" not in tx or tx["chainId"] in (None, 0):
        try:
            tx["chainId"] = w3.eth.chain_id
        except Exception:
            pass

    # Load signer private key (should match the 'from' in tx)
    priv = os.getenv("PRIVATE_KEY") or os.getenv("TEST_WALLET_PRIVATE_KEYS", "").split(",")[0].strip()
    if not priv:
        print("❌ No PRIVATE_KEY found in environment.")
        return
    acct = w3.eth.account.from_key(priv)

    tx_from = tx.get("from")
    if not tx_from:
        tx["from"] = acct.address
    elif Web3.to_checksum_address(tx_from) != Web3.to_checksum_address(acct.address):
        print(f"⚠️ Tx 'from' {tx_from} does not match signer {acct.address}. Overriding to signer address.")
        tx["from"] = acct.address

    # If nonce missing, fetch for signer
    if "nonce" not in tx:
        tx["nonce"] = w3.eth.get_transaction_count(acct.address)

    # Sign and send
    signed = w3.eth.account.sign_transaction(tx, priv)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"🚀 Sent tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("📜 Receipt:")
    print(json.dumps(dict(receipt), default=lambda o: o.hex() if isinstance(o, (bytes, bytearray)) else str(o), indent=2))


if __name__ == "__main__":
    main()
