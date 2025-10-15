import json
def get_contract_abi():
    with open('blockchain/OrderContract_ABI.json') as f:
        return json.loads(f.read())
    
def get_erc20_abi():
    with open('blockchain/ERC20_ABI.json') as f:
        return json.loads(f.read())