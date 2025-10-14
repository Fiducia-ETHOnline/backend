"""
Blockchain service layer for integrating smart contracts with the API
"""

from typing import Dict, Any, Optional, List
import logging
from .smart_contract import SmartContractManager
from .config import blockchain_settings, get_provider_url
from .exceptions import (
    ContractNotInitializedException,
    TransactionFailedException,
    InsufficientFundsException,
    InvalidAddressException,
    NetworkConnectionException
)
import json

logger = logging.getLogger(__name__)

class BlockchainService:
    """
    Service layer for blockchain operations
    Integrates smart contract functionality with the existing API
    """
    
    def __init__(self):
        self.contract_manager: Optional[SmartContractManager] = None
        self._initialized = False
    
    def initialize_contract(self, 
                          contract_address: str, 
                          contract_abi: List[Dict],
                          private_key: Optional[str] = None) -> bool:
        """
        Initialize the smart contract connection
        
        Args:
            contract_address: The deployed contract address
            contract_abi: The contract ABI
            private_key: Private key for transactions (optional)
            
        Returns:
            True if initialization successful
        """
        try:
            provider_url = get_provider_url()
            
            self.contract_manager = SmartContractManager(
                provider_url=provider_url,
                contract_address=contract_address,
                contract_abi=contract_abi,
                private_key=private_key or blockchain_settings.private_key
            )
            
            self._initialized = True
            logger.info("Blockchain service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize blockchain service: {str(e)}")
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if the service is properly initialized"""
        return self._initialized and self.contract_manager is not None
    
    def _ensure_initialized(self):
        """Ensure the service is initialized, raise exception if not"""
        if not self.is_initialized():
            raise ContractNotInitializedException("Blockchain service not initialized")
    
    def get_contract_info(self) -> Dict[str, Any]:
        """Get basic contract information"""
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        return {
            "contract_address": self.contract_manager.contract_address,
            "network": blockchain_settings.ethereum_network,
            "connected": self.contract_manager.w3.isConnected(),
            "latest_block": self.contract_manager.w3.eth.block_number
        }
    
    def check_balance(self, address: str) -> Dict[str, Any]:
        """
        Check ETH balance for an address
        
        Args:
            address: Ethereum address
            
        Returns:
            Balance information
        """
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        try:
            balance_eth = self.contract_manager.get_account_balance(address)
            return {
                "address": address,
                "balance_eth": balance_eth,
                "balance_wei": self.contract_manager.w3.toWei(balance_eth, 'ether')
            }
        except Exception as e:
            logger.error(f"Error checking balance for {address}: {str(e)}")
            raise
    
    def read_contract_data(self, function_name: str, *args) -> Any:
        """
        Read data from the smart contract
        
        Args:
            function_name: Contract function name
            *args: Function arguments
            
        Returns:
            Function result
        """
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        return self.contract_manager.call_contract_function(function_name, *args)
    
    def write_contract_data(self, 
                           function_name: str, 
                           *args,
                           value_eth: float = 0,
                           wait_for_confirmation: bool = True) -> Dict[str, Any]:
        """
        Write data to the smart contract
        
        Args:
            function_name: Contract function name
            *args: Function arguments
            value_eth: ETH amount to send with transaction
            wait_for_confirmation: Whether to wait for transaction confirmation
            
        Returns:
            Transaction information
        """
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        try:
            value_wei = self.contract_manager.w3.toWei(value_eth, 'ether') if value_eth > 0 else 0
            
            # Send transaction
            tx_hash = self.contract_manager.send_transaction(
                function_name,
                *args,
                value=value_wei,
                gas_limit=blockchain_settings.default_gas_limit,
                gas_price=self.contract_manager.w3.toWei(blockchain_settings.default_gas_price_gwei, 'gwei')
            )
            
            result = {
                "transaction_hash": tx_hash,
                "function_name": function_name,
                "value_eth": value_eth,
                "status": "pending"
            }
            
            if wait_for_confirmation:
                receipt = self.contract_manager.wait_for_transaction_receipt(
                    tx_hash, 
                    timeout=blockchain_settings.transaction_timeout
                )
                result.update({
                    "status": "confirmed" if receipt.get("status") == 1 else "failed",
                    "gas_used": receipt.get("gasUsed"),
                    "block_number": receipt.get("blockNumber"),
                    "receipt": receipt
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error writing to contract {function_name}: {str(e)}")
            raise
    
    def send_payment(self, 
                    to_address: str, 
                    amount_eth: float,
                    wait_for_confirmation: bool = True) -> Dict[str, Any]:
        """
        Send ETH payment to an address
        
        Args:
            to_address: Recipient address
            amount_eth: Amount in ETH
            wait_for_confirmation: Whether to wait for confirmation
            
        Returns:
            Transaction information
        """
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        try:
            tx_hash = self.contract_manager.send_eth(to_address, amount_eth)
            
            result = {
                "transaction_hash": tx_hash,
                "to_address": to_address,
                "amount_eth": amount_eth,
                "status": "pending"
            }
            
            if wait_for_confirmation:
                receipt = self.contract_manager.wait_for_transaction_receipt(
                    tx_hash,
                    timeout=blockchain_settings.transaction_timeout
                )
                result.update({
                    "status": "confirmed" if receipt.get("status") == 1 else "failed",
                    "gas_used": receipt.get("gasUsed"),
                    "block_number": receipt.get("blockNumber"),
                    "receipt": receipt
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending payment: {str(e)}")
            raise
    
    def estimate_transaction_cost(self, 
                                 function_name: str, 
                                 *args, 
                                 value_eth: float = 0) -> Dict[str, Any]:
        """
        Estimate the cost of a transaction
        
        Args:
            function_name: Contract function name
            *args: Function arguments
            value_eth: ETH amount to send
            
        Returns:
            Cost estimation
        """
        if not self.is_initialized():
            raise ValueError("Blockchain service not initialized")
        
        try:
            value_wei = self.contract_manager.w3.toWei(value_eth, 'ether') if value_eth > 0 else 0
            gas_estimate = self.contract_manager.estimate_gas(function_name, *args, value=value_wei)
            gas_price = self.contract_manager.w3.toWei(blockchain_settings.default_gas_price_gwei, 'gwei')
            
            total_cost_wei = gas_estimate * gas_price
            total_cost_eth = self.contract_manager.w3.fromWei(total_cost_wei, 'ether')
            
            return {
                "gas_estimate": gas_estimate,
                "gas_price_gwei": blockchain_settings.default_gas_price_gwei,
                "total_cost_wei": total_cost_wei,
                "total_cost_eth": total_cost_eth,
                "value_eth": value_eth,
                "total_eth_needed": total_cost_eth + value_eth
            }
        except Exception as e:
            logger.error(f"Error estimating transaction cost: {str(e)}")
            raise

# Global service instance
blockchain_service = BlockchainService()