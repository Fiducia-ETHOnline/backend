🍕 Merchant Menu & Quote Agent
This agent helps shoppers discover items and get real prices from a specific merchant. It reads a live, admin-managed menu (via MeTTa) and responds with clear suggestions and prices. Merchants can update their menu and wallet via simple chat commands (admin-only), and the changes take effect immediately.

Below is practical guidance for end users and merchants—no technical jargon required.

✅ Things the Agent Can Do
- Show the current menu with item names and prices
- Recommend the best match within a budget
- Suggest alternatives if the exact item isn’t available
- Return concise, human-friendly replies (name + price) for quick decisions

❌ Things the Agent Will Not Do
- Take payments or finalize orders (that happens via the Customer Agent + smart contract)
- Create or seed menu items automatically (admins must add them)
- Manage delivery or post-purchase logistics

🧪 Example Prompts (User)
- “What do you serve?” → Lists available items and prices
- “Do you have cheese pizza under $6?” → Suggests matching or closest option with prices
- “Recommend something cheap” → Suggests a budget-friendly item with price

🧪 Example Prompts (Merchant Admin)
- “set_wallet:0xABC…” → Sets payout wallet
- “add_item:cheese pizza:5” → Adds a multi‑word item with price
- “update_price:cheese pizza:6” → Changes price
- “remove_item:cheese pizza” → Removes item from visible menu

🗺 Coverage
- Works for one merchant at a time based on a merchant_id hint
- Multiple merchants are supported; each has separate menu/wallet data

ℹ️ Tips for Best Results
- Use plain language: “cheese pizza 5” is stored and displayed exactly as written
- Items can be multi‑word; the system saves a friendly display name and a safe internal slug
- Ask for the “menu” or use a budget phrase like “under $10” to get targeted suggestions

🔁 Follow‑up Queries
- “Show the full menu”
- “Anything around $8?”
- “Any vegetarian options?”

🧾 What You’ll Get
Test Pizza – Here’s our menu:
- cheese pizza: $5
- pineapple pizza: $8

Tell me what you’d like and I’ll suggest the best match.

—

# Technical details (for developers)

## Overview
The Merchant Agent represents the seller side of the marketplace. It receives customer intents, matches inventory, provides quotes, and answers proposals on-chain through the OrderContract. It also coordinates fulfillment updates.

## Capabilities
- Interpret customer needs and map to products
- Price recommendation and quoting
- Respond to order proposals (`propose_order_answer`)
- Coordinate fulfillment and status updates
- Dynamic MeTTa-backed merchant data (menu, prices, metadata, wallet)

## Protocols
- ChatProtocol (uAgents chat) for back-and-forth with Customer Agent
- A3AContext protocol for structured requests/responses

## Environment
Ensure the following variables are set (see `.env.example`):
- CONTRACT_URL
- AGENT_CONTRACT
- PYUSD_ADDRESS
- AGENT_PRIVATE_KEY

## How it works
1. Processes incoming customer messages
2. Matches to catalog and suggests best option
3. Calls `propose_order_answer(order_id, details, price)`
4. Sends fulfillment and tracking updates post-confirmation

## Run locally
1. Install requirements: `pip install -r requirements.txt`
2. Start backend: `python app.py`
3. Start Merchant Agent: `python start_merchant.py`

## Dynamic merchant updates (admin commands)

This agent supports lightweight admin commands to mutate merchant data in MeTTa at runtime. To prevent accidental edits, the agent only processes these when the incoming message has `role == "agent"`.

Recommended UX patterns:
- Provide an Admin/User toggle in your UI for authenticated merchants.
- Or support slash commands like `/admin on` to send subsequent messages as agent-role.

Accepted admin commands (sent as plain text when role==agent):
- `set_wallet:0xYourMerchantAddress`
- `add_item:<name>:<price>`
- `update_price:<name>:<new_price>`
- `remove_item:<name>`
- `set_desc:<text>`
- `set_hours:<text>`
- `set_location:<text>`
- `set_item_desc:<name>:<text>`

Command grammar notes:
- Names can be multi-word. The system stores a normalized slug internally, but displays the original name to users.
- Price is a number and should be the final field.

Example slash mapping (UI → agent message):
- `/set_wallet 0xABC...` → `set_wallet:0xABC...`
- `/add_item cheese pizza 12` → `add_item:cheese pizza:12`
- `/update_price cheese pizza 13` → `update_price:cheese pizza:13`
- `/remove_item cheese pizza` → `remove_item:cheese pizza`

Scoping / multi-merchant:
- The frontend or customer agent can include a hint like `merchant_id:123` as a separate agent-role message to scope data.
- The merchant agent reads this hint and serves/updates data for that merchant only.

## Wallet resolution

When another agent queries for the wallet (role `query_wallet` via A3A protocol), the merchant returns:
1) The wallet stored in MeTTa for the active merchant (if previously set via `set_wallet:`), otherwise
2) The fallback `MERCHANT_WALLET_ADDRESS` from environment.

## Testing tips

- You can validate dynamic behavior without blockchain using the script `test/metta_dynamic_merchant.py`.
- In live runs, after starting the merchant agent, send an admin command (role=agent) to update data; the system prompt automatically reflects the latest menu from MeTTa.

## Example prompts
- "What’s on your menu?"
- "Do you have a cheese pizza under $6?"
- "Recommend the cheapest option"

## Files
- `agent/merchant.py` - Merchant agent logic
- `agent/protocol/a3acontext.py` - Shared message types

## Notes
- Requires OrderContract deployed and accessible
- Merchant data (menu, prices, desc, wallet) is stored in MeTTa lazily and only when admin updates occur (NFT-gated at API layer).
*- No static seeding is performed by default.*

The merchant agent address is printed at startup; use that in MERCHANT_AGENT_ADDRESS for API calls.

### Agent address

**Customer Agent Address**: `agent1qf9ua6p2gz6nx47emvsf5d9840h7wpfwlcqhsqt4zz0dun8tj43l23jtuch`
