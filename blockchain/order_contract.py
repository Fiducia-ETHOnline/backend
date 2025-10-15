"""
OrderContract specific integration module

This module provides specialized functions for interacting with the OrderContract
smart contract, including all order management operations and user queries.
"""

from web3 import Web3
from web3.contract import Contract
from eth_account import Account
import json
import hashlib
from typing import Optional, Dict, Any, List, Tuple
import logging
from enum import IntEnum
from dataclasses import dataclass
from datetime import datetime

from .smart_contract import SmartContractManager
from .exceptions import (
    ContractNotInitializedException,
    TransactionFailedException,
    InsufficientFundsException,
    InvalidAddressException
)
from .utils import is_valid_ethereum_address, to_checksum_address, wei_to_eth, eth_to_wei

logger = logging.getLogger(__name__)

class OrderStatus(IntEnum):
    """Order status enum matching the smart contract"""
    PROPOSED = 0    # Order has been proposed by agent with price
    CONFIRMED = 1   # User has confirmed and paid for the order
    IN_PROGRESS = 2 # Order has been created but no answer proposed yet
    COMPLETED = 3   # Order has been finalized and payment released
    CANCELLED = 4   # Order has been cancelled and refunded

@dataclass
class OrderDetails:
    """Data class for order details"""
    order_id: str
    buyer: str
    seller:str
    prompt_hash: str
    answer_hash: str
    price: float  # in pyUSD
    paid: float   # in pyUSD
    timestamp: datetime
    status: OrderStatus
    status_name: str

@dataclass
class OrderEvent:
    """Data class for order events"""
    event_type: str
    user: str
    order_id: str
    transaction_hash: str
    block_number: int
    additional_data: Dict[str, Any]

class OrderContractManager:
    """
    Specialized manager for OrderContract interactions
    """
    
    # Contract constants
    AGENT_FEE = eth_to_wei(1.0)  # 1 pyUSD
    HOLD_PERIOD = 600  # 10 minutes in seconds
    
    def __init__(self,
                 provider_url: str,
                 order_contract_address: str,
                 pyusd_token_address: str,
                 order_contract_abi: List[Dict],
                 erc20_abi: List[Dict],
                 agent_controller_private_key: Optional[str] = None,
                 user_private_key: Optional[str] = None):
        """
        Initialize OrderContract manager
        
        Args:
            provider_url: Ethereum node URL
            order_contract_address: OrderContract address
            pyusd_token_address: pyUSD token address
            order_contract_abi: OrderContract ABI
            erc20_abi: ERC20 ABI for pyUSD token
            agent_controller_private_key: Agent controller private key
            user_private_key: User private key for transactions
        """
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.order_contract_address = to_checksum_address(order_contract_address)
        self.pyusd_token_address = to_checksum_address(pyusd_token_address)
        
        # Initialize contracts
        self.order_contract: Contract = self.w3.eth.contract(
            address=self.order_contract_address,
            abi=order_contract_abi
        )
        
        self.pyusd_contract: Contract = self.w3.eth.contract(
            address=self.pyusd_token_address,
            abi=erc20_abi
        )
        
        # Set up accounts
        self.agent_account = None
        self.user_account = None
        
        if agent_controller_private_key:
            self.agent_account = Account.from_key(agent_controller_private_key)
            
        if user_private_key:
            self.user_account = Account.from_key(user_private_key)
            
        self._verify_connection()
    def set_user_private_key(self,key):
        self.user_account = Account.from_key(key)

    def _verify_connection(self):
        """Verify Web3 connection and contract setup"""
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum network")
        
        logger.info(f"Connected to Ethereum network. Latest block: {self.w3.eth.block_number}")
        logger.info(f"OrderContract address: {self.order_contract_address}")
        logger.info(f"pyUSD Token address: {self.pyusd_token_address}")
    
    def create_prompt_hash(self, prompt: str) -> str:
        """
        Create a hash for the user prompt
        
        Args:
            prompt: User prompt text
            
        Returns:
            Hex string of the hash
        """
        return Web3.keccak(text=prompt).hex()
    
    def create_answer_hash(self, answer: str) -> str:
        """
        Create a hash for the agent answer
        
        Args:
            answer: Agent answer text
            
        Returns:
            Hex string of the hash
        """
        return '0x'+Web3.keccak(text=answer).hex()
    
    # ========== USER FUNCTIONS ==========
    def build_propose_order_transaction(self,prompt_hash:str,user_address:str):
        """
        Create a new order proposal but now real send (user function)
        
        Args:
            prompt: User prompt text
            user_address: User address (uses user_account if not provided)
            
        Returns:
            Tuple of (order_id, transaction_hash)
        """
        if not self.user_account and not user_address:
            raise ValueError("User account or address required")
        if user_address:
            user_address = to_checksum_address(user_address)
        # prompt_hash = self.create_prompt_hash(prompt)
        from_address = user_address or self.user_account.address
        # print(f'from_address is {from_address}')
        try:
            # Build transaction
            transaction = self.order_contract.functions.proposeOrder(
                prompt_hash
            ).build_transaction({
                'from': from_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })
            return transaction
           
        except Exception as e:
            logger.error(f"Error proposing order: {str(e)}")
            raise
    def propose_order(self, prompt_hash: str, user_wallet_address: str) -> Tuple[str, str]:
        """
        Create a new order proposal (user function)
        
        Args:
            prompt: User prompt text
            user_address: User address (uses user_account if not provided)
            
        Returns:
            Tuple of (order_id, transaction_hash)
        """
        # if not self.user_account and not user_address:
        #     raise ValueError("User account or address required")
        # if user_address:
        #     user_address = to_checksum_address(user_address)
        # prompt_hash = self.create_prompt_hash(prompt)
        from_address =  self.agent_account.address
        # print(f'from_address is {from_address}')
        try:
            # Build transaction
            transaction = self.order_contract.functions.proposeOrder(
                prompt_hash,
                to_checksum_address(user_wallet_address)
            ).build_transaction({
                'from': from_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })
            
            # Sign and send transaction
            # if self.user_account:
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.agent_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            # else:
                # raise ValueError("User private key required for transaction signing")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            # Extract order ID from events

            print(receipt)
            for log in receipt.logs:
                try:
                    decoded_log = self.order_contract.events.OrderProposed().process_log(log)
                    order_id = str(decoded_log['args']['offerId'])
                    logger.info(f"Order created: {order_id}")
                    return order_id, tx_hash.hex()
                except Exception as e:
                    print(e)
                    continue
                    
            raise Exception("OrderProposed event not found in transaction receipt")
            
        except Exception as e:
            logger.error(f"Error proposing order: {str(e)}")
            raise
    def build_confirm_order(self, order_id: str, user_address: Optional[str] = None) -> str:
        """
        Confirm an order and pay for it (user function)
        
        Args:
            order_id: Order ID to confirm
            user_address: User address (uses user_account if not provided)
            
        Returns:
            Transaction hash
        """
        if not self.user_account and not user_address:
            raise ValueError("User account or address required")
        
        from_address = user_address or self.user_account.address
        from_address = to_checksum_address(from_address)
        try:
            # Get order details to check price
            order_details = self.get_order_details_by_id(order_id)
            total_amount = order_details.price + wei_to_eth(self.AGENT_FEE)
            
            # Check pyUSD balance
            # balance = self.get_pyusd_balance(from_address)
            # if balance < total_amount:
            #     raise InsufficientFundsException(f"Insufficient pyUSD balance. Required: {total_amount}, Available: {balance}")
            
            # # Check and approve pyUSD spending if needed
            # allowance = self.get_pyusd_allowance(from_address, self.order_contract_address)
            # required_amount_wei = eth_to_wei(total_amount)
            
            # if allowance < required_amount_wei:
            #     approve_tx = self.approve_pyusd_spending(required_amount_wei, from_address)
            #     logger.info(f"Approved pyUSD spending: {approve_tx}")
            
            # Confirm order
            transaction = self.order_contract.functions.confirmOrder(
                int(order_id)
            ).build_transaction({
                'from': from_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })
            
            # if self.user_account:
            #     signed_txn = self.w3.eth.account.sign_transaction(transaction, self.user_account.key)
            #     tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            #     return tx_hash.hex()
            # else:
            #     raise ValueError("User private key required for transaction signing")
            return transaction    
        except Exception as e:
            logger.error(f"Error confirming order {order_id}: {str(e)}")
            raise
    
    def confirm_order(self, order_id: str, user_address: Optional[str] = None) -> str:
        """
        Confirm an order and pay for it (user function)
        
        Args:
            order_id: Order ID to confirm
            user_address: User address (uses user_account if not provided)
            
        Returns:
            Transaction hash
        """
        if not self.user_account and not user_address:
            raise ValueError("User account or address required")
        
        from_address = user_address or self.user_account.address
        
        try:
            # Get order details to check price
            order_details = self.get_order_details_by_id(order_id)
            total_amount = order_details.price + wei_to_eth(self.AGENT_FEE)
            
            # Check pyUSD balance
            balance = self.get_pyusd_balance(from_address)
            if balance < total_amount:
                raise InsufficientFundsException(f"Insufficient pyUSD balance. Required: {total_amount}, Available: {balance}")
            
            # Check and approve pyUSD spending if needed
            allowance = self.get_pyusd_allowance(from_address, self.order_contract_address)
            required_amount_wei = eth_to_wei(total_amount)
            
            if allowance < required_amount_wei:
                approve_tx = self.approve_pyusd_spending(required_amount_wei, from_address)
                logger.info(f"Approved pyUSD spending: {approve_tx}")
            
            # Confirm order
            transaction = self.order_contract.functions.confirmOrder(
                int(order_id)
            ).build_transaction({
                'from': from_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })
            
            if self.user_account:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.user_account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                return tx_hash.hex()
            else:
                raise ValueError("User private key required for transaction signing")
                
        except Exception as e:
            logger.error(f"Error confirming order {order_id}: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str, user_address: Optional[str] = None) -> str:
        """
        Cancel a confirmed order after hold period (user function)
        
        Args:
            order_id: Order ID to cancel
            user_address: User address (uses user_account if not provided)
            
        Returns:
            Transaction hash
        """
        if not self.user_account and not user_address:
            raise ValueError("User account or address required")
        
        from_address = user_address or self.user_account.address
        
        try:
            transaction = self.order_contract.functions.cancelOrder(
                int(order_id)
            ).build_transaction({
                'from': from_address,
                'gas': 300000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_address),
            })
            
            if self.user_account:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.user_account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                return tx_hash.hex()
            else:
                raise ValueError("User private key required for transaction signing")
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            raise
    
    # ========== AGENT FUNCTIONS ==========
    
    def propose_order_answer(self, order_id: str, answer: str, price_pyusd: float,seller_address:str) -> str:
        """
        Propose an answer and price for an order (agent function)
        
        Args:
            order_id: Order ID to answer
            answer: Agent's answer text
            price_pyusd: Price in pyUSD
            
        Returns:
            Transaction hash
        """
        if not self.agent_account:
            raise ValueError("Agent controller account required")
        
        answer_hash = self.create_answer_hash(answer)
        price_wei = eth_to_wei(price_pyusd)
        controller_onchain = self.order_contract.functions.getAgentController().call()


        try:
            txn = self.order_contract.functions.proposeOrderAnswer(
                answer_hash,
                int(order_id),
                price_wei,
                to_checksum_address(seller_address)
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 300000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
            })

            signed_txn = self.w3.eth.account.sign_transaction(txn, self.agent_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print("✅ sent:", tx_hash.hex())
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Error proposing answer for order {order_id}: {str(e)}")
            raise
    
    def finalize_order(self, order_id: str) -> str:
        """
        Finalize an order and release payment (agent function)
        
        Args:
            order_id: Order ID to finalize
            
        Returns:
            Transaction hash
        """
        if not self.agent_account:
            raise ValueError("Agent controller account required")
        
        try:
            transaction = self.order_contract.functions.finalizeOrder(
                int(order_id)
            ).build_transaction({
                'from': self.agent_account.address,
                'gas': 300000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.agent_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Error finalizing order {order_id}: {str(e)}")
            raise
    
    # ========== QUERY FUNCTIONS ==========
    
    def get_user_order_ids(self, user_address: str) -> List[str]:
        """Get all order IDs for a user"""
        user_address = to_checksum_address(user_address)
        order_ids = self.order_contract.functions.getUserOrderIds(user_address).call()
        return [str(order_id) for order_id in order_ids]
    
    def get_user_orders_with_status(self, user_address: str) -> Tuple[List[str], List[OrderStatus]]:
        """Get all orders and their statuses for a user"""
        user_address = to_checksum_address(user_address)
        order_ids, statuses = self.order_contract.functions.getUserOrdersWithStatus(user_address).call()
        return [str(order_id) for order_id in order_ids], [OrderStatus(status) for status in statuses]
    
    def get_user_orders_by_status(self, user_address: str, status: OrderStatus) -> List[str]:
        """Get orders for a user filtered by status"""
        user_address = to_checksum_address(user_address)
        order_ids = self.order_contract.functions.getUserOrdersByStatus(user_address, status.value).call()
        return [str(order_id) for order_id in order_ids]
    
    def get_user_order_details(self, user_address: str, order_id: str) -> OrderDetails:
        """Get complete order details for a user's order"""
        user_address = to_checksum_address(user_address)
        offer = self.order_contract.functions.getUserOrderDetails(user_address, int(order_id)).call()
        
        return OrderDetails(
            order_id=order_id,
            buyer=offer[0],
            prompt_hash=offer[1].hex(),
            answer_hash=offer[2].hex(),
            price=wei_to_eth(offer[3]),
            paid=wei_to_eth(offer[4]),
            timestamp=datetime.fromtimestamp(offer[5]),
            status=OrderStatus(offer[6]),
            status_name=OrderStatus(offer[6]).name
        )
    
    def get_order_details_by_id(self, order_id: str) -> OrderDetails:
        """Get order details by order ID"""
        offer = self.order_contract.functions.offers(int(order_id)).call()
        
        return OrderDetails(
            order_id=order_id,
            buyer=offer[0],
            seller=offer[1],
            prompt_hash=offer[2].hex(),
            answer_hash=offer[3].hex(),
            price=wei_to_eth(offer[4]),
            paid=wei_to_eth(offer[5]),
            timestamp=datetime.fromtimestamp(offer[6]),
            status=OrderStatus(offer[7]),
            status_name=OrderStatus(offer[7]).name
        )
    
    def has_user_order(self, user_address: str, order_id: str) -> bool:
        """Check if a specific order belongs to a user"""
        user_address = to_checksum_address(user_address)
        return self.order_contract.functions.hasUserOrder(user_address, int(order_id)).call()
    
    def get_user_order_status(self, user_address: str, order_id: str) -> OrderStatus:
        """Get the status of a specific order for a user"""
        user_address = to_checksum_address(user_address)
        status = self.order_contract.functions.getUserOrderStatus(user_address, int(order_id)).call()
        return OrderStatus(status)
    
    # ========== pyUSD TOKEN FUNCTIONS ==========
    
    def get_pyusd_balance(self, address: str) -> float:
        """Get pyUSD balance for an address"""
        address = to_checksum_address(address)
        balance_wei = self.pyusd_contract.functions.balanceOf(address).call()
        return wei_to_eth(balance_wei)
    
    def get_pyusd_allowance(self, owner: str, spender: str) -> int:
        """Get pyUSD allowance"""
        owner = to_checksum_address(owner)
        spender = to_checksum_address(spender)
        return self.pyusd_contract.functions.allowance(owner, spender).call()
    
    def approve_pyusd_spending(self, amount_wei: int, from_address: Optional[str] = None) -> str:
        """Approve pyUSD spending for the OrderContract"""
        if not self.user_account and not from_address:
            raise ValueError("User account required for approval")
        
        from_addr = from_address or self.user_account.address
        
        try:
            transaction = self.pyusd_contract.functions.approve(
                self.order_contract_address,
                amount_wei
            ).build_transaction({
                'from': from_addr,
                'gas': 100000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(from_addr),
            })
            
            if self.user_account:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.user_account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                return tx_hash.hex()
            else:
                raise ValueError("User private key required for transaction signing")
                
        except Exception as e:
            logger.error(f"Error approving pyUSD spending: {str(e)}")
            raise
    
    # ========== CONTRACT INFO FUNCTIONS ==========
    
    def get_agent_controller(self) -> str:
        """Get the agent controller address"""
        return self.order_contract.functions.getAgentController().call()
    
    def get_agent_fee(self) -> float:
        """Get the agent fee in pyUSD"""
        fee_wei = self.order_contract.functions.getAgentFee().call()
        return wei_to_eth(fee_wei)
    
    def get_contract_info(self) -> Dict[str, Any]:
        """Get general contract information"""
        return {
            "order_contract_address": self.order_contract_address,
            "pyusd_token_address": self.pyusd_token_address,
            "agent_controller": self.get_agent_controller(),
            "agent_fee_pyusd": self.get_agent_fee(),
            "hold_period_seconds": self.HOLD_PERIOD,
            "network_connected": self.w3.is_connected(),
            "latest_block": self.w3.eth.block_number
        }