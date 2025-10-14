# Smart Contract Integration

This module provides Web3 integration for interacting with Ethereum smart contracts.

## Features

- 🔗 Smart contract connection management
- 📖 Read contract data (view functions)
- ✍️ Write contract data (transaction functions)
- 💰 ETH transfers
- ⛽ Gas estimation
- 🛡️ Error handling and validation
- 🔐 Authentication integration

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `BLOCKCHAIN_PROVIDER_URL`: Your Ethereum node URL (Infura, Alchemy, etc.)
- `BLOCKCHAIN_CONTRACT_ADDRESS`: Your deployed contract address
- `BLOCKCHAIN_PRIVATE_KEY`: Private key for signing transactions (optional for read-only)

### 2. Install Dependencies

Dependencies are already included in `requirements.txt`:
- `web3`: Web3.py library for Ethereum interaction
- `eth-account`: Account management

### 3. Contract ABI

You'll need your contract's ABI (Application Binary Interface). You can:
- Load it from a JSON file using `load_abi_from_file()`
- Pass it directly as a list of dictionaries

## Usage

### Initialize the Service

```python
from blockchain.service import blockchain_service

# Initialize with your contract
success = blockchain_service.initialize_contract(
    contract_address="0x...",
    contract_abi=your_abi_data,
    private_key="0x..."  # Optional
)
```

### API Endpoints

The blockchain functionality is exposed through REST API endpoints:

#### POST `/blockchain/initialize`
Initialize smart contract connection

#### GET `/blockchain/info`
Get contract information and network status

#### POST `/blockchain/balance`
Check ETH balance for an address

#### POST `/blockchain/call`
Call read-only contract functions

#### POST `/blockchain/transaction`
Send transactions to contract

#### POST `/blockchain/payment`
Send ETH payments

#### POST `/blockchain/estimate-cost`
Estimate transaction costs

## Example Usage

### Reading Contract Data

```python
# Call a view function
result = blockchain_service.read_contract_data("balanceOf", "0x...")
```

### Writing Contract Data

```python
# Send a transaction
result = blockchain_service.write_contract_data(
    "transfer",
    "0x...",  # recipient
    1000,     # amount
    value_eth=0.1,  # ETH to send with transaction
    wait_for_confirmation=True
)
```

### Sending ETH

```python
# Send ETH payment
result = blockchain_service.send_payment(
    to_address="0x...",
    amount_eth=0.5,
    wait_for_confirmation=True
)
```

## Security Notes

- Never commit private keys to version control
- Use environment variables for sensitive data
- Consider using a hardware wallet or key management service in production
- Always validate addresses and amounts before transactions
- Test on testnets (Sepolia, Goerli) before mainnet deployment

## Network Support

Currently supports:
- Ethereum Mainnet
- Ethereum Sepolia (testnet)
- Polygon Mainnet
- Local networks (for development)

## Error Handling

The module includes custom exceptions:
- `ContractNotInitializedException`
- `TransactionFailedException`
- `InsufficientFundsException`
- `InvalidAddressException`
- `NetworkConnectionException`

## Next Steps

1. Provide your contract ABI
2. Set up your environment variables
3. Test the initialization endpoint
4. Implement your specific contract interactions

## Testing

Test your integration:

```bash
# Check if service is running
curl http://localhost:5000/blockchain/info

# Initialize contract (replace with your data)
curl -X POST http://localhost:5000/blockchain/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "contract_address": "0x...",
    "contract_abi": [...],
    "private_key": "0x..."
  }'
```