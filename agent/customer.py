from datetime import datetime
from uuid import uuid4
 
from openai import OpenAI

from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from protocol.a2acontext import A2AContext,A2AResponse
import json
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

def mock_create_propse(desc,price):
    return {
        'desc':desc,
        'price':price
    }

client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
 
    # You can get an ASI:One api key by creating an account at https://asi1.ai/dashboard/api-keys
    api_key='sk_01514396b3c742b3bad785a5e869e87b0da3d0d123fc4849bd57f19bf0075b92',
)
 
NewsAgent = Agent(
    name="A2A Customer Agent",
    port=8000,
    seed="fiducia_seed",
    endpoint=["http://127.0.0.1:8000/submit"],
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
async def query_handler2(ctx: Context, sender: str, msg: A2AContext):
    ctx.logger.info(msg)
    
    msgs = [
                {"role": "system", "content": system_prompt},
                
            ]
    msgs.extend(msg.messages)
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
                     ctx.send(sender,A2AResponse(type='order',content=mock_create_propse(desc,price)))
                     return
                 else:
                     message = arguments['message']
                     ctx.logger.info("The agent tries to consult a merchant agent:")
                     ctx.logger.info(message)
                     ctx.logger.info("Mock return: ")
                     mock_msg = '''
                    I suggest this object's price as 15USD
                    '''
                     ctx.logger.info(mock_msg)
                     msgs.append({"role":'tool','tool_call_id':tool.id,'content':mock_msg})
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

 
# We create a new protocol which is compatible with the chat protocol spec. This ensures
# compatibility between agents
# protocol = Protocol(spec=chat_protocol_spec)
# a2aprotocol = Protocol()
# We define the handler for the chat messages that are sent to your agent
# @agent.on_query(model=A2AContext,replies=A2AResponse)
# async def handle_message(ctx: Context, sender: str, msg: A2AContext):
    
 
 
# @protocol.on_message(ChatAcknowledgement)
# async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
#     # we are not interested in the acknowledgements for this example, but they can be useful to
#     # implement read receipts, for example.
#     print(ctx)
#     print(sender)
#     print(msg)
#     pass
 
 
# attach the protocol to the agent
# agent.include(protocol, publish_manifest=True)
# agent.include(a2aprotocol)
# agent.run()