from datetime import datetime
from uuid import uuid4
from uagents import Agent, Context, Protocol, Model
from uagents_core.contrib.protocols.chat import AgentContent, ChatMessage, ChatAcknowledgement, TextContent
 
AI_AGENT_ADDRESS = "agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up"
 
agent = Agent(
    name="asi-agent",
    seed="hiweihvhieivhwehihiweivbw;ibv;rikbv;erv;rkkbv",
    port=8002,
    endpoint=["http://127.0.0.1:8002/submit"],
)
 
 
@agent.on_event("startup")
async def send_message(ctx: Context):
    await ctx.send(AI_AGENT_ADDRESS, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text="Give me facts about the sun")],
    ))
 
 
@agent.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Got an acknowledgement from {sender} for {msg.acknowledged_msg_id}")
 
 
@agent.on_message(ChatMessage)
async def handle_ack(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"Received request from {sender} for {msg.content[0].text}")
 
agent.run()