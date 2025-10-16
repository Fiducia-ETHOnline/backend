# Fiducia Backend - Decentralized Order Management with ASI Agent Integration

## Overview

Fiducia Backend is a production-ready decentralized order management platform that bridges traditional API services with blockchain smart contracts and ASI (Artificial Superintelligence) agent communication. Built on FastAPI with comprehensive Web3 integration, it enables seamless order processing through smart contracts using pyUSD tokens while maintaining real-time communication with ASI agents.

**🔗 Smart Contract Integration**: Complete OrderContract implementation with pyUSD token payments  
**🤖 ASI Agent Bridge**: Direct communication with ASI agents for automated order processing  
**⚡ Real-time Events**: Blockchain event listening and processing  
**🛡️ Production Ready**: Comprehensive error handling, validation, and testing  
**📊 RESTful APIs**: 15+ endpoints for complete order lifecycle management  

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  OrderContract   │    │   ASI Agents    │
│                 │    │   (Ethereum)     │    │                 │
│  • Auth System  │◄──►│  • pyUSD Token   │◄──►│ • Customer      │
│  • Order APIs   │    │  • Order Logic   │    │ • Merchant      │
│  • Event System │    │  • Agent Control │    │ • Bridge        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Web3 Service   │    │  Event Listener  │    │  Agent Bridge   │
│                 │    │                  │    │                 │
│ • Contract Mgmt │    │ • Real-time      │    │ • Message Queue │
│ • Transaction   │    │ • Historical     │    │ • Order Sync    │
│ • Gas Handling  │    │ • Processing     │    │ • Agent Comms   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

### 🔐 Authentication & Authorization
- JWT token-based authentication
- Role-based access control (Customer/Merchant)
- Secure wallet integration
- Session management

### 💼 Order Management
- **Smart Contract Orders**: Create, confirm, cancel orders on-chain
- **pyUSD Integration**: Seamless token payments and transfers
- **Agent Communication**: ASI agent integration for automated processing
- **Real-time Updates**: Live order status synchronization
- **Order History**: Complete transaction tracking

### 🤖 ASI Agent Integration
- **Customer Agent**: Handles order requests and customer interactions
- **Merchant Agent**: Manages inventory and order fulfillment
- **Agent Bridge**: Facilitates communication between agents and smart contracts
- **Message Queue**: Reliable message passing system

### ⛓️ Blockchain Integration
- **OrderContract**: Complete smart contract interaction
- **Event Listening**: Real-time blockchain event processing
- **Gas Management**: Automatic gas estimation and optimization
- **Error Handling**: Comprehensive transaction error management

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for smart contract deployment)
- Ethereum development environment (Anvil/Ganache)

### 1. Clone Repository
```bash
git clone https://github.com/Fiducia-ETHOnline/backend.git
cd backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Smart Contract Setup
```bash
# Clone smart contract repository
git clone -b feature/backend-integration-test git@github.com:Fiducia-ETHOnline/smart-contract-for-orderAgent.git
cd smart-contract-for-orderAgent

# Build contracts
forge build

# Start local blockchain
anvil

# Deploy contracts
forge script script/DeployOrderContract.s.sol:DeployOrderContract --rpc-url 127.0.0.1:8545 --broadcast --private-key 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba
```

### 4. Environment Configuration
```bash
cp .env.example .env
# Update .env with your contract addresses and keys
```

### 5. Start Backend Services
```bash
# Start main API server
python app.py

# Start ASI agents (in separate terminals)
python start_customer.py
python start_merchant.py
```

## API Endpoints

### Authentication
- `POST /api/auth/challenge` - Generate authentication challenge
- `POST /api/auth/login` - User login with credentials

### Order Management
- `GET /orders/` - List all orders
- `POST /orders/propose` - Propose new order
- `POST /orders/{order_id}/confirm` - Confirm order
- `POST /orders/{order_id}/cancel` - Cancel order
- `GET /orders/{order_id}/status` - Get order status

### Agent Operations
- `POST /orders/agent/propose` - Agent propose order
- `POST /orders/agent/respond` - Agent respond to order
- `GET /orders/agent/queue` - Get agent message queue

### Blockchain Queries
- `GET /orders/contract/info` - Get contract information
- `GET /orders/events/{event_type}` - Query blockchain events
- `POST /orders/initialize` - Initialize contract connection

## Smart Contract Integration

### OrderContract Functions

#### User Operations
```python
# Propose a new order
propose_order(item_name: str, quantity: int, price_per_item: int, buyer_agent: str, seller_agent: str)

# Confirm an order (buyer)
confirm_order(order_id: int, payment_amount: int)

# Cancel an order
cancel_order(order_id: int)
```

#### Agent Operations
```python
# Agent proposes order response
propose_order_answer(order_id: int, response_details: str)

# Finalize completed order
finalize_order(order_id: int)
```

### Event Monitoring
Real-time blockchain event listening for:
- `OrderProposed` - New order creation
- `OrderConfirmed` - Order confirmation with payment
- `OrderFinalized` - Order completion
- `OrderCancelled` - Order cancellation

## ASI Agent System

### Agent Types

#### Customer Agent
- **Address**: `agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up`
- **Functions**: Order requests, payment processing, status tracking
- **Protocols**: Chat communication, order negotiation

#### Merchant Agent
- **Functions**: Inventory management, order fulfillment, shipping
- **Protocols**: Order processing, status updates

### Agent Communication
```python
# Agent message structure
{
    "agent_id": "agent1q...",
    "order_id": 123,
    "message_type": "order_request",
    "data": {
        "item": "Product Name",
        "quantity": 5,
        "price": 100
    }
}
```

## Testing

### Integration Tests
```bash
# Run comprehensive integration tests
python test_integration.py

# Test specific components
python test/chat.py          # Chat functionality
python test/get_orders.py    # Order retrieval
python test/auth.py          # Authentication
```

### Manual Testing
```bash
# Test order creation
curl -X POST http://localhost:5000/orders/propose \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Test Item", "quantity": 1, "price_per_item": 100}'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Update documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🚀 Ready for production deployment with comprehensive smart contract integration, real-time events, and ASI agent communication!**

## Agents

- Customer Agent: see `agent/customer_readme.md`
- Merchant Agent: see `agent/merchant_readme.md`

## Protocols (Summary)

- ChatProtocol (uAgents): natural language chat for human ↔ agent and agent ↔ agent
- A3AContext: internal structured messages for order-related intents

Example A3A message:

```
{
  "message_id": "msg_12345",
  "sender_agent": "agent1q...",
  "recipient_agent": "agent1q...",
  "type": "order_request",
  "data": {
    "desc": "2x cheese pizza, large",
    "price": "12.00"
  }
}
```