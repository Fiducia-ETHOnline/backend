# Customer Agent README

## Overview
The Customer Agent helps end-users discover products, refine requirements, and create blockchain-backed orders using the OrderContract with pyUSD payments. It collaborates with the Merchant Agent to fetch offers and finalize orders.

## Capabilities
- Requirement gathering and refinement
- Merchant consultation via agent-to-agent messaging
- Order proposal creation on-chain (OrderContract)
- Payment confirmation workflow using pyUSD
- Status updates and notifications
- Price fallback from merchant MeTTa data when the model omits/returns invalid price

## Protocols
- ChatProtocol (uAgents chat) for natural-language interaction
- A3AContext protocol (internal) for structured agent-to-agent messages

## Environment
Ensure the following variables are set (see `.env.example`):
- CONTRACT_URL
- AGENT_CONTRACT
- PYUSD_ADDRESS
- AGENT_PRIVATE_KEY

## How it works
1. Gathers user needs via chat
2. Consults Merchant Agent for pricing/availability
3. Proposes an order using `create_propose(desc, price)`
4. Confirms payment with `confirm_order(order_id)`

### Wallet lookup
When building a payment, the Customer Agent queries the Merchant Agent’s wallet via the A3A protocol. The Merchant Agent will return the MeTTa-stored wallet if set by admin command, else it falls back to `MERCHANT_WALLET_ADDRESS` from environment.

## Run locally
1. Install requirements: `pip install -r requirements.txt`
2. Start backend: `python app.py`
3. Start Customer Agent: `python start_customer.py`

## Example prompts
- "I need a large cheese pizza with extra toppings."
- "Create an order for 2 pizzas at $12 each"
- "Confirm my last order"

## Files
- `agent/customer.py` - Customer agent logic
- `agent/protocol/a3acontext.py` - Shared message types

## Notes
- Requires OrderContract deployed and accessible
- Uses Lighthouse for order description storage
- Integrates MeTTa-based merchant knowledge (menu, prices) for better end-to-end flows

**Customer Agent Address**: agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up