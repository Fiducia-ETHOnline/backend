# Merchant Agent README

## Overview
The Merchant Agent represents the seller side of the marketplace. It receives customer intents, matches inventory, provides quotes, and answers proposals on-chain through the OrderContract. It also coordinates fulfillment updates.

## Capabilities
- Interpret customer needs and map to products
- Price recommendation and quoting
- Respond to order proposals (`propose_order_answer`)
- Coordinate fulfillment and status updates

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
