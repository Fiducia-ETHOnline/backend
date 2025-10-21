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
from metta.utils import (
    create_metta,
    add_menu_item,
    get_menu_for_merchant,
    update_item_price,
    remove_menu_item,
    set_merchant_description,
    set_open_hours,
    set_location,
    set_item_description,
    set_merchant_wallet,
    get_merchant_wallet,
    get_merchant_description,
    get_open_hours,
    get_location,
)

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
    readme_path='agent/merchant_readme',
    publish_agent_details=True
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
    # Merchant identity for scoping MeTTa entries; default fallback name
    merchant_label = "TestPizzaAgent"
    # First pass: scan messages for a merchant_id hint to set scoping before any other handling
    try:
        for m in msg.messages:
            if isinstance(m, dict):
                role = m.get('role')
                content = m.get('content')
                if role in ('agent', 'system') and isinstance(content, str) and content.startswith('merchant_id:'):
                    merchant_label = content.split(':', 1)[1].strip() or merchant_label
    except Exception:
        pass
    # Special case: return configured or MeTTa-stored wallet (after merchant_label resolved)
    if msg.messages[-1]['role'] == 'query_wallet':
        wallet = get_merchant_wallet(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else None
        wallet = wallet or MERCHANT_WALLET_ADDRESS
        await ctx.send(sender, A3AWalletResponse(wallet))
        return
    wallet_address = ''
    # Track whether this request performed an admin action (not just a merchant_id hint)
    admin_action_present = False
    # Precompute menu based on current merchant_label
    menu = get_menu_for_merchant(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else []
    new_system_prompt = system_prompt
    if menu:
        new_system_prompt += "\n\nAvailable Menu (via MeTTa):\n" + "\n".join([f"- {i}: ${p}" for i, p in menu])
    msgs = [
                {"role": "system", "content": new_system_prompt},
                
            ]
    last_admin_content = None
    for item in msg.messages:
        role = item.get('role')
        # Only forward user-facing content to the LLM
        if role == 'user':
            content = item.get('content')
            if not isinstance(content, str):
                content = str(content)
            msgs.append({"role": "user", "content": content})
        # Handle dynamic merchant admin updates via chat messages with 'agent' role conventions
        # Expected formats (simple, human-typed or tool-generated):
        #  - set_wallet:0xABC...
        #  - add_item:cheese_pizza:12
        #  - update_price:cheese_pizza:13
        #  - remove_item:cheese_pizza
        #  - set_desc:Best NY-style thin crust pizza.
        #  - set_hours:Mon–Fri 10–22, Sat–Sun 9–24
        #  - set_location:123 Main St, Anytown
        #  - set_item_desc:cheese_pizza:Creamy mozzarella and rich tomato sauce
        if role == 'agent' and isinstance(item.get('content'), str):
            content = item['content'].strip()
            # Merchant scoping hint is applied immediately
            if content.startswith('merchant_id:'):
                try:
                    merchant_label = content.split(':', 1)[1].strip() or merchant_label
                    menu = get_menu_for_merchant(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else []
                except Exception:
                    ctx.logger.warning("Failed to apply merchant_id hint")
                continue
            # For admin mutations, only keep the last command for this turn
            last_admin_content = content

    # Apply only the latest admin command once per request
    if last_admin_content and METTA_INSTANCE:
        content = last_admin_content
        try:
            if content.startswith('set_wallet:'):
                set_merchant_wallet(METTA_INSTANCE, merchant_label, content.split(':',1)[1].strip())
                admin_action_present = True
            elif content.startswith('add_item:'):
                _, rest = content.split(':',1)
                name, price = [s.strip() for s in rest.split(':',1)]
                add_menu_item(METTA_INSTANCE, merchant_label, name, price)
                admin_action_present = True
            elif content.startswith('update_price:'):
                _, rest = content.split(':',1)
                name, price = [s.strip() for s in rest.split(':',1)]
                update_item_price(METTA_INSTANCE, name, price)
                admin_action_present = True
            elif content.startswith('remove_item:'):
                name = content.split(':',1)[1].strip()
                remove_menu_item(METTA_INSTANCE, merchant_label, name)
                admin_action_present = True
            elif content.startswith('set_desc:'):
                set_merchant_description(METTA_INSTANCE, merchant_label, content.split(':',1)[1].strip())
                admin_action_present = True
            elif content.startswith('set_hours:'):
                set_open_hours(METTA_INSTANCE, merchant_label, content.split(':',1)[1].strip())
                admin_action_present = True
            elif content.startswith('set_location:'):
                set_location(METTA_INSTANCE, merchant_label, content.split(':',1)[1].strip())
                admin_action_present = True
            elif content.startswith('set_item_desc:'):
                _, rest = content.split(':',1)
                name, desc = [s.strip() for s in rest.split(':',1)]
                set_item_description(METTA_INSTANCE, name, desc)
                admin_action_present = True
        except Exception as e:
            ctx.logger.warning(f"Failed to apply admin command '{content}': {e}")

    print(msgs)
    # If this is an admin-only update (no user messages), acknowledge deterministically without calling the LLM
    if admin_action_present and len(msgs) == 1:
        try:
            updated_menu = get_menu_for_merchant(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else []
            menu_lines = "\n".join([f"- {i}: ${p}" for i, p in updated_menu]) if updated_menu else "(no items yet)"
            desc = get_merchant_description(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else None
            hours = get_open_hours(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else None
            loc = get_location(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else None
            extras = []
            if desc:
                extras.append(f"Description: {desc}")
            if hours:
                extras.append(f"Hours: {hours}")
            if loc:
                extras.append(f"Location: {loc}")
            extras_text = ("\n" + "\n".join(extras)) if extras else ""
            ack = (
                f"Merchant verified; managing merchant_id={merchant_label}. "
                f"Updated settings applied. Test Pizza Agent — Here's the current menu:\n{menu_lines}{extras_text}"
            )
            await ctx.send(sender, A3AResponse(type='chat', content=ack))
            return
        except Exception:
            ctx.logger.exception('Error building admin acknowledgement')
            # fall through to model path if something unexpected happens
    try:
        while True:
            r = client.chat.completions.create(
                model="asi1-mini",
                messages=msgs,
                max_tokens=2048,
            )
            print(r)
            # tool_calls = r.choices[0].message.tool_calls  # unused for now
            response = str(r.choices[0].message.content)
            if admin_action_present:
                response = f"Merchant verified; managing merchant_id={merchant_label}. " + response
            print(response)
            await ctx.send(sender, A3AResponse(type='chat', content=response))
            return
    except Exception:
        ctx.logger.exception('Error querying model')
        # Fallback: build a simple response from the known menu to avoid 500s and help the user proceed
        try:
            fallback_menu = get_menu_for_merchant(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else []
            if fallback_menu:
                items = "\n".join([f"- {i}: ${p}" for i, p in fallback_menu])
                fallback_text = (
                    "Test Pizza Agent — Here's our current menu (fallback):\n"
                    f"{items}\n\n"
                    "Tell me what you'd like, and I can help you place an order."
                )
            else:
                fallback_text = (
                    "I'm here to help with orders. I couldn't reach the assistant model just now, "
                    "but you can tell me what you want and I'll try again."
                )
            if admin_action_present:
                fallback_text = f"Merchant verified; managing merchant_id={merchant_label}. " + fallback_text
            await ctx.send(sender, A3AResponse(type='chat', content=fallback_text))
            return
        except Exception:
            pass
 
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

