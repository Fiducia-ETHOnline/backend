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
    _normalize_item_name,
)
from metta.storage import (
    merchant_file,
    load_merchant_into,
    append_menu_item as storage_append_menu_item,
    append_price as storage_append_price,
    append_remove_item as storage_append_remove,
    append_wallet as storage_append_wallet,
    append_desc as storage_append_desc,
    append_hours as storage_append_hours,
    append_location as storage_append_location,
    append_item_desc as storage_append_item_desc,
)
from blockchain.merchant_nft import get_wallet_for_merchant_id

# Global MeTTa instance for merchant knowledge (lazy, NFT-gated via admin API)
METTA_INSTANCE: MeTTa | None = None


def _rewrite_wallet_singleton(file_path: str, merchant_label: str, wallet: str) -> None:
    """Ensure only a single merchant-wallet fact exists for this merchant in storage.

    This rewrites the .metta file by removing all existing (merchant-wallet <id> "...")
    lines for the given merchant_label and appending exactly one with the new wallet.
    """
    try:
        # Read all lines
        with open(file_path, 'r') as f:
            lines = f.readlines()
        # Filter out existing wallet lines for this merchant
        prefix = f"(merchant-wallet {merchant_label} "
        filtered = [ln for ln in lines if not ln.strip().startswith(prefix)]
        # Append the new single wallet line
        filtered.append(f'(merchant-wallet {merchant_label} "{wallet}")\n')
        # Write back
        with open(file_path, 'w') as f:
            f.writelines(filtered)
    except Exception:
        # Non-fatal: if rewrite fails, we still set wallet in MeTTa and appended to storage
        # downstream queries will prefer the in-memory value; persistence will be cleaned up later
        pass


def _normalize_admin_command(text: str) -> str:
    """Support slash-style admin commands by mapping them to colon syntax.
    Examples:
      /set_wallet 0xABC        -> set_wallet:0xABC
      /add_item cheese pizza 5 -> add_item:cheese pizza:5
      /update_price cheese pizza 6 -> update_price:cheese pizza:6
      /remove_item cheese pizza    -> remove_item:cheese pizza
      /set_desc Best NY slices -> set_desc:Best NY slices
      /set_hours Mon-Fri 10-22 -> set_hours:Mon-Fri 10-22
      /set_location Brooklyn   -> set_location:Brooklyn
      /set_item_desc cheese pizza Creamy mozz -> set_item_desc:cheese pizza:Creamy mozz
    """
    if not isinstance(text, str):
        return text
    s = text.strip()
    if not s.startswith('/'):
        return s
    s = s[1:].strip()
    parts = s.split()
    if not parts:
        return text
    cmd = parts[0]
    rest = parts[1:]
    if cmd == 'set_wallet' and len(rest) >= 1:
        return f"set_wallet:{rest[0]}"
    if cmd == 'add_item' and len(rest) >= 2:
        price = rest[-1]
        name = ' '.join(rest[:-1])
        return f"add_item:{name}:{price}"
    if cmd == 'update_price' and len(rest) >= 2:
        price = rest[-1]
        name = ' '.join(rest[:-1])
        return f"update_price:{name}:{price}"
    if cmd == 'remove_item' and len(rest) >= 1:
        name = ' '.join(rest)
        return f"remove_item:{name}"
    if cmd == 'set_desc' and len(rest) >= 1:
        return f"set_desc:{' '.join(rest)}"
    if cmd == 'set_hours' and len(rest) >= 1:
        return f"set_hours:{' '.join(rest)}"
    if cmd == 'set_location' and len(rest) >= 1:
        return f"set_location:{' '.join(rest)}"
    if cmd == 'set_item_desc' and len(rest) >= 2:
        name = rest[0]
        desc = ' '.join(rest[1:])
        return f"set_item_desc:{name}:{desc}"
    # Fallback: no mapping; return original without leading slash
    return s

def _ensure_metta_for_admin() -> MeTTa:
    """Create the MeTTa instance on-demand for admin-only mutations.

    Admin access is already NFT-gated at the API layer (only role='merchant' can
    send agent-role messages). We avoid creating any MeTTa state unless an admin
    mutation is performed.
    """
    global METTA_INSTANCE
    if METTA_INSTANCE is None:
        METTA_INSTANCE = create_metta()
    return METTA_INSTANCE

def _ensure_metta_for_read(merchant_label: str) -> MeTTa:
    """Ensure a MeTTa instance exists and is hydrated from storage for this merchant."""
    global METTA_INSTANCE
    if METTA_INSTANCE is None:
        METTA_INSTANCE = create_metta()
    # Load persisted facts (idempotent)
    try:
        load_merchant_into(METTA_INSTANCE, merchant_label)
    except Exception:
        pass
    return METTA_INSTANCE
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
You are the merchant's sales assistant.
Customers will chat to describe what they want. Your job is to:
1. Check the current product list (menu) and pick the best match.
    If nothing matches exactly, say so and suggest the closest option.
    Always include the product name and price in your reply.
2. Never reply with an empty message; if there’s no good match, say that clearly and propose alternatives.
3. Keep responses concise and helpful.

Notes:
- The live menu may be provided separately in the system context as "Available Menu (via MeTTa)".
- If the menu is empty, request more details or suggest nearby options, but do not invent unavailable items.
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
    ctx.logger.info(f"Merchant Agent Address is {A3AMerchantAgent.address}")
    # Do not create or seed MeTTa here. MeTTa is created only when an admin mutation occurs.


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
    # Special cases: queries that bypass LLM
    last_role = msg.messages[-1]['role']
    if last_role == 'query_wallet':
        metta_ro = _ensure_metta_for_read(merchant_label)
        # 1) Try MeTTa-stored wallet
        wallet = get_merchant_wallet(metta_ro, merchant_label)
        # 2) Fallback to NFT owner (merchant_id interpreted as tokenId when numeric)
        if not wallet:
            try:
                if str(merchant_label).isdigit():
                    owner_wallet = get_wallet_for_merchant_id(int(merchant_label))
                else:
                    owner_wallet = None
            except Exception:
                owner_wallet = None
            # No environment fallback by design; return empty if unresolved
            wallet = owner_wallet or ""
        await ctx.send(sender, A3AWalletResponse(wallet))
        return
    if last_role == 'query_menu':
        metta_ro = _ensure_metta_for_read(merchant_label)
        menu = get_menu_for_merchant(metta_ro, merchant_label)
        menu_lines = "\n".join([f"- {i}: ${p}" for i, p in (menu or [])]) if menu else "(no items yet)"
        await ctx.send(sender, A3AMenuResponse(menu_lines))
        return
    if last_role == 'list_menu':
        try:
            with open('metta_store/index.json') as f:
                indexs = json.load(f)['index']
        except Exception as e:
            await ctx.send(sender, A3AMenuResponse('The menu is empty now!'))
            return
        menu_lines = ''
        for k,v in indexs.items():
            metta_ro = _ensure_metta_for_read(k)
            menu = get_menu_for_merchant(metta_ro, k)
            menu_lines+='\nThe following are from merchant_id: '+k+'\n'
            menu_lines+= "\n".join([f"- {i}: ${p}" for i, p in (menu or [])]) if menu else "(no items yet)"
        print(menu_lines)
        await ctx.send(sender, A3AMenuResponse(menu_lines))
        return
        #customer side list menu

    wallet_address = ''
    # Track whether this request performed an admin action (not just a merchant_id hint)
    admin_action_present = False
    # Precompute menu based on current merchant_label
    metta_ro = _ensure_metta_for_read(merchant_label)
    menu = get_menu_for_merchant(metta_ro, merchant_label)
    new_system_prompt = system_prompt
    if menu:
        new_system_prompt += "\n\nAvailable Menu (via MeTTa):\n" + "\n".join([f"- {i}: ${p}" for i, p in menu])
    msgs = [
                {"role": "system", "content": new_system_prompt},
                
            ]
    last_admin_content = None
    print(msg.messages)
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
            print(f'recv admin: {content}')
            # Merchant scoping hint is applied immediately
            if content.startswith('merchant_id:'):
                try:
                    merchant_label = content.split(':', 1)[1].strip() or merchant_label
                    menu = get_menu_for_merchant(METTA_INSTANCE, merchant_label) if METTA_INSTANCE else []
                except Exception:
                    ctx.logger.warning("Failed to apply merchant_id hint")
                continue
            # For admin mutations, only keep the last command for this turn
            last_admin_content = _normalize_admin_command(content)

    # Apply only the latest admin command once per request
    if last_admin_content:
        print('is last time admin:')
    
        metta = _ensure_metta_for_admin()
        content = last_admin_content
        try:
            if content.startswith('set_wallet:'):
                wallet = content.split(':',1)[1].strip()
                set_merchant_wallet(metta, merchant_label, wallet)
                try:
                    mf = merchant_file(merchant_label)
                    storage_append_wallet(mf, merchant_label, wallet)
                    # Ensure only one wallet entry remains for this merchant in the file
                    _rewrite_wallet_singleton(mf, merchant_label, wallet)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('add_item:'):
                _, rest = content.split(':',1)
                name, price = [s.strip() for s in rest.split(':',1)]
                add_menu_item(metta, merchant_label, name, price)
                # Persist: menu + item-display + price
                try:
                    slug = _normalize_item_name(name)
                    storage_append_menu_item(merchant_file(merchant_label), merchant_label, slug, name, price)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('update_price:'):
                _, rest = content.split(':',1)
                name, price = [s.strip() for s in rest.split(':',1)]
                update_item_price(metta, name, price)
                try:
                    slug = _normalize_item_name(name)
                    storage_append_price(merchant_file(merchant_label), slug, price)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('remove_item:'):
                name = content.split(':',1)[1].strip()
                remove_menu_item(metta, merchant_label, name)
                try:
                    slug = _normalize_item_name(name)
                    storage_append_remove(merchant_file(merchant_label), merchant_label, slug)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('set_desc:'):
                desc = content.split(':',1)[1].strip()
                set_merchant_description(metta, merchant_label, desc)
                try:
                    storage_append_desc(merchant_file(merchant_label), merchant_label, desc)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('set_hours:'):
                hours = content.split(':',1)[1].strip()
                set_open_hours(metta, merchant_label, hours)
                try:
                    storage_append_hours(merchant_file(merchant_label), merchant_label, hours)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('set_location:'):
                loc = content.split(':',1)[1].strip()
                set_location(metta, merchant_label, loc)
                try:
                    storage_append_location(merchant_file(merchant_label), merchant_label, loc)
                except Exception:
                    pass
                admin_action_present = True
            elif content.startswith('set_item_desc:'):
                _, rest = content.split(':',1)
                name, desc = [s.strip() for s in rest.split(':',1)]
                set_item_description(metta, name, desc)
                try:
                    slug = _normalize_item_name(name)
                    storage_append_item_desc(merchant_file(merchant_label), slug, desc)
                except Exception:
                    pass
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
                f"Updated settings applied. Merchant {merchant_label} — Here's the current menu:\n{menu_lines}{extras_text}"
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
                    f"Merchant {merchant_label} — Here's our current menu (fallback):\n"
                    f"{items}\n\n"
                    "Tell me what you'd like, and I can help you place an order."
                )
            else:
                fallback_text = (
                    "I'm here to help with orders. I couldn't reach the assistant model just now, "
                    "but you can tell me what you want and I'll try again."
                )
            # if admin_action_present:
            fallback_text = f"Current merchant_id={merchant_label}. " + fallback_text
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

