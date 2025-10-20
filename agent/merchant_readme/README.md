# Merchant Agent README

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

Example slash mapping (UI → agent message):
- `/set_wallet 0xABC...` → `set_wallet:0xABC...`
- `/add_item cheese_pizza 12` → `add_item:cheese_pizza:12`
- `/update_price cheese_pizza 13` → `update_price:cheese_pizza:13`
- `/remove_item cheese_pizza` → `remove_item:cheese_pizza`

## Wallet resolution

When another agent queries for the wallet (role `query_wallet` via A3A protocol), the merchant returns:
1) The wallet stored in MeTTa for `TestPizzaAgent` (if previously set via `set_wallet:`), otherwise
2) The fallback `MERCHANT_WALLET_ADDRESS` from environment.

## Testing tips

- You can validate dynamic behavior without blockchain using the script `test/metta_dynamic_merchant.py`.
- In live runs, after starting the merchant agent, send an admin command (role=agent) to update data; the system prompt automatically reflects the latest menu from MeTTa.

## Example prompts
- "Customer wants onion pizza under $12"
- "Send a quote for large cheese pizza"

## Files
- `agent/merchant.py` - Merchant agent logic
- `agent/protocol/a3acontext.py` - Shared message types

## Notes
- Requires OrderContract deployed and accessible
- Include merchant name in every response (see system prompt)

**Merchant Agent Address**:'agent1qf9ua6p2gz6nx47emvsf5d9840h7wpfwlcqhsqt4zz0dun8tj43l23jtuch'
