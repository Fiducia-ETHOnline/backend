"""
ASI Agent integration with OrderContract
This module connects the uAgent system with the smart contract functionality
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from uagents import Context
from .agent_bridge import AgentOrderBridge, AgentMessage, AgentOrderRequest, AgentOrderResponse
from .order_service import order_contract_service

logger = logging.getLogger(__name__)

class AgentContractInterface:
    """
    Interface between ASI agents and the OrderContract
    Handles agent-specific operations and message routing
    """
    
    def __init__(self, agent_address: str):
        """
        Initialize agent contract interface
        
        Args:
            agent_address: Agent's address/identifier
        """
        self.agent_address = agent_address
        self.bridge: Optional[AgentOrderBridge] = None
        self.pending_operations: Dict[str, Dict[str, Any]] = {}
        
    async def initialize_bridge(self) -> bool:
        """Initialize the agent bridge connection"""
        try:
            # Ensure the order contract service is initialized
            if not order_contract_service._initialized:
                logger.error("OrderContract service not initialized")
                return False
            
            # Get the bridge from the service
            self.bridge = order_contract_service.agent_bridge
            
            if not self.bridge:
                logger.error("Agent bridge not available in order contract service")
                return False
            
            # Set up message callbacks
            self.bridge.add_message_callback('order_request', self._handle_order_request)
            self.bridge.add_message_callback('status_update', self._handle_status_update)
            
            logger.info(f"Agent contract interface initialized for {self.agent_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing agent bridge: {str(e)}")
            return False
    
    async def process_user_prompt(self, user_address: str, prompt: str, ctx: Context) -> Dict[str, Any]:
        """
        Process a user prompt and create an order
        
        Args:
            user_address: User's Ethereum address
            prompt: User's prompt/request
            ctx: uAgent context
            
        Returns:
            Processing result
        """
        try:
            if not self.bridge:
                await self.initialize_bridge()
                if not self.bridge:
                    raise Exception("Agent bridge not available")
            
            # Create order request
            request = await self.bridge.process_user_order_request(user_address, prompt)
            
            # Store for tracking
            operation_id = f"prompt_{request.request_id}"
            self.pending_operations[operation_id] = {
                'type': 'user_prompt',
                'request': request,
                'user_address': user_address,
                'prompt': prompt,
                'created_at': datetime.now(),
                'status': 'processing'
            }
            
            # Log the operation
            ctx.logger.info(f"Processing user prompt for {user_address}, order ID: {request.order_id}")
            
            return {
                'success': True,
                'operation_id': operation_id,
                'order_id': request.order_id,
                'request_id': request.request_id,
                'status': request.status,
                'message': 'Order created successfully, waiting for agent response'
            }
            
        except Exception as e:
            logger.error(f"Error processing user prompt: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process user prompt'
            }
    
    async def generate_agent_response(self, order_id: str, answer: str, price_pyusd: float, ctx: Context) -> Dict[str, Any]:
        """
        Generate agent response to an order
        
        Args:
            order_id: Order ID to respond to
            answer: Agent's answer
            price_pyusd: Price in pyUSD
            ctx: uAgent context
            
        Returns:
            Response result
        """
        try:
            if not self.bridge:
                await self.initialize_bridge()
                if not self.bridge:
                    raise Exception("Agent bridge not available")
            
            # Propose answer
            response = await self.bridge.agent_propose_answer(order_id, answer, price_pyusd)
            
            # Store for tracking
            operation_id = f"response_{response.request_id}"
            self.pending_operations[operation_id] = {
                'type': 'agent_response',
                'response': response,
                'order_id': order_id,
                'answer': answer,
                'price_pyusd': price_pyusd,
                'created_at': datetime.now(),
                'status': 'proposed'
            }
            
            # Log the operation
            ctx.logger.info(f"Agent response proposed for order {order_id}, price: {price_pyusd} pyUSD")
            
            return {
                'success': True,
                'operation_id': operation_id,
                'order_id': order_id,
                'request_id': response.request_id,
                'answer_hash': response.answer_hash,
                'price_pyusd': price_pyusd,
                'status': response.status,
                'message': 'Answer proposed successfully, waiting for user confirmation'
            }
            
        except Exception as e:
            logger.error(f"Error generating agent response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate agent response'
            }
    
    async def finalize_completed_order(self, order_id: str, ctx: Context) -> Dict[str, Any]:
        """
        Finalize a completed order
        
        Args:
            order_id: Order ID to finalize
            ctx: uAgent context
            
        Returns:
            Finalization result
        """
        try:
            if not self.bridge:
                await self.initialize_bridge()
                if not self.bridge:
                    raise Exception("Agent bridge not available")
            
            # Finalize order
            tx_hash = await self.bridge.finalize_completed_order(order_id)
            
            # Update tracking
            for op_id, operation in self.pending_operations.items():
                if operation.get('order_id') == order_id:
                    operation['status'] = 'completed'
                    operation['finalized_at'] = datetime.now()
                    operation['finalize_tx_hash'] = tx_hash
                    break
            
            # Log the operation
            ctx.logger.info(f"Order {order_id} finalized, transaction: {tx_hash}")
            
            return {
                'success': True,
                'order_id': order_id,
                'transaction_hash': tx_hash,
                'status': 'completed',
                'message': 'Order finalized successfully, payment released'
            }
            
        except Exception as e:
            logger.error(f"Error finalizing order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to finalize order'
            }
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending operations for this agent"""
        if not self.bridge:
            return []
        
        pending_requests = self.bridge.get_pending_requests()
        pending_responses = self.bridge.get_pending_responses()
        
        orders = []
        
        # Add pending requests (orders waiting for agent response)
        for request in pending_requests:
            orders.append({
                'order_id': request.order_id,
                'request_id': request.request_id,
                'user_address': request.user_address,
                'prompt': request.prompt,
                'status': request.status,
                'type': 'awaiting_response',
                'created_at': request.created_at.isoformat()
            })
        
        # Add pending responses (orders waiting for user confirmation or completion)
        for response in pending_responses:
            orders.append({
                'order_id': response.order_id,
                'request_id': response.request_id,
                'answer': response.answer,
                'price_pyusd': response.price_pyusd,
                'status': response.status,
                'type': 'awaiting_confirmation',
                'created_at': response.created_at.isoformat()
            })
        
        return orders
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        if not self.bridge:
            return {
                'agent_address': self.agent_address,
                'bridge_connected': False,
                'total_operations': len(self.pending_operations)
            }
        
        bridge_stats = self.bridge.get_agent_stats()
        return {
            **bridge_stats,
            'local_operations': len(self.pending_operations),
            'bridge_connected': True
        }
    
    def _handle_order_request(self, message: AgentMessage):
        """Handle incoming order request messages"""
        logger.info(f"New order request: {message.data.get('order_id')} from {message.sender}")
        
        # Here you could trigger agent processing logic
        # For example, send the order to an AI model for processing
        order_id = message.data.get('order_id')
        prompt = message.data.get('prompt')
        
        # Store the request for processing
        self.pending_operations[f"incoming_{order_id}"] = {
            'type': 'incoming_request',
            'order_id': order_id,
            'user_address': message.sender,
            'prompt': prompt,
            'received_at': datetime.now(),
            'status': 'received'
        }
    
    def _handle_status_update(self, message: AgentMessage):
        """Handle status update messages"""
        logger.info(f"Status update for order {message.data.get('order_id')}: {message.data.get('status')}")
        
        # Update local tracking
        order_id = message.data.get('order_id')
        new_status = message.data.get('status')
        
        for operation in self.pending_operations.values():
            if operation.get('order_id') == order_id:
                operation['status'] = new_status
                operation['last_update'] = datetime.now()
                break

# Global agent interface instances
agent_interfaces: Dict[str, AgentContractInterface] = {}

def get_agent_interface(agent_address: str) -> AgentContractInterface:
    """
    Get or create agent interface for a specific agent
    
    Args:
        agent_address: Agent's address/identifier
        
    Returns:
        AgentContractInterface instance
    """
    if agent_address not in agent_interfaces:
        agent_interfaces[agent_address] = AgentContractInterface(agent_address)
    
    return agent_interfaces[agent_address]

async def initialize_agent_interfaces():
    """Initialize all agent interfaces"""
    for interface in agent_interfaces.values():
        await interface.initialize_bridge()

# Helper functions for direct use in uAgent handlers
async def agent_process_user_request(agent_address: str, user_address: str, prompt: str, ctx: Context) -> Dict[str, Any]:
    """Convenience function for processing user requests"""
    interface = get_agent_interface(agent_address)
    return await interface.process_user_prompt(user_address, prompt, ctx)

async def agent_respond_to_order(agent_address: str, order_id: str, answer: str, price_pyusd: float, ctx: Context) -> Dict[str, Any]:
    """Convenience function for agent responses"""
    interface = get_agent_interface(agent_address)
    return await interface.generate_agent_response(order_id, answer, price_pyusd, ctx)

async def agent_finalize_order(agent_address: str, order_id: str, ctx: Context) -> Dict[str, Any]:
    """Convenience function for finalizing orders"""
    interface = get_agent_interface(agent_address)
    return await interface.finalize_completed_order(order_id, ctx)