
from web3 import Web3
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
class A3ATokenContract:
    def __init__(self):
        self.token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    
    def check_a3a_allowance(self,sender_address)->float:
        current_allowance = self.token_contract.functions.allowance(sender_address, spender_address).call()
        return current_allowance / 1e18
    def check_a3a_balance(self,sender_address)->float:
        balance = self.token_contract.functions.balanceOf(sender_address).call()
        
        return balance / 1e18