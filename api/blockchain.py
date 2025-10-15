from blockchain.order_contract import OrderContractManager
import json,os
def get_contract_abi():
    with open('blockchain/OrderContract_ABI.json') as f:
        return json.loads(f.read())
    
def get_erc20_abi():
    with open('blockchain/ERC20_ABI.json') as f:
        return json.loads(f.read())

backend_ordercontract = OrderContractManager(
    provider_url=os.environ['CONTRACT_URL'],
    order_contract_address=os.environ['AGENT_CONTRACT'],
    pyusd_token_address=os.environ['PYUSD_ADDRESS'],
    order_contract_abi=get_contract_abi(),
    erc20_abi=get_erc20_abi(),
    agent_controller_private_key=os.environ['AGENT_PRIVATE_KEY'],
)
print('Smart Contract Initialized!')
