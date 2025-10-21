import os
from web3 import Web3

PROVIDER = os.getenv('CONTRACT_URL', 'http://127.0.0.1:8545')
NFT_ADDRESS = os.getenv('MERCHANT_NFT_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PUBLIC_KEY = os.getenv('PUBLIC_KEY')

# Minimal ABI for mintNft(uint256) and ownerOf(uint256)
ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "merchantId", "type": "uint256"}],
        "name": "mintNft",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def main():
    if not (NFT_ADDRESS and PRIVATE_KEY and PUBLIC_KEY):
        print('Missing env: MERCHANT_NFT_ADDRESS, PRIVATE_KEY, PUBLIC_KEY required')
        return

    w3 = Web3(Web3.HTTPProvider(PROVIDER))
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    c = w3.eth.contract(address=Web3.to_checksum_address(NFT_ADDRESS), abi=ABI)

    # Use a deterministic merchantId for testing, e.g., 1
    merchant_id = int(os.getenv('TEST_MERCHANT_ID', '1'))

    # Build tx
    tx = c.functions.mintNft(merchant_id).build_transaction({
        'from': acct.address,
        'nonce': w3.eth.get_transaction_count(acct.address),
        'gas': 500000,
        'maxFeePerGas': w3.to_wei('2', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
        'chainId': w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    txh = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(txh)
    print('Mint tx mined:', receipt.transactionHash.hex())

    # Optional: verify ownerOf(merchant_id)
    owner = c.functions.ownerOf(merchant_id).call()
    print('Owner of token', merchant_id, 'is', owner)

if __name__ == '__main__':
    main()
