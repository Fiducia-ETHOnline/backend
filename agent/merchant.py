from datetime import datetime
from uuid import uuid4
from storage.lighthouse import upload_order_desc,CID2Digest
from uagents.query import send_sync_message,query

from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from agent.protocol.a3acontext import *
import json,os
from dotenv import load_dotenv
from hyperon import MeTTa
from metta.utils import create_metta, add_menu_item, get_menu_for_merchant

# Global MeTTa instance for merchant knowledge
METTA_INSTANCE: MeTTa | None = create_metta()
from blockchain.order_contract import OrderContractManager

from agent.contract import get_erc20_abi,get_contract_abi
# Load environment variables from .env
load_dotenv()

order_contract = OrderContractManager(
    provider_url=os.environ['CONTRACT_URL'],
    order_contract_address=os.environ['AGENT_CONTRACT'],
    pyusd_token_address=os.environ['PYUSD_ADDRESS'],
    order_contract_abi=get_contract_abi(),
    erc20_abi=get_erc20_abi(),
    # agent_controller_private_key=os.environ['AGENT_PRIVATE_KEY'],
)

a3a_protocol= create_a3a_protocol()

# Merchant wallet (can be configured via env)
MERCHANT_WALLET_ADDRESS = os.getenv(
    'MERCHANT_WALLET_ADDRESS',
    '0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f'
)

system_prompt='''
You are an agent works as a merchant seller:
Customer may chat to you with their needs.
You need:
1. If customer tell you their need, you should check your product list, and find the best match one.
   If no product is matched, just tell the customer no matched product or and suggest a similar product.
   When responding, you should send both the product description and product's price to the customer
2. You should never respond an empty string, even if there is no best match, try to find the most similar one; if no similar one, return some text to indicate the situation and give some suggestion
3. You should ALWAYS include the merchant's name: Test Pizza Agent in EVERY response to user
Here's your product list:

'''


#for backup
'''
1. pizza with meat: 15 USD
2. pizza with onion: 10 USD
3. pizza with pineapple: 8 USD
4. pizza with cheese: 12 USD
5. Other custom pizza is also possible, you can give a reasonable price

'''
# all_goods_list =[
#     {
#         'desc':'''
#         John's Pizza
#         Menu:
#         - Onion-beef pizza: 15 USD
#         - Pineapple-chicken pizza: 15USD
#         - Pork pizza: 10USD
#         - Cheese pizza: 15USD
#         For pizza size:
#         - If you order large size, you have to add extra 5USD
#         Customize:
#         - You can place custom order with reasonable price
        

# '''
#     }
# ]

create_propose = {
"type": "function",
"function": {
  "name": "create_propose",
  "description": "Create an order proposal",
  "parameters": {
    "type": "object",
    "properties": {
        "desc": {"type": "string"},
        "price":{"type":"number"}
      },
      "required": ["desc","price"]
    }
  }
}


_asi_api_key = os.getenv('API_ASI_KEY')
if not _asi_api_key:
    raise RuntimeError("Missing API_ASI_KEY in environment; set it in your .env file.")

client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
    api_key=_asi_api_key,
)
  
A3AMerchantAgent = Agent(
    name="A2A Merchant Agent",
    port=8001,
    seed="fiducia_seed_merchant",
    endpoint=["http://127.0.0.1:8001/submit"],
    mailbox=True,
    readme_path='agent/merchant_readme.md'
)

# Registering agent on Almanac and funding it.
# fund_agent_if_low(A3AMerchantAgent.wallet.address())


# On agent startup printing address
@A3AMerchantAgent.on_event("startup")
async def agent_details(ctx: Context):
    ctx.logger.info(f"Search Agent Address is {A3AMerchantAgent.address}")
    # Seed menu into MeTTa graph (idempotent)
    if METTA_INSTANCE:
        add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "meat_pizza", "15")
        add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "onion_pizza", "10")
        add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "pineapple_pizza", "8")
        add_menu_item(METTA_INSTANCE, "TestPizzaAgent", "cheese_pizza", "12")


# On_query handler for news_url request
@a3a_protocol.on_query(model=A3AContext, replies={A3AResponse})
async def query_handler(ctx: Context, sender: str, msg: A3AContext):
    if msg.messages[-1]['role'] == 'query_wallet':
        await ctx.send(sender,A3AWalletResponse(MERCHANT_WALLET_ADDRESS))
        return
    wallet_address = ''
    menu = get_menu_for_merchant(METTA_INSTANCE, "TestPizzaAgent") if METTA_INSTANCE else []
    new_system_prompt = system_prompt
    if menu:
        new_system_prompt += "\n\nAvailable Menu (via MeTTa):\n" + "\n".join([f"- {i}: ${p}" for i, p in menu])
    msgs = [
                {"role": "system", "content": new_system_prompt},
                
            ]
    for item in msg.messages:
        if item['role'] == 'user' or item['role'] == 'agent': 
            msgs.append(item)

            
    print(msgs)
    try:
      while True:
        r = client.chat.completions.create(
            model="asi1-mini",
            messages=msgs,
            max_tokens=2048,

        )
        print(r)
        tool_calls = r.choices[0].message.tool_calls
        
        response = str(r.choices[0].message.content)
        print(response)

        await ctx.send(sender, A3AResponse(type='chat', content=response))
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


A3AMerchantAgent.include(a3a_protocol)

