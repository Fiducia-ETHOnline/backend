"""
Event listening system for OrderContract real-time updates
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List
from web3 import Web3
from web3.contract import Contract
from threading import Thread
import json
from datetime import datetime

from .order_contract import OrderContractManager, OrderStatus, OrderEvent
from .utils import wei_to_eth

logger = logging.getLogger(__name__)

class OrderEventListener:
    """
    Event listener for OrderContract events with real-time notifications
    """
    
    def __init__(self, order_contract_manager: OrderContractManager):
        """
        Initialize event listener
        
        Args:
            order_contract_manager: OrderContractManager instance
        """
        self.contract_manager = order_contract_manager
        self.w3 = order_contract_manager.w3
        self.contract = order_contract_manager.order_contract
        self.listeners = {}
        self.is_listening = False
        self.event_filters = {}
        
    def add_event_callback(self, event_type: str, callback: Callable[[OrderEvent], None]):
        """
        Add callback for specific event type
        
        Args:
            event_type: Event type ('OrderProposed', 'OrderConfirmed', 'orderFinalized', 'all')
            callback: Callback function to execute when event is received
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        logger.info(f"Added callback for {event_type} events")
    
    def remove_event_callback(self, event_type: str, callback: Callable[[OrderEvent], None]):
        """Remove callback for specific event type"""
        if event_type in self.listeners:
            if callback in self.listeners[event_type]:
                self.listeners[event_type].remove(callback)
    
    def _create_event_filters(self):
        """Create event filters for all contract events"""
        try:
            # OrderProposed events
            self.event_filters['OrderProposed'] = self.contract.events.OrderProposed.create_filter(
                fromBlock='latest'
            )
            
            # OrderConfirmed events
            self.event_filters['OrderConfirmed'] = self.contract.events.OrderConfirmed.create_filter(
                fromBlock='latest'
            )
            
            # orderFinalized events
            self.event_filters['orderFinalized'] = self.contract.events.orderFinalized.create_filter(
                fromBlock='latest'
            )
            
            logger.info("Created event filters for all OrderContract events")
            
        except Exception as e:
            logger.error(f"Error creating event filters: {str(e)}")
            raise
    
    def _process_order_proposed_event(self, event):
        """Process OrderProposed event"""
        try:
            args = event['args']
            order_event = OrderEvent(
                event_type='OrderProposed',
                user=args['user'],
                order_id=str(args['offerId']),
                transaction_hash=event['transactionHash'].hex(),
                block_number=event['blockNumber'],
                additional_data={
                    'prompt_hash': args['promptHash'].hex(),
                    'status': 'InProgress',
                    'status_code': OrderStatus.IN_PROGRESS.value
                }
            )
            
            self._notify_callbacks('OrderProposed', order_event)
            self._notify_callbacks('all', order_event)
            
        except Exception as e:
            logger.error(f"Error processing OrderProposed event: {str(e)}")
    
    def _process_order_confirmed_event(self, event):
        """Process OrderConfirmed event"""
        try:
            args = event['args']
            order_event = OrderEvent(
                event_type='OrderConfirmed',
                user=args['user'],
                order_id=str(args['offerId']),
                transaction_hash=event['transactionHash'].hex(),
                block_number=event['blockNumber'],
                additional_data={
                    'amount_paid': wei_to_eth(args['amountPaid']),
                    'amount_paid_wei': args['amountPaid'],
                    'status': 'Confirmed',
                    'status_code': OrderStatus.CONFIRMED.value
                }
            )
            
            self._notify_callbacks('OrderConfirmed', order_event)
            self._notify_callbacks('all', order_event)
            
        except Exception as e:
            logger.error(f"Error processing OrderConfirmed event: {str(e)}")
    
    def _process_order_finalized_event(self, event):
        """Process orderFinalized event"""
        try:
            args = event['args']
            order_event = OrderEvent(
                event_type='orderFinalized',
                user=args['user'],
                order_id=str(args['offerId']),
                transaction_hash=event['transactionHash'].hex(),
                block_number=event['blockNumber'],
                additional_data={
                    'status': 'Completed',
                    'status_code': OrderStatus.COMPLETED.value
                }
            )
            
            self._notify_callbacks('orderFinalized', order_event)
            self._notify_callbacks('all', order_event)
            
        except Exception as e:
            logger.error(f"Error processing orderFinalized event: {str(e)}")
    
    def _notify_callbacks(self, event_type: str, order_event: OrderEvent):
        """Notify all callbacks for a specific event type"""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(order_event)
                except Exception as e:
                    logger.error(f"Error in event callback: {str(e)}")
    
    def _listen_for_events(self):
        """Main event listening loop"""
        logger.info("Starting event listening loop")
        
        while self.is_listening:
            try:
                # Check OrderProposed events
                if 'OrderProposed' in self.event_filters:
                    for event in self.event_filters['OrderProposed'].get_new_entries():
                        self._process_order_proposed_event(event)
                
                # Check OrderConfirmed events
                if 'OrderConfirmed' in self.event_filters:
                    for event in self.event_filters['OrderConfirmed'].get_new_entries():
                        self._process_order_confirmed_event(event)
                
                # Check orderFinalized events
                if 'orderFinalized' in self.event_filters:
                    for event in self.event_filters['orderFinalized'].get_new_entries():
                        self._process_order_finalized_event(event)
                
                # Sleep to prevent excessive polling
                asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in event listening loop: {str(e)}")
                asyncio.sleep(5)  # Wait longer if there's an error
    
    def start_listening(self):
        """Start listening for events"""
        if self.is_listening:
            logger.warning("Event listener is already running")
            return
        
        try:
            self._create_event_filters()
            self.is_listening = True
            
            # Start listening in a separate thread
            self.listener_thread = Thread(target=self._listen_for_events, daemon=True)
            self.listener_thread.start()
            
            logger.info("Event listener started successfully")
            
        except Exception as e:
            logger.error(f"Error starting event listener: {str(e)}")
            self.is_listening = False
            raise
    
    def stop_listening(self):
        """Stop listening for events"""
        self.is_listening = False
        
        # Clean up event filters
        for filter_name, event_filter in self.event_filters.items():
            try:
                self.w3.eth.uninstall_filter(event_filter.filter_id)
            except Exception as e:
                logger.error(f"Error removing filter {filter_name}: {str(e)}")
        
        self.event_filters.clear()
        logger.info("Event listener stopped")
    
    def get_historical_events(self, 
                            event_type: str, 
                            from_block: int = 0, 
                            to_block: str = 'latest',
                            user_address: Optional[str] = None) -> List[OrderEvent]:
        """
        Get historical events from the blockchain
        
        Args:
            event_type: Event type to fetch
            from_block: Starting block number
            to_block: Ending block number or 'latest'
            user_address: Filter by user address (optional)
            
        Returns:
            List of OrderEvent objects
        """
        events = []
        
        try:
            # Create argument filter
            argument_filters = {}
            if user_address:
                argument_filters['user'] = user_address
            
            if event_type == 'OrderProposed':
                event_filter = self.contract.events.OrderProposed.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block,
                    argument_filters=argument_filters
                )
                
                for event in event_filter.get_all_entries():
                    args = event['args']
                    events.append(OrderEvent(
                        event_type='OrderProposed',
                        user=args['user'],
                        order_id=str(args['offerId']),
                        transaction_hash=event['transactionHash'].hex(),
                        block_number=event['blockNumber'],
                        additional_data={
                            'prompt_hash': args['promptHash'].hex(),
                            'status': 'InProgress',
                            'status_code': OrderStatus.IN_PROGRESS.value
                        }
                    ))
            
            elif event_type == 'OrderConfirmed':
                event_filter = self.contract.events.OrderConfirmed.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block,
                    argument_filters=argument_filters
                )
                
                for event in event_filter.get_all_entries():
                    args = event['args']
                    events.append(OrderEvent(
                        event_type='OrderConfirmed',
                        user=args['user'],
                        order_id=str(args['offerId']),
                        transaction_hash=event['transactionHash'].hex(),
                        block_number=event['blockNumber'],
                        additional_data={
                            'amount_paid': wei_to_eth(args['amountPaid']),
                            'amount_paid_wei': args['amountPaid'],
                            'status': 'Confirmed',
                            'status_code': OrderStatus.CONFIRMED.value
                        }
                    ))
            
            elif event_type == 'orderFinalized':
                event_filter = self.contract.events.orderFinalized.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block,
                    argument_filters=argument_filters
                )
                
                for event in event_filter.get_all_entries():
                    args = event['args']
                    events.append(OrderEvent(
                        event_type='orderFinalized',
                        user=args['user'],
                        order_id=str(args['offerId']),
                        transaction_hash=event['transactionHash'].hex(),
                        block_number=event['blockNumber'],
                        additional_data={
                            'status': 'Completed',
                            'status_code': OrderStatus.COMPLETED.value
                        }
                    ))
            
            # Clean up the filter
            self.w3.eth.uninstall_filter(event_filter.filter_id)
            
        except Exception as e:
            logger.error(f"Error fetching historical events: {str(e)}")
            raise
        
        return events

class UserEventSubscription:
    """
    User-specific event subscription management
    """
    
    def __init__(self, event_listener: OrderEventListener, user_address: str):
        """
        Initialize user event subscription
        
        Args:
            event_listener: OrderEventListener instance
            user_address: User address to subscribe to
        """
        self.event_listener = event_listener
        self.user_address = user_address.lower()
        self.callbacks = {}
        self.is_subscribed = False
    
    def subscribe_to_user_events(self, callback: Callable[[OrderEvent], None]):
        """
        Subscribe to all events for this user
        
        Args:
            callback: Callback function for user events
        """
        def user_event_filter(event: OrderEvent):
            if event.user.lower() == self.user_address:
                callback(event)
        
        self.event_listener.add_event_callback('all', user_event_filter)
        self.is_subscribed = True
        logger.info(f"Subscribed to events for user: {self.user_address}")
    
    def subscribe_to_order_events(self, order_id: str, callback: Callable[[OrderEvent], None]):
        """
        Subscribe to events for a specific order
        
        Args:
            order_id: Order ID to subscribe to
            callback: Callback function for order events
        """
        def order_event_filter(event: OrderEvent):
            if (event.user.lower() == self.user_address and 
                event.order_id == order_id):
                callback(event)
        
        self.event_listener.add_event_callback('all', order_event_filter)
        logger.info(f"Subscribed to events for order {order_id} by user {self.user_address}")
    
    def get_user_event_history(self, from_block: int = 0) -> List[OrderEvent]:
        """Get historical events for this user"""
        all_events = []
        
        # Get all event types
        for event_type in ['OrderProposed', 'OrderConfirmed', 'orderFinalized']:
            events = self.event_listener.get_historical_events(
                event_type=event_type,
                from_block=from_block,
                user_address=self.user_address
            )
            all_events.extend(events)
        
        # Sort by block number
        all_events.sort(key=lambda x: x.block_number)
        return all_events