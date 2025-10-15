from web3 import Web3

# ========== 1. 链接本地节点 ==========
rpc_url = "http://127.0.0.1:8545"
w3 = Web3(Web3.HTTPProvider(rpc_url))


token_address = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")
spender_address = Web3.to_checksum_address("0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")


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

def check_a3a_allowance(sender_address):
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    current_allowance = token_contract.functions.allowance(sender_address, spender_address).call()
    print(f"🔍 Query current allowance: {current_allowance / 1e18} tokens")
    return current_allowance/1e18

def check_a3a_balance(sender_address):
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    current_allowance = token_contract.functions.balanceOf(sender_address).call()
    print(f"🔍 Query current balance: {current_allowance / 1e18} tokens")
    return current_allowance/1e18
def approve_address(wallet_private_key,amount):
    private_key = wallet_private_key
    account = w3.eth.account.from_key(private_key)
    sender = account.address
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)

    amount = amount * 10**18  # 10 

    nonce = w3.eth.get_transaction_count(sender)
    tx = token_contract.functions.approve(spender_address, amount).build_transaction({
        "from": sender,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": w3.to_wei("10", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"✅ Approve hash: {w3.to_hex(tx_hash)}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"🎉 Approve done, block number: {receipt.blockNumber}")

    current_allowance = token_contract.functions.allowance(sender, spender_address).call()
    print(f"🔍 Query current allowance: {current_allowance / 1e18} tokens")

