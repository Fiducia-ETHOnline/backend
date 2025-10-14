from datetime import datetime
from uuid import uuid4
from storage.lighthouse import upload_order_desc
from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from agent.protocol.a2acontext import A2AContext,A2AResponse,A2AErrorPacket,A2AProposePacket
import json


system_prompt='''
You are an agent works as a sales person,
your goal is to help user define their information of a product, and help them sell this product online
A normal process of your job is listed as follow:

1. (optional) introduce yourself
2. ask user their product
3. help user make their product more in detail
4. Finally, You should have:
- detailed description of user's product
- reasonable price of such a product
5. Then, ask user to confirm this product
6. Call create_propose to create such a product
'''

all_goods_list =[
    {
        'desc':'''
        John's Pizza
        Menu:
        - Onion-beef pizza: 15 USD
        - Pineapple-chicken pizza: 15USD
        - Pork pizza: 10USD
        - Cheese pizza: 15USD
        For pizza size:
        - If you order large size, you have to add extra 5USD
        Customize:
        - You can place custom order with reasonable price
        

'''
    }
]

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

def real_upload_propose(desc:str,price:float,wallet_address:str):
    product_desc = {
        'desc':desc,
        'price':price,
        'owner':wallet_address
    }
    cid = upload_order_desc(product_desc,wallet_address)
    return cid

def real_create_sc(hash)

client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
 
    # You can get an ASI:One api key by creating an account at https://asi1.ai/dashboard/api-keys
    api_key='sk_01514396b3c742b3bad785a5e869e87b0da3d0d123fc4849bd57f19bf0075b92',
)
  
NewsAgent = Agent(
    name="A2A Merchant Agent",
    port=8001,
    seed="fiducia_seed_merchant",
    endpoint=["http://127.0.0.1:8001/submit"],
    mailbox=True
)

# Registering agent on Almanac and funding it.
# fund_agent_if_low(NewsAgent.wallet.address())


# On agent startup printing address
@NewsAgent.on_event("startup")
async def agent_details(ctx: Context):
    ctx.logger.info(f"Search Agent Address is {NewsAgent.address}")


# On_query handler for news_url request
@NewsAgent.on_query(model=A2AContext, replies={A2AResponse})
async def query_handler(ctx: Context, sender: str, msg: A2AContext):
    
    wallet_address = ''
    msgs = [
                {"role": "system", "content": system_prompt},
                
            ]
    for item in msg.messages:
        if item['role'] == 'wallet':
            wallet_address = item['content'].lower().strip()
        else:
            msgs.append(item)
    if wallet_address == '':
        ctx.send(sender,A2AErrorPacket('Cannot find wallet address in this context!'))
        return
    # msgs.extend(msg.messages)
    try:
      while True:
        r = client.chat.completions.create(
            model="asi1-mini",
            messages=msgs,
            max_tokens=2048,
            tools=[
                create_propose
            ]
        )
        tool_calls = r.choices[0].message.tool_calls
        # ctx.logger.warning(r.choices[0].message)
        
        if tool_calls:
            msgs.append(r.choices[0].message)
            for tool in tool_calls:
                 
                 function_name = tool.function.name
                 arguments = json.loads(tool.function.arguments)
                 if function_name == 'create_propose':
                     desc = arguments['desc']
                     price = arguments['price']
                     cid = real_upload_propose(desc,price,wallet_address)
                     ctx.send(sender,A2AProposePacket(desc,price,))
                     return
        else:
          response = str(r.choices[0].message.content)
          await ctx.send(sender, A2AResponse(type='chat',content=response))
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


if __name__ == "__main__":
    NewsAgent.run()

 