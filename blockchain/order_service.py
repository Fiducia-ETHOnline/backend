"""
OrderContract service layer - integrates all components for API use
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .order_contract import OrderContractManager, OrderStatus, OrderDetails
from .event_listener import OrderEventListener, OrderEvent, UserEventSubscription
from .agent_bridge import AgentOrderBridge, AgentMessage, AgentMessageQueue
from .config import blockchain_settings, get_provider_url
from .exceptions import (
    ContractNotInitializedException,
    TransactionFailedException,
    InsufficientFundsException,
    InvalidAddressException
)

logger = logging.getLogger(__name__)

class OrderContractService:
    """
    Comprehensive service layer for OrderContract integration
    Combines all blockchain functionality for easy API access
    """
    
    def __init__(self):
        """Initialize the service"""
        self.contract_manager: Optional[OrderContractManager] = None
        self.event_listener: Optional[OrderEventListener] = None
        self.agent_bridge: Optional[AgentOrderBridge] = None
        self.message_queue: AgentMessageQueue = AgentMessageQueue()
        self._initialized = False
        
        # Contract addresses (to be set during initialization)
        self.order_contract_address: Optional[str] = None
        self.pyusd_token_address: str = "0xCaC524BcA292aaade2DF8A05cC58F0a65B1B3bB9"  # Sepolia
        self.agent_controller_address: Optional[str] = None
    
    async def initialize_service(self,
                               order_contract_address: str,
                               agent_controller_private_key: Optional[str] = None,
                               pyusd_token_address: Optional[str] = None) -> bool:
        """
        Initialize the OrderContract service with contract details
        
        Args:
            order_contract_address: Deployed OrderContract address
            agent_controller_private_key: Agent controller private key
            pyusd_token_address: pyUSD token address (optional, uses default)
            
        Returns:
            True if initialization successful
        """
        try:
            # Set addresses
            self.order_contract_address = order_contract_address
            if pyusd_token_address:
                self.pyusd_token_address = pyusd_token_address
            
            # Load ABIs
            order_abi = self._load_order_contract_abi()
            erc20_abi = self._load_erc20_abi()
            
            # Initialize contract manager
            provider_url = get_provider_url()
            self.contract_manager = OrderContractManager(
                provider_url=provider_url,
                order_contract_address=order_contract_address,
                pyusd_token_address=self.pyusd_token_address,
                order_contract_abi=order_abi,
                erc20_abi=erc20_abi,
                agent_controller_private_key=agent_controller_private_key
            )
            
            # Get agent controller address
            self.agent_controller_address = self.contract_manager.get_agent_controller()
            
            # Initialize event listener
            self.event_listener = OrderEventListener(self.contract_manager)
            
            # Initialize agent bridge
            if self.agent_controller_address:
                self.agent_bridge = AgentOrderBridge(
                    self.contract_manager,
                    self.event_listener,
                    self.agent_controller_address
                )
            
            # Start event listening
            self.event_listener.start_listening()
            
            self._initialized = True
            logger.info("OrderContract service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OrderContract service: {str(e)}")
            self._initialized = False
            return False
    
    def _load_order_contract_abi(self) -> List[Dict]:
        """Load OrderContract ABI"""
        try:
            with open('/Users/vickzmacbook/Documents/Sites/backend/blockchain/OrderContract_ABI.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading OrderContract ABI: {str(e)}")
            raise
    
    def _load_erc20_abi(self) -> List[Dict]:
        """Load ERC20 ABI"""
        try:
            with open('/Users/vickzmacbook/Documents/Sites/backend/blockchain/ERC20_ABI.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ERC20 ABI: {str(e)}")
            raise
    
    def _ensure_initialized(self):
        """Ensure service is initialized"""
        if not self._initialized or not self.contract_manager:
            raise ContractNotInitializedException("OrderContract service not initialized")
    
    # ========== USER ORDER FUNCTIONS ==========
    
    async def create_user_order(self, user_address: str, prompt: str) -> Dict[str, Any]:
        """
        Create a new order for a user
        
        Args:
            user_address: User's Ethereum address
            prompt: User's prompt/request
            
        Returns:
            Order creation result
        """
        self._ensure_initialized()
        
        try:
            # Use agent bridge if available for better tracking
            if self.agent_bridge:
                request = await self.agent_bridge.process_user_order_request(user_address, prompt)
                return {
                    'success': True,
                    'order_id': request.order_id,
                    'request_id': request.request_id,
                    'prompt_hash': self.contract_manager.create_prompt_hash(prompt),
                    'status': 'InProgress',
                    'message': 'Order created successfully'
                }
            else:
                # Direct contract interaction
                order_id, tx_hash = self.contract_manager.propose_order(prompt, user_address)
                return {
                    'success': True,
                    'order_id': order_id,
                    'transaction_hash': tx_hash,
                    'prompt_hash': self.contract_manager.create_prompt_hash(prompt),
                    'status': 'InProgress',
                    'message': 'Order created successfully'
                }
                
        except Exception as e:
            logger.error(f"Error creating user order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create order'
            }
    
    async def confirm_user_order(self, user_address: str, order_id: str) -> Dict[str, Any]:
        """
        Confirm and pay for an order
        
        Args:
            user_address: User's Ethereum address
            order_id: Order ID to confirm
            
        Returns:
            Confirmation result
        """
        self._ensure_initialized()
        
        try:
            tx_hash = self.contract_manager.confirm_order(order_id, user_address)
            return {
                'success': True,
                'order_id': order_id,
                'transaction_hash': tx_hash,
                'status': 'Confirmed',
                'message': 'Order confirmed and payment processed'
            }
            
        except Exception as e:
            logger.error(f"Error confirming order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to confirm order'
            }
    
    async def cancel_user_order(self, user_address: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order and get refund
        
        Args:
            user_address: User's Ethereum address
            order_id: Order ID to cancel
            
        Returns:
            Cancellation result
        """
        self._ensure_initialized()
        
        try:
            tx_hash = self.contract_manager.cancel_order(order_id, user_address)
            return {
                'success': True,
                'order_id': order_id,
                'transaction_hash': tx_hash,
                'status': 'Cancelled',
                'message': 'Order cancelled and refund processed'
            }
            
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cancel order'
            }
    
    # ========== AGENT FUNCTIONS ==========
    
    async def agent_propose_answer(self, order_id: str, answer: str, price_pyusd: float) -> Dict[str, Any]:
        """
        Agent proposes an answer to an order
        
        Args:
            order_id: Order ID to answer
            answer: Agent's answer
            price_pyusd: Price in pyUSD
            
        Returns:
            Proposal result
        """
        self._ensure_initialized()
        
        try:
            if self.agent_bridge:
                response = await self.agent_bridge.agent_propose_answer(order_id, answer, price_pyusd)
                return {
                    'success': True,
                    'order_id': order_id,
                    'request_id': response.request_id,
                    'answer_hash': response.answer_hash,
                    'price_pyusd': price_pyusd,
                    'status': 'Proposed',
                    'message': 'Answer proposed successfully'
                }
            else:
                tx_hash = self.contract_manager.propose_order_answer(order_id, answer, price_pyusd)
                return {
                    'success': True,
                    'order_id': order_id,
                    'transaction_hash': tx_hash,
                    'answer_hash': self.contract_manager.create_answer_hash(answer),
                    'price_pyusd': price_pyusd,
                    'status': 'Proposed',
                    'message': 'Answer proposed successfully'
                }
                
        except Exception as e:
            logger.error(f"Error proposing answer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to propose answer'
            }
    
    async def agent_finalize_order(self, order_id: str) -> Dict[str, Any]:
        """
        Agent finalizes a completed order
        
        Args:
            order_id: Order ID to finalize
            
        Returns:
            Finalization result
        """
        self._ensure_initialized()
        
        try:
            if self.agent_bridge:
                tx_hash = await self.agent_bridge.finalize_completed_order(order_id)
            else:
                tx_hash = self.contract_manager.finalize_order(order_id)
                
            return {
                'success': True,
                'order_id': order_id,
                'transaction_hash': tx_hash,
                'status': 'Completed',
                'message': 'Order finalized and payment released'
            }
            
        except Exception as e:
            logger.error(f"Error finalizing order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to finalize order'
            }
    
    # ========== QUERY FUNCTIONS ==========
    
    def get_user_orders(self, user_address: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all orders for a user
        
        Args:
            user_address: User's Ethereum address
            status_filter: Optional status filter
            
        Returns:
            User orders
        """
        self._ensure_initialized()
        
        try:
            if status_filter:
                # Filter by specific status
                status_enum = OrderStatus[status_filter.upper()]
                order_ids = self.contract_manager.get_user_orders_by_status(user_address, status_enum)
                orders = []
                
                for order_id in order_ids:
                    order_details = self.contract_manager.get_user_order_details(user_address, order_id)
                    orders.append(self._format_order_details(order_details))
            else:
                # Get all orders
                order_ids, statuses = self.contract_manager.get_user_orders_with_status(user_address)
                orders = []
                
                for i, order_id in enumerate(order_ids):
                    order_details = self.contract_manager.get_user_order_details(user_address, order_id)
                    orders.append(self._format_order_details(order_details))
            
            return {
                'success': True,
                'user_address': user_address,
                'total_orders': len(orders),
                'orders': orders
            }
            
        except Exception as e:
            logger.error(f"Error getting user orders: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve user orders'
            }
    
    def get_order_details(self, order_id: str, user_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about an order
        
        Args:
            order_id: Order ID
            user_address: User address (for user-specific details)
            
        Returns:
            Order details
        """
        self._ensure_initialized()
        
        try:
            if user_address:
                order_details = self.contract_manager.get_user_order_details(user_address, order_id)
            else:
                order_details = self.contract_manager.get_order_details_by_id(order_id)
            
            # Add agent bridge info if available
            additional_info = {}
            if self.agent_bridge:
                try:
                    status_info = self.agent_bridge.get_order_status(order_id)
                    additional_info['agent_tracking'] = status_info.get('local_tracking', {})
                except:
                    pass
            
            return {
                'success': True,
                'order_details': self._format_order_details(order_details),
                'additional_info': additional_info
            }
            
        except Exception as e:
            logger.error(f"Error getting order details: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve order details'
            }
    
    def get_pyusd_info(self, user_address: str) -> Dict[str, Any]:
        """
        Get pyUSD balance and allowance information
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            pyUSD information
        """
        self._ensure_initialized()
        
        try:
            balance = self.contract_manager.get_pyusd_balance(user_address)
            allowance = self.contract_manager.get_pyusd_allowance(user_address, self.order_contract_address)
            agent_fee = self.contract_manager.get_agent_fee()
            
            return {
                'success': True,
                'user_address': user_address,
                'pyusd_balance': balance,
                'allowance': allowance,
                'agent_fee': agent_fee,
                'pyusd_token_address': self.pyusd_token_address,
                'order_contract_address': self.order_contract_address
            }
            
        except Exception as e:
            logger.error(f"Error getting pyUSD info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve pyUSD information'
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service status and information"""
        try:
            info = {
                'success': True,
                'initialized': self._initialized,
                'service_status': 'active' if self._initialized else 'inactive'
            }
            
            if self._initialized and self.contract_manager:
                contract_info = self.contract_manager.get_contract_info()
                info.update(contract_info)
                
                # Add agent bridge stats if available
                if self.agent_bridge:
                    agent_stats = self.agent_bridge.get_agent_stats()
                    info['agent_stats'] = agent_stats
                
                # Add event listener status
                if self.event_listener:
                    info['event_listener_active'] = self.event_listener.is_listening
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve service information'
            }
    
    def _format_order_details(self, order_details: OrderDetails) -> Dict[str, Any]:
        """Format order details for API response"""
        return {
            'order_id': order_details.order_id,
            'buyer': order_details.buyer,
            'prompt_hash': order_details.prompt_hash,
            'answer_hash': order_details.answer_hash,
            'price_pyusd': order_details.price,
            'paid_pyusd': order_details.paid,
            'timestamp': order_details.timestamp.isoformat(),
            'status': order_details.status_name,
            'status_code': order_details.status.value
        }
    
    # ========== EVENT FUNCTIONS ==========
    
    def subscribe_to_user_events(self, user_address: str, callback: callable) -> UserEventSubscription:
        """
        Subscribe to events for a specific user
        
        Args:
            user_address: User address to subscribe to
            callback: Callback function for events
            
        Returns:
            UserEventSubscription object
        """
        self._ensure_initialized()
        
        if not self.event_listener:
            raise ValueError("Event listener not available")
        
        subscription = UserEventSubscription(self.event_listener, user_address)
        subscription.subscribe_to_user_events(callback)
        return subscription
    
    def get_user_event_history(self, user_address: str, from_block: int = 0) -> List[Dict[str, Any]]:
        """
        Get historical events for a user
        
        Args:
            user_address: User address
            from_block: Starting block number
            
        Returns:
            List of events
        """
        self._ensure_initialized()
        
        if not self.event_listener:
            return []
        
        subscription = UserEventSubscription(self.event_listener, user_address)
        events = subscription.get_user_event_history(from_block)
        
        return [
            {
                'event_type': event.event_type,
                'user': event.user,
                'order_id': event.order_id,
                'transaction_hash': event.transaction_hash,
                'block_number': event.block_number,
                'additional_data': event.additional_data
            }
            for event in events
        ]
    
    def stop_service(self):
        """Stop the service and clean up resources"""
        if self.event_listener:
            self.event_listener.stop_listening()
        
        self._initialized = False
        logger.info("OrderContract service stopped")

# Global service instance
order_contract_service = OrderContractService()