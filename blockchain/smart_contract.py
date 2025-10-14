"""
Smart Contract Integration Module

This module handles all interactions with the smart contract including:
- Contract initialization with ABI
- Reading from the contract
- Writing to the contract
- Token/ETH transfers
- Transaction management
"""

from web3 import Web3
from web3.contract import Contract
from eth_account import Account
import json
import os
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SmartContractManager:
    """
    Manages smart contract interactions using Web3.py
    """
    
    def __init__(self, 
                 provider_url: str,
                 contract_address: str,
                 contract_abi: List[Dict],
                 private_key: Optional[str] = None):
        """
        Initialize the smart contract manager
        
        Args:
            provider_url: Ethereum node URL (e.g., Infura, Alchemy)
            contract_address: The deployed contract address
            contract_abi: The contract ABI as a list of dictionaries
            private_key: Private key for signing transactions (optional)
        """
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract_address = Web3.toChecksumAddress(contract_address)
        self.contract_abi = contract_abi
        self.private_key = private_key
        
        # Initialize contract instance
        self.contract: Contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
        
        # Set default account if private key provided
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.w3.eth.default_account = self.account.address
        
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Web3 connection and contract setup"""
        if not self.w3.isConnected():
            raise ConnectionError("Failed to connect to Ethereum network")
        
        logger.info(f"Connected to Ethereum network. Latest block: {self.w3.eth.block_number}")
        logger.info(f"Contract address: {self.contract_address}")
    
    def get_account_balance(self, address: str) -> float:
        """
        Get ETH balance for an address
        
        Args:
            address: Ethereum address
            
        Returns:
            Balance in ETH
        """
        address = Web3.toChecksumAddress(address)
        balance_wei = self.w3.eth.get_balance(address)
        return self.w3.fromWei(balance_wei, 'ether')
    
    def call_contract_function(self, function_name: str, *args, **kwargs) -> Any:
        """
        Call a read-only contract function
        
        Args:
            function_name: Name of the contract function
            *args: Function arguments
            **kwargs: Additional arguments
            
        Returns:
            Function result
        """
        try:
            contract_function = getattr(self.contract.functions, function_name)
            result = contract_function(*args).call()
            logger.info(f"Called {function_name} with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling {function_name}: {str(e)}")
            raise
    
    def send_transaction(self, 
                        function_name: str, 
                        *args,
                        value: int = 0,
                        gas_limit: Optional[int] = None,
                        gas_price: Optional[int] = None,
                        **kwargs) -> str:
        """
        Send a transaction to the contract
        
        Args:
            function_name: Name of the contract function
            *args: Function arguments
            value: ETH value to send (in wei)
            gas_limit: Gas limit for the transaction
            gas_price: Gas price in wei
            **kwargs: Additional arguments
            
        Returns:
            Transaction hash
        """
        if not self.private_key:
            raise ValueError("Private key required for sending transactions")
        
        try:
            # Get contract function
            contract_function = getattr(self.contract.functions, function_name)
            
            # Build transaction
            transaction = contract_function(*args).buildTransaction({
                'from': self.account.address,
                'value': value,
                'gas': gas_limit or 2000000,
                'gasPrice': gas_price or self.w3.toWei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Sent transaction {function_name}: {tx_hash_hex}")
            return tx_hash_hex
            
        except Exception as e:
            logger.error(f"Error sending transaction {function_name}: {str(e)}")
            raise
    
    def wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 120) -> Dict:
        """
        Wait for transaction confirmation
        
        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
            
        Returns:
            Transaction receipt
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            logger.info(f"Transaction confirmed: {tx_hash}")
            return dict(receipt)
        except Exception as e:
            logger.error(f"Error waiting for transaction {tx_hash}: {str(e)}")
            raise
    
    def send_eth(self, to_address: str, amount_eth: float) -> str:
        """
        Send ETH to an address
        
        Args:
            to_address: Recipient address
            amount_eth: Amount in ETH
            
        Returns:
            Transaction hash
        """
        if not self.private_key:
            raise ValueError("Private key required for sending ETH")
        
        try:
            to_address = Web3.toChecksumAddress(to_address)
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            transaction = {
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': self.w3.toWei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            }
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Sent {amount_eth} ETH to {to_address}: {tx_hash_hex}")
            return tx_hash_hex
            
        except Exception as e:
            logger.error(f"Error sending ETH: {str(e)}")
            raise
    
    def estimate_gas(self, function_name: str, *args, value: int = 0) -> int:
        """
        Estimate gas for a transaction
        
        Args:
            function_name: Name of the contract function
            *args: Function arguments
            value: ETH value to send (in wei)
            
        Returns:
            Estimated gas
        """
        try:
            contract_function = getattr(self.contract.functions, function_name)
            gas_estimate = contract_function(*args).estimateGas({
                'from': self.account.address if self.account else None,
                'value': value
            })
            return gas_estimate
        except Exception as e:
            logger.error(f"Error estimating gas for {function_name}: {str(e)}")
            raise


class ContractConfig:
    """Configuration management for smart contracts"""
    
    @staticmethod
    def load_abi_from_file(file_path: str) -> List[Dict]:
        """Load ABI from JSON file"""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_provider_url(network: str = "mainnet") -> str:
        """Get provider URL based on network"""
        providers = {
            "mainnet": os.getenv("ETHEREUM_MAINNET_URL", "https://mainnet.infura.io/v3/YOUR_PROJECT_ID"),
            "sepolia": os.getenv("ETHEREUM_SEPOLIA_URL", "https://sepolia.infura.io/v3/YOUR_PROJECT_ID"),
            "polygon": os.getenv("POLYGON_MAINNET_URL", "https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID"),
        }
        return providers.get(network, providers["mainnet"])