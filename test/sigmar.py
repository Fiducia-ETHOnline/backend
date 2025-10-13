from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from datetime import datetime
from uuid import uuid4
class RawMessage(Model):
    content: str
 
sigmar = Agent(name="sigmar", seed="sigmar recovery phrase", port=8000, endpoint=["http://localhost:8000/submit"])
SLAANESH_ADDRESS = 'agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up'
 
@sigmar.on_interval(period=10.0)
async def send_message(ctx: Context):
    await ctx.send(SLAANESH_ADDRESS, RawMessage(content='what is the whether in NewYork?'))
 
@sigmar.on_message(model=RawMessage)
async def sigmar_message_handler(ctx: Context, sender: str, msg: RawMessage):
    ctx.logger.info(f"Received message from {sender}: {msg.content}")
 
if __name__ == "__main__":
    sigmar.run()