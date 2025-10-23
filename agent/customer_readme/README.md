🛒 Order Assistant Agent
This agent helps you describe what you want, checks the merchant’s live menu, suggests the best option within your budget, and prepares your on-chain order for payment.

Below is practical guidance—no technical jargon required.

✅ Things the Agent Can Do
- Understand what you want and suggest matching items with prices
- Consult the merchant for availability and pricing
- Create an order proposal and return a payment transaction for you to sign
- Keep details clear: item, price, and a linkable order description (CID)

❌ Things the Agent Will Not Do
- Take payment on your behalf (you sign the transaction)
- Modify the merchant’s menu (only merchants can update items/prices)
- Handle delivery or customer support post-purchase

🧪 Example Prompts
- “I want a cheese pizza under $6” → Suggests any items in budget, e.g., “cheese pizza: $5”
- “Recommend something cheap” → Suggests the best value option
- “Let’s proceed with that” → The agent will prepare the order proposal

🗺 Coverage
- Works with a specific merchant at a time (by merchant_id); your app preselects or sets this
- Uses the merchant’s live menu for accurate names and prices

ℹ️ Tips for Best Results
- Include a budget: “under $6” or “around $8”
- Be specific about size/toppings if needed
- Make sure your wallet is connected and funded for payment

🔁 Follow‑up Queries
- “Increase budget to $8”
- “What’s the total including the agent fee?”
- “Show me the menu again”

🧾 What You’ll Get (Order Response)
- Order ID: 1
- Description: cheese pizza
- Price: 5.00
- CID: bafy… (link to your order details)
- Unsigned transaction: JSON ready to sign and broadcast

After you sign and broadcast the transaction, the order is confirmed on-chain.

—

# Technical details (for developers)

## Capabilities
- Requirement gathering and refinement
- Merchant consultation via agent-to-agent messaging
- Order proposal creation on-chain (OrderContract)
- Payment confirmation workflow using pyUSD
- Status updates and notifications
- Price grounding from merchant MeTTa data (live menu)

## Protocols
- ChatProtocol (uAgents chat) for natural-language interaction
- A3AContext protocol (internal) for structured agent-to-agent messages

## Environment
Ensure the following variables are set (see `.env.example`):
- CONTRACT_URL
- AGENT_CONTRACT
- PYUSD_ADDRESS
- AGENT_PRIVATE_KEY
- DEFAULT_MERCHANT_ID (e.g., `1`, used to scope menu/wallet and merchant consultations)

## How it works
1. Gathers user needs via chat
2. Consults Merchant Agent for pricing/availability
3. Proposes an order using `create_propose(desc, price)`
4. Confirms payment with `confirm_order(order_id)`

### Merchant scoping and wallet lookup
The Customer Agent always scopes merchant queries (menu, wallet, consultations) by `DEFAULT_MERCHANT_ID`. This ensures the live MeTTa state for that merchant is used.

When building a payment, the Customer Agent queries the Merchant Agent’s wallet via the A3A protocol. The Merchant Agent will return the MeTTa-stored wallet if set by admin command, else it falls back to `MERCHANT_WALLET_ADDRESS` from environment.

## Run locally
1. Install requirements: `pip install -r requirements.txt`
2. Start backend: `python app.py`
3. Start Customer Agent: `python start_customer.py`

## Example prompts
- "I want a cheese pizza under $6"
- "Create an order for 2 pizzas at $5 each"
- "Confirm my last order"

## Files
- `agent/customer.py` - Customer agent logic
- `agent/protocol/a3acontext.py` - Shared message types

## Notes
- Requires OrderContract deployed and accessible
- Uses Lighthouse for order description storage
- Integrates MeTTa-based merchant knowledge (menu, prices) for better end-to-end flows
- The Customer Agent does not seed or mock menu data; it fetches the live menu from the Merchant Agent.

**Customer Agent Address**: agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up