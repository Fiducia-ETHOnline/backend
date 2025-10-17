from blockchain.order_service import OrderContractManager
import asyncio, json, os
from dotenv import load_dotenv

# ========== 🌐 Initialize with your contract ==========
with open('./blockchain/OrderContract_ABI.json') as f:
    abi_dic = json.loads(f.read())
with open('./blockchain/ERC20_ABI.json') as f:
    erc20_abi_dic = json.loads(f.read())

# Load environment variables from .env
load_dotenv()

order_contract = OrderContractManager(
    provider_url=os.getenv('CONTRACT_URL', 'http://127.0.0.1:8545'),
    order_contract_address=os.getenv('AGENT_CONTRACT', ''),
    pyusd_token_address=os.getenv('PYUSD_ADDRESS', ''),
    order_contract_abi=abi_dic,
    erc20_abi=erc20_abi_dic,
    agent_controller_private_key=os.getenv('AGENT_PRIVATE_KEY', ''),
    user_private_key=os.getenv('TEST_USER_PRIVATE_KEY', '')
)

BUYER_ADDRESS = os.getenv('TEST_BUYER_ADDRESS', '0xa0Ee7A142d267C1f36714E4a8F75612F20a79720')
SELLER_ADDRESS = os.getenv('TEST_SELLER_ADDRESS', '0x14dC79964da2C08b23698B3D3cc7Ca32193d9955')


def main():
    print("✅ Successfully connected to local chain!\n")

    print("⚙️  Step 1: Creating propose order...")
    resp = order_contract.propose_order(
        '0x6cd67c9b2a0a41ea04cd258b125e6cf78a69a27fa50943afdf742e36243a2423',
        BUYER_ADDRESS
    )
    orderid = resp[0]
    print(f"📦 New Order Created — ID: {orderid}\n🔗 TxHash: {resp[1]}\n")

    print("🧾 Fetching order details...")
    details = order_contract.get_order_details_by_id(orderid)
    print(details)

    print("💬 Step 2: Seller responding with price offer...")
    resp = order_contract.propose_order_answer(orderid, "Test answer information", 15.0, SELLER_ADDRESS)
    print(f"💡 Response submitted! 🔗 TxHash: {resp}\n")

    print("🧾 Updated order details:")
    details = order_contract.get_order_details_by_id(orderid)
    print(details)

    print(f"📜 Step 3: Fetching all orders for buyer wallet: {BUYER_ADDRESS}")
    user_orders = order_contract.get_user_order_ids(BUYER_ADDRESS)
    print("🗂️  Orders:", user_orders, "\n")

    print("💰 Step 4: Buyer confirming the order...")
    resp = order_contract.confirm_order(orderid, user_address=BUYER_ADDRESS)
    print(f"🚀 Order confirmed! 🔗 TxHash: {resp}\n")

    print("🧾 Final order details:")
    details = order_contract.get_order_details_by_id(orderid)
    print(details)

    print("✅ All steps completed successfully! 🎉")


# if __name__ == "__main__":
main()
