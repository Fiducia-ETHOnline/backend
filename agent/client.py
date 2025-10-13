from uagents.query import send_sync_message
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    AgentContent,
    chat_protocol_spec,
)
from uagents import Model
import asyncio
import threading
test_agent_address = "agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up"


class SimpleText(Model):
    msg:str

async def main():
    while True:
        txt = input("Input queries to the agent:")
        res = await send_sync_message(destination=test_agent_address,message=ChatMessage(content=[
            TextContent(txt)
        ]))
        print(res)

asyncio.run(main())