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

all_goods_list =[
    {
        
    }
]

 
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
    
    try:
        r = client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": f"""
        You are a helpful assistant 
                """},
                {"role": "user", "content": text},
            ],
            max_tokens=2048,
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