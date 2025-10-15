"""
OrderContract API endpoints for smart contract integration
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
from ..blockchain.order_service import order_contract_service
from .auth_dependencies import get_current_user  # Assuming you have auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["order-contract"])

# Pydantic models for OrderContract requests/responses
class ServiceInitRequest(BaseModel):
    order_contract_address: str = Field(..., description="OrderContract address")
    agent_controller_private_key: Optional[str] = Field(None, description="Agent controller private key")
    pyusd_token_address: Optional[str] = Field(None, description="pyUSD token address (optional)")

class CreateOrderRequest(BaseModel):
    user_address: str = Field(..., description="User's Ethereum address")
    prompt: str = Field(..., description="User's prompt/request")

class ConfirmOrderRequest(BaseModel):
    user_address: str = Field(..., description="User's Ethereum address")
    order_id: str = Field(..., description="Order ID to confirm")

class CancelOrderRequest(BaseModel):
    user_address: str = Field(..., description="User's Ethereum address")
    order_id: str = Field(..., description="Order ID to cancel")

class AgentAnswerRequest(BaseModel):
    order_id: str = Field(..., description="Order ID to answer")
    answer: str = Field(..., description="Agent's answer")
    price_pyusd: float = Field(..., gt=0, description="Price in pyUSD")

class FinalizeOrderRequest(BaseModel):
    order_id: str = Field(..., description="Order ID to finalize")

class UserOrdersRequest(BaseModel):
    user_address: str = Field(..., description="User's Ethereum address")
    status_filter: Optional[str] = Field(None, description="Status filter (optional)")

class OrderDetailsRequest(BaseModel):
    order_id: str = Field(..., description="Order ID")
    user_address: Optional[str] = Field(None, description="User address (optional)")

class PyUSDInfoRequest(BaseModel):
    user_address: str = Field(..., description="User's Ethereum address")

class EventSubscriptionRequest(BaseModel):
    user_address: str = Field(..., description="User address to subscribe to")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")

class EventHistoryRequest(BaseModel):
    user_address: str = Field(..., description="User address")
    from_block: int = Field(default=0, description="Starting block number")

# API Endpoints

@router.post("/initialize")
async def initialize_service(
    request: ServiceInitRequest,
    current_user=Depends(get_current_user)
):
    """Initialize OrderContract service"""
    try:
        success = await order_contract_service.initialize_service(
            order_contract_address=request.order_contract_address,
            agent_controller_private_key=request.agent_controller_private_key,
            pyusd_token_address=request.pyusd_token_address
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize OrderContract service"
            )
        
        service_info = order_contract_service.get_service_info()
        return {
            "message": "OrderContract service initialized successfully",
            "service_info": service_info
        }
        
    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service initialization failed: {str(e)}"
        )

@router.get("/info")
async def get_service_info(current_user=Depends(get_current_user)):
    """Get OrderContract service information"""
    try:
        service_info = order_contract_service.get_service_info()
        
        if not service_info.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OrderContract service not initialized"
            )
        
        return service_info
        
    except Exception as e:
        logger.error(f"Error getting service info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/confirm")
async def confirm_order(
    request: ConfirmOrderRequest,
    current_user=Depends(get_current_user)
):
    """Confirm and pay for an order"""
    try:
        result = await order_contract_service.confirm_user_order(
            user_address=request.user_address,
            order_id=request.order_id
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Failed to confirm order')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error confirming order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/agent/finalize")
async def agent_finalize_order(
    request: FinalizeOrderRequest,
    current_user=Depends(get_current_user)
):
    """Agent finalizes a completed order"""
    try:
        result = await order_contract_service.agent_finalize_order(
            order_id=request.order_id
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Failed to finalize order')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error finalizing order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ========== QUERY ENDPOINTS ==========

@router.post("/user/orders")
async def get_user_orders(
    request: UserOrdersRequest,
    current_user=Depends(get_current_user)
):
    """Get all orders for a user"""
    try:
        result = order_contract_service.get_user_orders(
            user_address=request.user_address,
            status_filter=request.status_filter
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Failed to retrieve user orders')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/order/details")
async def get_order_details(
    request: OrderDetailsRequest,
    current_user=Depends(get_current_user)
):
    """Get detailed information about an order"""
    try:
        result = order_contract_service.get_order_details(
            order_id=request.order_id,
            user_address=request.user_address
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Failed to retrieve order details')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting order details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/pyusd/info")
async def get_pyusd_info(
    request: PyUSDInfoRequest,
    current_user=Depends(get_current_user)
):
    """Get pyUSD balance and allowance information"""
    try:
        result = order_contract_service.get_pyusd_info(
            user_address=request.user_address
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Failed to retrieve pyUSD information')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting pyUSD info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ========== EVENT ENDPOINTS ==========

@router.post("/events/subscribe")
async def subscribe_to_events(
    request: EventSubscriptionRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """Subscribe to events for a user"""
    try:
        def event_callback(event):
            logger.info(f"Event received for user {request.user_address}: {event.event_type}")
            # Here you could send to webhook, store in database, etc.
            if request.webhook_url:
                # Send to webhook (implement webhook sending logic)
                pass
        
        subscription = order_contract_service.subscribe_to_user_events(
            user_address=request.user_address,
            callback=event_callback
        )
        
        return {
            "success": True,
            "message": f"Subscribed to events for user {request.user_address}",
            "user_address": request.user_address,
            "webhook_url": request.webhook_url
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/events/history")
async def get_event_history(
    request: EventHistoryRequest,
    current_user=Depends(get_current_user)
):
    """Get historical events for a user"""
    try:
        events = order_contract_service.get_user_event_history(
            user_address=request.user_address,
            from_block=request.from_block
        )
        
        return {
            "success": True,
            "user_address": request.user_address,
            "from_block": request.from_block,
            "total_events": len(events),
            "events": events
        }
        
    except Exception as e:
        logger.error(f"Error getting event history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ========== UTILITY ENDPOINTS ==========

@router.get("/status/{order_id}")
async def get_order_status(
    order_id: str,
    current_user=Depends(get_current_user)
):
    """Get quick order status"""
    try:
        result = order_contract_service.get_order_details(order_id=order_id)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order_details = result.get('order_details', {})
        return {
            "order_id": order_id,
            "status": order_details.get('status'),
            "status_code": order_details.get('status_code'),
            "buyer": order_details.get('buyer'),
            "price_pyusd": order_details.get('price_pyusd')
        }
        
    except Exception as e:
        logger.error(f"Error getting order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        service_info = order_contract_service.get_service_info()
        return {
            "status": "healthy" if service_info.get('initialized', False) else "unhealthy",
            "service_initialized": service_info.get('initialized', False),
            "timestamp": service_info.get('latest_block', 0) if service_info.get('initialized') else None
        }
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }