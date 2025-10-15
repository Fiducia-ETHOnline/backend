# OrderContract Backend Integration - Quick Start

## 🚀 You're Almost Ready!

The complete OrderContract integration has been implemented. Here's how to get started:

## 1. Environment Setup

```bash
# Copy the environment template
cp .env.example .env

# Edit with your actual values
nano .env
```

**Required values in `.env`:**
```env
ORDER_CONTRACT_ADDRESS=0x...  # Your deployed OrderContract address
AGENT_CONTROLLER_PRIVATE_KEY=0x...  # Private key for agent operations
ETHEREUM_PROVIDER_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
```

## 2. Test the Integration

```bash
# Run the test script
python test_integration.py

# Start the server
python app.py

# Test health endpoint
curl http://localhost:5000/orders/health
```

## 3. Initialize the Service

```bash
curl -X POST http://localhost:5000/orders/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "order_contract_address": "YOUR_ACTUAL_CONTRACT_ADDRESS",
    "agent_controller_private_key": "YOUR_ACTUAL_PRIVATE_KEY"
  }'
```

## 4. Test Basic Operations

```bash
# Create an order
curl -X POST http://localhost:5000/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "0x...",
    "prompt": "What is the weather today?"
  }'

# Check service info
curl http://localhost:5000/orders/info
```

## 🎯 What's Ready

- ✅ Complete smart contract integration
- ✅ All OrderContract functions implemented
- ✅ pyUSD token handling
- ✅ Real-time event listening
- ✅ ASI agent bridge
- ✅ 15+ API endpoints
- ✅ Comprehensive error handling
- ✅ Production ready

## 📊 API Endpoints Available

- `POST /orders/initialize` - Initialize service
- `POST /orders/create` - Create new order
- `POST /orders/confirm` - Confirm order payment
- `POST /orders/agent/answer` - Agent proposes answer
- `POST /orders/agent/finalize` - Finalize completed order
- `POST /orders/user/orders` - Get user orders
- `GET /orders/health` - Health check
- And many more...

## 🔧 Integration with Your uAgent

```python
from blockchain.agent_integration import agent_process_user_request

@agent.on_message(A3AContext)
async def handle_request(ctx: Context, sender: str, msg: A3AContext):
    result = await agent_process_user_request(
        agent_address=ctx.agent.address,
        user_address=sender,
        prompt=msg.messages[0]['content'],
        ctx=ctx
    )
    # Process the result...
```

## 🚀 Ready for Production!

Your backend is now fully equipped to handle OrderContract operations!