"""
ASI Agent integration bridge for OrderContract communication

This module provides the communication bridge between uAgents and the OrderContract,
enabling agents to interact with the smart contract for order management.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

from .order_contract import OrderContractManager, OrderStatus, OrderDetails
from .event_listener import OrderEventListener, OrderEvent
from .utils import is_valid_ethereum_address

logger = logging.getLogger(__name__)

@dataclass
class AgentOrderRequest:
    """Data class for agent order requests"""
    request_id: str
    user_address: str
    prompt: str
    order_id: Optional[str] = None
    status: str = "pending"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AgentOrderResponse:
    """Data class for agent order responses"""
    request_id: str
    order_id: str
    answer: str
    price_pyusd: float
    answer_hash: str
    status: str = "proposed"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AgentMessage:
    """Data class for agent messages"""
    message_type: str  # 'order_request', 'order_response', 'status_update', 'event_notification'
    sender: str
    recipient: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AgentOrderBridge:
    """
    Bridge between ASI agents and OrderContract
    Handles communication and order management for agents
    """
    
    def __init__(self, 
                 order_contract_manager: OrderContractManager,
                 event_listener: OrderEventListener,
                 agent_address: str):
        """
        Initialize agent bridge
        
        Args:
            order_contract_manager: OrderContract manager instance
            event_listener: Event listener instance
            agent_address: Agent's blockchain address
        """
        self.contract_manager = order_contract_manager
        self.event_listener = event_listener
        self.agent_address = agent_address
        
        # Storage for pending requests and responses
        self.pending_requests: Dict[str, AgentOrderRequest] = {}
        self.pending_responses: Dict[str, AgentOrderResponse] = {}
        self.completed_orders: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks for different message types
        self.message_callbacks: Dict[str, List[Callable]] = {
            'order_request': [],
            'order_response': [],
            'status_update': [],
            'event_notification': []
        }
        
        # Set up event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up event listeners for contract events"""
        self.event_listener.add_event_callback('OrderProposed', self._handle_order_proposed)
        self.event_listener.add_event_callback('OrderConfirmed', self._handle_order_confirmed)
        self.event_listener.add_event_callback('orderFinalized', self._handle_order_finalized)
    
    def add_message_callback(self, message_type: str, callback: Callable[[AgentMessage], None]):
        """
        Add callback for specific message type
        
        Args:
            message_type: Type of message to listen for
            callback: Callback function
        """
        if message_type not in self.message_callbacks:
            self.message_callbacks[message_type] = []
        self.message_callbacks[message_type].append(callback)
    
    def _notify_callbacks(self, message_type: str, message: AgentMessage):
        """Notify all callbacks for a message type"""
        if message_type in self.message_callbacks:
            for callback in self.message_callbacks[message_type]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in message callback: {str(e)}")
    
    # ========== ORDER REQUEST HANDLING ==========
    
    async def process_user_order_request(self, 
                                       user_address: str, 
                                       prompt: str, 
                                       request_id: Optional[str] = None) -> AgentOrderRequest:
        """
        Process a new order request from a user
        
        Args:
            user_address: User's Ethereum address
            prompt: User's prompt/request
            request_id: Optional request ID (auto-generated if not provided)
            
        Returns:
            AgentOrderRequest object
        """
        if not is_valid_ethereum_address(user_address):
            raise ValueError(f"Invalid Ethereum address: {user_address}")
        
        if not request_id:
            request_id = f"req_{int(datetime.now().timestamp())}_{user_address[:8]}"
        
        # Create order request
        order_request = AgentOrderRequest(
            request_id=request_id,
            user_address=user_address,
            prompt=prompt,
            status="processing"
        )
        
        try:
            # Create order on blockchain (user function)
            order_id, tx_hash = self.contract_manager.propose_order(prompt, user_address)
            order_request.order_id = order_id
            order_request.status = "created"
            
            # Store request
            self.pending_requests[request_id] = order_request
            
            # Notify agent about new order request
            message = AgentMessage(
                message_type='order_request',
                sender=user_address,
                recipient=self.agent_address,
                data={
                    'request_id': request_id,
                    'order_id': order_id,
                    'user_address': user_address,
                    'prompt': prompt,
                    'transaction_hash': tx_hash,
                    'status': 'created'
                }
            )
            
            self._notify_callbacks('order_request', message)
            
            logger.info(f"Processed order request {request_id} -> order {order_id}")
            return order_request
            
        except Exception as e:
            order_request.status = "failed"
            logger.error(f"Error processing order request: {str(e)}")
            raise
    
    async def agent_propose_answer(self, 
                                 order_id: str, 
                                 answer: str, 
                                 price_pyusd: float,
                                 seller_address: str,
                                 request_id: Optional[str] = None) -> AgentOrderResponse:
        """
        Agent proposes an answer for an order
        
        Args:
            order_id: Order ID to answer
            answer: Agent's answer/response
            price_pyusd: Price in pyUSD
            request_id: Related request ID (optional)
            
        Returns:
            AgentOrderResponse object
        """
        if not request_id:
            request_id = f"resp_{int(datetime.now().timestamp())}_{order_id}"
        
        try:
            # Create answer hash
            answer_hash = self.contract_manager.create_answer_hash(answer)
            
            # Propose answer on blockchain
            tx_hash = self.contract_manager.propose_order_answer(order_id, answer, price_pyusd, seller_address)
            
            # Create response object
            order_response = AgentOrderResponse(
                request_id=request_id,
                order_id=order_id,
                answer=answer,
                price_pyusd=price_pyusd,
                answer_hash=answer_hash,
                status="proposed"
            )
            
            # Store response
            self.pending_responses[request_id] = order_response
            
            # Get order details to find user
            order_details = self.contract_manager.get_order_details_by_id(order_id)
            
            # Notify user about agent response
            message = AgentMessage(
                message_type='order_response',
                sender=self.agent_address,
                recipient=order_details.buyer,
                data={
                    'request_id': request_id,
                    'order_id': order_id,
                    'answer': answer,
                    'price_pyusd': price_pyusd,
                    'answer_hash': answer_hash,
                    'transaction_hash': tx_hash,
                    'status': 'proposed'
                }
            )
            
            self._notify_callbacks('order_response', message)
            
            logger.info(f"Agent proposed answer for order {order_id}")
            return order_response
            
        except Exception as e:
            logger.error(f"Error proposing answer for order {order_id}: {str(e)}")
            raise
    
    async def finalize_completed_order(self, order_id: str) -> str:
        """
        Finalize a completed order (agent function)
        
        Args:
            order_id: Order ID to finalize
            
        Returns:
            Transaction hash
        """
        try:
            tx_hash = self.contract_manager.finalize_order(order_id)
            
            # Move to completed orders
            if order_id in self.pending_responses:
                response = self.pending_responses.pop(order_id)
                self.completed_orders[order_id] = {
                    'response': asdict(response),
                    'finalized_at': datetime.now(),
                    'finalize_tx_hash': tx_hash
                }
            
            logger.info(f"Finalized order {order_id}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error finalizing order {order_id}: {str(e)}")
            raise
    
    # ========== EVENT HANDLERS ==========
    
    def _handle_order_proposed(self, event: OrderEvent):
        """Handle OrderProposed event"""
        logger.info(f"Order proposed: {event.order_id} by {event.user}")
        
        # Update pending request status if it exists
        for request_id, request in self.pending_requests.items():
            if request.order_id == event.order_id:
                request.status = "proposed"
                break
        
        # Notify about status update
        message = AgentMessage(
            message_type='status_update',
            sender='system',
            recipient=self.agent_address,
            data={
                'order_id': event.order_id,
                'user': event.user,
                'status': 'proposed',
                'event_type': 'OrderProposed',
                'transaction_hash': event.transaction_hash,
                'additional_data': event.additional_data
            }
        )
        
        self._notify_callbacks('status_update', message)
    
    def _handle_order_confirmed(self, event: OrderEvent):
        """Handle OrderConfirmed event"""
        logger.info(f"Order confirmed: {event.order_id} by {event.user}")
        
        # Update pending response status if it exists
        for request_id, response in self.pending_responses.items():
            if response.order_id == event.order_id:
                response.status = "confirmed"
                break
        
        # Notify about status update
        message = AgentMessage(
            message_type='status_update',
            sender='system',
            recipient=self.agent_address,
            data={
                'order_id': event.order_id,
                'user': event.user,
                'status': 'confirmed',
                'event_type': 'OrderConfirmed',
                'transaction_hash': event.transaction_hash,
                'additional_data': event.additional_data
            }
        )
        
        self._notify_callbacks('status_update', message)
    
    def _handle_order_finalized(self, event: OrderEvent):
        """Handle orderFinalized event"""
        logger.info(f"Order finalized: {event.order_id} by {event.user}")
        
        # Move to completed orders
        for request_id, response in list(self.pending_responses.items()):
            if response.order_id == event.order_id:
                self.completed_orders[event.order_id] = {
                    'response': asdict(response),
                    'finalized_at': datetime.now(),
                    'finalize_tx_hash': event.transaction_hash
                }
                del self.pending_responses[request_id]
                break
        
        # Notify about completion
        message = AgentMessage(
            message_type='status_update',
            sender='system',
            recipient=self.agent_address,
            data={
                'order_id': event.order_id,
                'user': event.user,
                'status': 'completed',
                'event_type': 'orderFinalized',
                'transaction_hash': event.transaction_hash,
                'additional_data': event.additional_data
            }
        )
        
        self._notify_callbacks('status_update', message)
    
    # ========== QUERY AND STATUS FUNCTIONS ==========
    
    def get_pending_requests(self) -> List[AgentOrderRequest]:
        """Get all pending order requests"""
        return list(self.pending_requests.values())
    
    def get_pending_responses(self) -> List[AgentOrderResponse]:
        """Get all pending responses"""
        return list(self.pending_responses.values())
    
    def get_completed_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed orders"""
        return self.completed_orders.copy()
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get comprehensive order status
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Order status information
        """
        try:
            # Get contract details
            order_details = self.contract_manager.get_order_details_by_id(order_id)
            
            # Check if we have local tracking info
            local_info = {}
            
            # Check pending requests
            for request_id, request in self.pending_requests.items():
                if request.order_id == order_id:
                    local_info['request'] = asdict(request)
                    break
            
            # Check pending responses
            for request_id, response in self.pending_responses.items():
                if response.order_id == order_id:
                    local_info['response'] = asdict(response)
                    break
            
            # Check completed orders
            if order_id in self.completed_orders:
                local_info['completed'] = self.completed_orders[order_id]
            
            return {
                'order_id': order_id,
                'contract_details': asdict(order_details),
                'local_tracking': local_info,
                'contract_status': order_details.status_name,
                'contract_status_code': order_details.status.value
            }
            
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            raise
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            'agent_address': self.agent_address,
            'pending_requests': len(self.pending_requests),
            'pending_responses': len(self.pending_responses),
            'completed_orders': len(self.completed_orders),
            'total_orders_processed': (
                len(self.pending_requests) + 
                len(self.pending_responses) + 
                len(self.completed_orders)
            )
        }

class AgentMessageQueue:
    """
    Message queue system for agent communication
    """
    
    def __init__(self):
        """Initialize message queue"""
        self.queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[str]] = {}
    
    async def create_queue(self, queue_name: str) -> asyncio.Queue:
        """Create a new message queue"""
        if queue_name not in self.queues:
            self.queues[queue_name] = asyncio.Queue()
        return self.queues[queue_name]
    
    async def send_message(self, queue_name: str, message: AgentMessage):
        """Send message to a queue"""
        if queue_name not in self.queues:
            await self.create_queue(queue_name)
        
        await self.queues[queue_name].put(message)
        logger.debug(f"Message sent to queue {queue_name}: {message.message_type}")
    
    async def receive_message(self, queue_name: str, timeout: Optional[float] = None) -> AgentMessage:
        """Receive message from a queue"""
        if queue_name not in self.queues:
            await self.create_queue(queue_name)
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.queues[queue_name].get(), 
                    timeout=timeout
                )
            else:
                message = await self.queues[queue_name].get()
            
            logger.debug(f"Message received from queue {queue_name}: {message.message_type}")
            return message
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"No message received from queue {queue_name} within {timeout} seconds")
    
    async def subscribe_to_messages(self, 
                                  queue_name: str, 
                                  callback: Callable[[AgentMessage], None]):
        """
        Subscribe to messages from a queue with callback
        
        Args:
            queue_name: Queue to subscribe to
            callback: Callback function for messages
        """
        if queue_name not in self.subscribers:
            self.subscribers[queue_name] = []
        
        # Start listening in background
        async def message_listener():
            while True:
                try:
                    message = await self.receive_message(queue_name)
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in message subscriber: {str(e)}")
                    await asyncio.sleep(1)
        
        asyncio.create_task(message_listener())
        logger.info(f"Subscribed to messages from queue: {queue_name}")
    
    def get_queue_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all queues"""
        stats = {}
        for queue_name, queue in self.queues.items():
            stats[queue_name] = {
                'pending_messages': queue.qsize(),
                'subscribers': len(self.subscribers.get(queue_name, []))
            }
        return stats