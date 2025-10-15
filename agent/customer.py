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

from agent.protocol.a3acontext import *
import json,os
from blockchain.order_contract import OrderContractManager
from storage.lighthouse import upload_order_desc,CID2Digest
from agent.contract import get_erc20_abi,get_contract_abi
order_contract = OrderContractManager(
    provider_url=os.environ['CONTRACT_URL'],
    order_contract_address=os.environ['AGENT_CONTRACT'],
    pyusd_token_address=os.environ['PYUSD_ADDRESS'],
    order_contract_abi=get_contract_abi(),
    erc20_abi=get_erc20_abi(),
    agent_controller_private_key=os.environ['AGENT_PRIVATE_KEY'],


)

MERCHANT_AGENT_ADDRESS = 'agent1qf9ua6p2gz6nx47emvsf5d9840h7wpfwlcqhsqt4zz0dun8tj43l23jtuch'

order_contract.user_account
system_prompt = '''
You are an agent works as a sales person,
your goal is to help user define their needs of a product, and help them create the order.
A normal process of your job is listed as follow:

1. (optional) introduce yourself
2. ask user their needs
3. help user make their needs more in detail
4. chat with a merchant agent using consult_merchant function to see which merchant has the best match to this result.
4. Finally, You should have:
- detailed description of user's needs
- reasonable price of such a order
5. Then, ask user to confirm this order
6. Call create_propose to create an order

'''

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

async def real_answer_propose(orderid,price)->str:
    resp =await try_send_to_merchant(A3AProposeCtx('',price,'',orderid,''))
    return resp.content
client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
 
    # You can get an ASI:One api key by creating an account at https://asi1.ai/dashboard/api-keys
    api_key='sk_01514396b3c742b3bad785a5e869e87b0da3d0d123fc4849bd57f19bf0075b92',
)
 
A3ACustomerAgent = Agent(
    name="A2A Customer Agent",
    port=8000,
    seed="fiducia_seed",
    endpoint=["http://127.0.0.1:8000/submit"],
    mailbox=True
)
# Registering agent on Almanac and funding it.
# fund_agent_if_low(A3ACustomerAgent.wallet.address())


# On agent startup printing address
@A3ACustomerAgent.on_event("startup")
async def agent_details(ctx: Context):
    ctx.logger.info(f"Search Agent Address is {A3ACustomerAgent.address}")


# On_query handler for news_url request
@A3ACustomerAgent.on_query(model=A3AContext, replies={A3AResponse})
async def query_handler2(ctx: Context, sender: str, msg: A3AContext):
    ctx.logger.info(msg)
    wallet_address=''
    msgs = [
                {"role": "system", "content": system_prompt},
                
            ]
    for item in msg.messages:
        if item['role'] == 'wallet':
            wallet_address = item['content'].lower().strip()
        else:
            msgs.append(item)
    if wallet_address == '':
        await ctx.send(sender,A3AErrorPacket('Cannot find wallet address in this context!'))
        return
    # msgs.extend(msg.messages)
    
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
                    price = arguments['price']
                    try:
                        digest = real_upload_order(wallet_address,desc,price)
                        orderid,txhash = real_create_propose(digest,wallet_address)
                        txhash = await real_answer_propose(orderid,price)
                        transaction = real_confirm_order(orderid,wallet_address)
                    except Exception as e:
                        print(e)
                        await ctx.send(sender,A3AErrorPacket('Fail to create_propose!'))
                        return
                    await ctx.send(sender,A3AResponse(type='order',content=json.dumps(transaction)))
                    return
                 else:
                    message = arguments['message']
                    resp:A3AResponse = await try_send_to_merchant(A3AContext(messages=[{'role':'user','content':message}]))
                    ctx.logger.info(f'From merchant agent:\n{resp}')
                    # ctx.logger.info("The agent tries to consult a merchant agent:")
                    # ctx.logger.info(message)
                    # ctx.logger.info("Mock return: ")
                    # mock_msg = '''
                    # I suggest this object's price as 15USD
                    # '''
                    # ctx.logger.info(mock_msg)
                    msgs.append({"role":'tool','tool_call_id':tool.id,'content':resp.content})
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