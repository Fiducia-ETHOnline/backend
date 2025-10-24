from datetime import datetime
from uuid import uuid4
 
from openai import OpenAI
from uagents.query import send_sync_message,query

from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from decimal import Decimal

from agent.protocol.a3acontext import *
import json,os
from dotenv import load_dotenv
from blockchain.order_contract import OrderContractManager
from storage.lighthouse import upload_order_desc,CID2Digest,CIDRebuild
from agent.contract import get_erc20_abi,get_contract_abi
from blockchain.utils import is_valid_ethereum_address, to_checksum_address
# Load environment variables from .env
load_dotenv()
from hyperon import MeTTa
from metta.utils import (
    create_metta,
    add_menu_item,
    get_menu_for_merchant,
    get_item_price,
)
from metta.knowledge import initialize_knowledge_graph, seed_merchant_example

order_contract = OrderContractManager(
    provider_url=os.environ['CONTRACT_URL'],
    order_contract_address=os.environ['AGENT_CONTRACT'],
    pyusd_token_address=os.environ['PYUSD_ADDRESS'],
    order_contract_abi=get_contract_abi(),
    erc20_abi=get_erc20_abi(),
    agent_controller_private_key=os.environ['AGENT_PRIVATE_KEY'],


)

MERCHANT_AGENT_ADDRESS = os.getenv(
    'MERCHANT_AGENT_ADDRESS',
    'agent1qf9ua6p2gz6nx47emvsf5d9840h7wpfwlcqhsqt4zz0dun8tj43l23jtuch'
)

# Default merchant scope used when querying the merchant agent for menu/wallet.
# This should match the merchant_id used during admin updates (if any).
DEFAULT_MERCHANT_ID = os.getenv('DEFAULT_MERCHANT_ID', '1')

order_contract.user_account
system_prompt = '''
You are Fiducia, the user's personal assistant, especially handling booking and shopping for the user for now with Web3.
Your goal is to help user define their needs of a product, and help them create the order.
A normal process of your job is listed as follow:

1. (optional) introduce yourself
2. ask user their needs
3. help user make their needs more in detail
4. chat with a merchant agent using consult_merchant function to see which merchant has the best match to this result.
4.1 When you return your result from merchant to user, you need to include the price of the product, the name of the merchant
5. Finally, You should have:
- detailed description of user's needs
- reasonable price of such a order
5. Then, ask user to confirm this order
6. Call create_propose to create an order

'''

create_propose = {
"type": "function",
"function": {
  "name": "create_propose",
  "description": "Create an order proposal. Price should be 2-decimal, a string for the price(just the price, no unit)",
  "parameters": {
    "type": "object",
    "properties": {
        "desc": {"type": "string"},
        "price":{"type":"string"}
      },
      "required": ["desc","price"]
    }
  }
}

consult_merchant = {
"type": "function",
"function": {
  "name": "consult_merchant",
  "description": "chat with the merchant agent ai bot",
  "parameters": {
    "type": "object",
    "properties": {
        "message":{"type":"string"}
      },
      "required": ["message"]
    },

  }
}

a3acustomer_protocol = create_a3a_protocol()
async def try_send_to_merchant(ctx:A3AContext)->A3AResponse:
    resp = await send_sync_message(MERCHANT_AGENT_ADDRESS,ctx,response_type=A3AResponse)
    return resp
def real_upload_order(wallet,desc,price):
    cid = upload_order_desc({
        'wallet':wallet,
        'desc':desc,
        'price':price
    },'buyer-'+wallet)
    digest = CID2Digest(cid)
    return digest

def real_confirm_order(orderid,wallet):
    return order_contract.build_confirm_order(orderid,wallet)


def real_create_propose(hash,wallet):
    return order_contract.propose_order('0x'+hash,wallet)
def real_answer_propose(orderid,price,seller_address):
   return order_contract.propose_order_answer(orderid,'answer from merchant',price,seller_address=seller_address)

_asi_api_key = os.getenv('API_ASI_KEY')
if not _asi_api_key:
    raise RuntimeError("Missing API_ASI_KEY in environment; set it in your .env file.")

client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
    api_key=_asi_api_key,
)
 
# Helper to safely extract content from merchant agent replies
def _safe_content(resp) -> str:
    """Return a string content from various response types.
    Handles objects without .content (e.g., MsgStatus) by falling back to str().
    """
    try:
        c = getattr(resp, 'content', None)
        if c is None:
            return str(resp)
        return str(c)
    except Exception:
        return str(resp)

# ------------------------------
# MeTTa integration (customer-side)
# ------------------------------

# Local MeTTa instance for querying merchant data.
# METTA_INSTANCE: MeTTa | None = create_metta()
# if METTA_INSTANCE is not None:
#     # Initialize base knowledge (optional/neutral)
#     initialize_knowledge_graph(METTA_INSTANCE)
#     # Minimal merchant-facing seed for demo parity with merchant agent
#     seed_merchant_example(METTA_INSTANCE, "TestPizzaAgent")
#     add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "meat_pizza", "15")
#     add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "onion_pizza", "10")
#     add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "pineapple_pizza", "8")
#     add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "cheese_pizza", "12")


# def _lookup_price_from_metta(desc: str, merchant: str = "TestPizzaAgent") -> tuple[str | None, str | None]:
#     """Find a suitable (item, price) from MeTTa given a user-provided description.
#     Strategy: match menu item names that appear in the description (underscore/space-insensitive),
#     else fall back to the cheapest item.
#     """
#     if METTA_INSTANCE is None:
#         return None, None
#     menu = get_menu_for_merchant(METTA_INSTANCE, merchant) or []
#     norm_desc = desc.lower().replace("_", " ")
#     def norm_item(n: str) -> str:
#         return n.replace("_", " ").lower()
#     for item, price in menu:
#         if norm_item(item) in norm_desc:
#             return item, price
#     # Fallback to cheapest
#     if menu:
#         cheapest = min(
#             menu,
#             key=lambda x: float(x[1]) if (x and x[1] is not None) else float("inf"),
#         )
#         return cheapest
#     return None, None
 
A3ACustomerAgent = Agent(
    name="A2A Customer Agent",
    port=8000,
    seed="fiducia_seed",
    endpoint=["http://127.0.0.1:8000/submit"],
    mailbox=True,
    readme_path='agent/customer_readme',
    publish_agent_details=True

)
# Registering agent on Almanac and funding it.
# fund_agent_if_low(A3ACustomerAgent.wallet.address())


# On agent startup printing address
@A3ACustomerAgent.on_event("startup")
async def agent_details(ctx: Context):
    ctx.logger.info(f"Search Agent Address is {A3ACustomerAgent.address}")


# On_query handler for news_url request
@a3acustomer_protocol.on_query(model=A3AContext, replies={A3AResponse})
async def query_handler2(ctx: Context, sender: str, msg: A3AContext):
    ctx.logger.info(msg)
    wallet_address=''
    msgs = [
                {"role": "system", "content": system_prompt},
                
            ]
    # Always fetch the merchant's current menu from merchant agent to ground the model
    try:
        # Scope the menu query to a specific merchant_id so it reflects admin updates
        menu_resp = await try_send_to_merchant(A3AMerchantMenuQuery(DEFAULT_MERCHANT_ID))
        menu_text = _safe_content(menu_resp)
    except Exception:
        menu_text = None

    # Build a single system message as the FIRST message (ASI requires system first)
    system_content = system_prompt
    if menu_text:
        system_content += f"\n\nMerchant menu (live):\n{menu_text}"
    msgs = [
                {"role": "system", "content": system_content},
            ]
    is_merchant = False
    for item in msg.messages:
        if item['role'] == 'wallet':
            wallet_address = item['content'].lower().strip()
        elif item['role'] == 'merchant_wallet':
            wallet_address = item['content'].lower().strip()
            is_merchant = True 
        else:
            msgs.append(item)
    if wallet_address == '':
        await ctx.send(sender,A3AErrorPacket('Cannot find wallet address in this context!'))
        return
    if is_merchant:
        resp:A3AResponse = await try_send_to_merchant(
        A3AContext(messages=[
            # {'role':'agent','content': f'merchant_id:{DEFAULT_MERCHANT_ID}'},
            {'role':'agent','content':msgs[-1]['content']}
        ])
        )
        print('customer -> merchant admin:')
        print(resp)
        ctx.send(sender,A3AResponse(type='chat',content= resp.content))
        return
    # Do NOT append another system message; keep only the first system message per ASI API rules
    
    # msgs.extend(msg.messages)
    try:
      while True:
        r = client.chat.completions.create(
            model="asi1-mini",
            messages=msgs,
            max_tokens=2048,
            tools=[
                create_propose,
                consult_merchant
            ]
        )
        tool_calls = r.choices[0].message.tool_calls
        ctx.logger.warning(r.choices[0].message)
        
        if tool_calls:
            msgs.append(r.choices[0].message)
            for tool in tool_calls:
                 
                 function_name = tool.function.name
                 arguments = json.loads(tool.function.arguments)
                 if function_name == 'create_propose':
                    desc = arguments['desc']
                    # Try to validate/normalize price; if invalid/missing, consult MeTTa
                    item_hint = None
                    # try:
                    price = str(Decimal(arguments['price']).quantize(Decimal('0.01')))
                    # except Exception:
                    #     item_hint, metta_price = _lookup_price_from_metta(desc)
                    #     if metta_price is not None:
                    #         price = str(Decimal(metta_price).quantize(Decimal('0.01')))
                    #     else:
                    #         price = str(Decimal('0').quantize(Decimal('0.01')))

                    try:
                        digest = real_upload_order(wallet_address,desc,price)
                        # Create order (agent signs and emits OrderProposed)
                        orderid, txhash = real_create_propose(digest, wallet_address)
                        # Get merchant payout wallet
                        mw_resp = await try_send_to_merchant(A3AMerchantWalletQuery(DEFAULT_MERCHANT_ID))
                        merchant_wallet = _safe_content(mw_resp).strip()
                        # Validate merchant wallet; fallback to env if invalid
                        if not is_valid_ethereum_address(merchant_wallet):
                            fallback_wallet = os.getenv('MERCHANT_WALLET_ADDRESS', '')
                            if not is_valid_ethereum_address(fallback_wallet):
                                raise ValueError(f"Invalid merchant wallet returned ('{merchant_wallet}') and fallback not set.")
                            merchant_wallet = fallback_wallet
                        merchant_wallet = to_checksum_address(merchant_wallet)
                        # Ensure numeric price for propose_answer
                        price_float = float(str(price))
                        _txhash_ans = real_answer_propose(orderid, price_float, merchant_wallet)
                        transaction = real_confirm_order(orderid, wallet_address)
                    except Exception as e:
                        ctx.logger.exception('Order creation failed')
                        await ctx.send(sender, A3AErrorPacket(f"Order creation failed: {e}"))
                        return
                    await ctx.send(sender,A3AOrderResponse(
                        orderid=orderid,
                        price=price,
                        desc=desc,
                        cid=CIDRebuild(digest),
                        unsigned_transaction=json.dumps(transaction)
                    ))
                    
                    # await ctx.send(sender,A3AResponse(type='order',content=json.dumps(transaction)))
                    return
                 else:
                    message = arguments['message']
                    # Include merchant_id hint so the merchant LLM path is scoped correctly
                    resp:A3AResponse = await try_send_to_merchant(
                        A3AContext(messages=[
                            {'role':'agent','content': f'merchant_id:{DEFAULT_MERCHANT_ID}'},
                            {'role':'user','content':message}
                        ])
                    )
                    ctx.logger.info(f'From merchant agent:\n{resp}')
                    # ctx.logger.info("The agent tries to consult a merchant agent:")
                    # ctx.logger.info(message)
                    # ctx.logger.info("Mock return: ")
                    # mock_msg = '''
                    # I suggest this object's price as 15USD
                    # '''
                    # ctx.logger.info(mock_msg)
                    msgs.append({"role": 'tool', 'tool_call_id': tool.id, 'content': _safe_content(resp)})
        else:
          response = str(r.choices[0].message.content)
          await ctx.send(sender, A3AResponse(type='chat',content=response))
          return
          
    except:
        ctx.logger.exception('Error querying model')
 
    msgs.pop(0)
    # send the response back to the user
    # try:
    #     ctx.logger.info(
    #         f"Fetching news url details for company_name: {msg.company_name}"
    #     )
    #     symbol = await fetch_symbol(msg.company_name)
    #     ctx.logger.info(f" Symbol for company provided is {symbol}")
    #     if symbol is not None:
    #         url_list = await fetch_url(symbol)
    #     else:
    #         url_list = await fetch_url(msg.company_name)
    #     ctx.logger.info(str(url_list))
    #     await ctx.send(sender, UrlResponse(url_list=url_list))
    # except Exception as e:
    #     error_message = f"Error fetching job details: {str(e)}"
    #     ctx.logger.error(error_message)
    #     # Ensure the error message is sent as a string
    #     await ctx.send(sender, ErrorResponse(error=str(error_message)))

A3ACustomerAgent.include(a3acustomer_protocol,publish_manifest=True)