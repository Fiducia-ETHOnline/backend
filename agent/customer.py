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
        "desc": {"type": "str"},
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
        "message":str
      },
      "required": ["message"]
    },

  }
}
client = OpenAI(
    # By default, we are using the ASI:One LLM endpoint and model
    base_url='https://api.asi1.ai/v1',
 
    # You can get an ASI:One api key by creating an account at https://asi1.ai/dashboard/api-keys
    api_key='sk_01514396b3c742b3bad785a5e869e87b0da3d0d123fc4849bd57f19bf0075b92',
)
 
agent = Agent(
    name="ASI-agent",
    seed="fiducia_seed",
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)
 
# We create a new protocol which is compatible with the chat protocol spec. This ensures
# compatibility between agents
protocol = Protocol(spec=chat_protocol_spec)
 
# We define the handler for the chat messages that are sent to your agent
@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(msg)
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )
 
    # collect up all the text chunks
    text = ''
    for item in msg.content:
        if isinstance(item, TextContent):
            
            text += item.text
 
    # query the model based on the user question
    # dialog_context = 
    try:
        r = client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=2048,
            # functions=[
            #     create_propose,
            #     consult_merchant
            # ]
        )
 
        response = str(r.choices[0].message.content)
    except:
        ctx.logger.exception('Error querying model')
 
    # send the response back to the user
    await ctx.send(sender, ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            # we send the contents back in the chat message
            TextContent(type="text", text=response),
            # we also signal that the session is over, this also informs the user that we are not recording any of the
            # previous history of messages.
            EndSessionContent(type="end-session"),
        ]
    ))
 
 
@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    # we are not interested in the acknowledgements for this example, but they can be useful to
    # implement read receipts, for example.
    print(ctx)
    print(sender)
    print(msg)
    pass
 
 
# attach the protocol to the agent
agent.include(protocol, publish_manifest=True)
 
agent.run()