from datetime import datetime
from uuid import uuid4
import os
from dotenv import load_dotenv
from uagents import Agent, Context, Protocol, Model
from uagents_core.contrib.protocols.chat import AgentContent, ChatMessage, ChatAcknowledgement, TextContent
from protocol.a3acontext import A3AContext

# Load environment variables from .env
load_dotenv()

# Address of the target agent (default to Customer Agent)
AI_AGENT_ADDRESS = os.getenv(
    "CUSTOMER_AGENT_ADDRESS",
    "agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up",
)

# Agent seed: unified single env var
AGENT_SEED = os.getenv(
    "AGENT_SEED",
    "hiweihvhieivhwehihiweivbw;ibv;rikbv;erv;rkkbv",
)
 
agent = Agent(
    name="asi-agent",
    seed=AGENT_SEED,
    port=8002,
    endpoint=["http://127.0.0.1:8002/submit"],
)
 
 
@agent.on_event("startup")
async def send_message(ctx: Context):
    await ctx.send(AI_AGENT_ADDRESS, A3AContext(messages= [
{'role':'user','content':'who are you?'}
    ]))
 
 
@agent.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Got an acknowledgement from {sender} for {msg.acknowledged_msg_id}")
 
 
@agent.on_message(A3AContext)
async def handle_ack(ctx: Context, sender: str, msg: A3AContext):
    ctx.logger.info(f"Received request from {sender} for {msg}")
 
agent.run()