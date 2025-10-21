from web3 import Web3
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3.exceptions import BadFunctionCallOutput

# ========== Connect to RPC ==========
load_dotenv()
rpc_url = os.getenv("CONTRACT_URL", "http://127.0.0.1:8545")
w3 = Web3(Web3.HTTPProvider(rpc_url))


def _load_order_contract():
    """Construct a web3 contract for the OrderContract using the local ABI file."""
    order_addr = os.getenv("AGENT_CONTRACT")
    if not order_addr:
        raise RuntimeError("AGENT_CONTRACT not set in environment")
    order_addr = Web3.to_checksum_address(order_addr)
    abi_path = Path(__file__).resolve().parents[2] / "blockchain" / "OrderContract_ABI.json"
    with open(abi_path, "r") as f:
        abi = json.load(f)
    return w3.eth.contract(address=order_addr, abi=abi)


def _resolve_a3a_token_address():
    """Prefer reading A3A token address from the OrderContract; fallback to env if call fails."""
    env_addr = os.getenv("A3ATOKEN_ADDRESS")
    try:
        order = _load_order_contract()
        addr = order.functions.getA3ATokenAddress().call()
        if addr and addr != "0x0000000000000000000000000000000000000000":
            return Web3.to_checksum_address(addr)
    except Exception:
        pass
    if not env_addr:
        raise RuntimeError("A3ATOKEN_ADDRESS not set and could not resolve from OrderContract")
    return Web3.to_checksum_address(env_addr)


def _ensure_contract_code(address: str, label: str):
    code = w3.eth.get_code(address)
    if code in (None, b"", b"0x") or len(code) == 0:
        raise RuntimeError(f"No contract code at {label} address {address}. Check your .env or deployment.")


token_address = _resolve_a3a_token_address()
spender_address = Web3.to_checksum_address(os.getenv("AGENT_CONTRACT", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"))
pyusd_address = Web3.to_checksum_address(os.getenv("PYUSD_ADDRESS", "0x0116686E2291dbd5e317F47faDBFb43B599786Ef"))

_ensure_contract_code(token_address, "A3A token")
_ensure_contract_code(spender_address, "OrderContract")
_ensure_contract_code(pyusd_address, "pyUSD token")


erc20_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
        {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]


def _build_token_contract(address: str):
    return w3.eth.contract(address=address, abi=erc20_abi)


def check_a3a_allowance(sender_address):
    token_contract = _build_token_contract(token_address)
    try:
        current_allowance = token_contract.functions.allowance(sender_address, spender_address).call()
        print(f"🔍 A3A allowance: {current_allowance / 1e18} tokens")
        return current_allowance / 1e18
    except BadFunctionCallOutput as e:
        raise RuntimeError("Failed to read A3A allowance. Is the A3A token deployed at the configured address?") from e


def check_a3a_balance(sender_address):
    token_contract = _build_token_contract(token_address)
    try:
        balance = token_contract.functions.balanceOf(sender_address).call()
        print(f"🔍 A3A balance: {balance / 1e18} tokens")
        return balance / 1e18
    except BadFunctionCallOutput as e:
        raise RuntimeError("Failed to read A3A balance. Is the A3A token deployed at the configured address?") from e


def check_pyusd_allowance(sender_address):
    token_contract = _build_token_contract(pyusd_address)
    try:
        current_allowance = token_contract.functions.allowance(sender_address, spender_address).call()
        print(f"🔍 pyUSD allowance: {current_allowance / 1e18} tokens")
        return current_allowance / 1e18
    except BadFunctionCallOutput as e:
        raise RuntimeError("Failed to read pyUSD allowance. Is the pyUSD token deployed at the configured address?") from e


def check_pyusd_balance(sender_address):
    token_contract = _build_token_contract(pyusd_address)
    try:
        balance = token_contract.functions.balanceOf(sender_address).call()
        print(f"🔍 pyUSD balance: {balance / 1e18} tokens")
        return balance / 1e18
    except BadFunctionCallOutput as e:
        raise RuntimeError("Failed to read pyUSD balance. Is the pyUSD token deployed at the configured address?") from e


def approve_address(wallet_private_key, amount):
    """Approve A3A token allowance for the OrderContract (spender)."""
    private_key = wallet_private_key
    account = w3.eth.account.from_key(private_key)
    sender = account.address
    token_contract = _build_token_contract(token_address)

    amount_wei = int(amount) * 10**18
    nonce = w3.eth.get_transaction_count(sender)
    tx = token_contract.functions.approve(spender_address, amount_wei).build_transaction({
        "from": sender,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": w3.to_wei("10", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"✅ Approve A3A hash: {w3.to_hex(tx_hash)}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"🎉 A3A approve done, block number: {receipt.blockNumber}")

    try:
        current_allowance = token_contract.functions.allowance(sender, spender_address).call()
        print(f"🔍 A3A allowance: {current_allowance / 1e18} tokens")
    except BadFunctionCallOutput:
        print("⚠️ Could not read A3A allowance after approval. Check token address and ABI.")


def approve_pyusd(wallet_private_key, amount):
    """Approve pyUSD token allowance for the OrderContract (spender)."""
    private_key = wallet_private_key
    account = w3.eth.account.from_key(private_key)
    sender = account.address
    token_contract = _build_token_contract(pyusd_address)

    amount_wei = int(amount) * 10**18
    nonce = w3.eth.get_transaction_count(sender)
    tx = token_contract.functions.approve(spender_address, amount_wei).build_transaction({
        "from": sender,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": w3.to_wei("10", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"✅ Approve pyUSD hash: {w3.to_hex(tx_hash)}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"🎉 pyUSD approve done, block number: {receipt.blockNumber}")

    try:
        current_allowance = token_contract.functions.allowance(sender, spender_address).call()
        print(f"🔍 pyUSD allowance: {current_allowance / 1e18} tokens")
    except BadFunctionCallOutput:
        print("⚠️ Could not read pyUSD allowance after approval. Check token address and ABI.")

