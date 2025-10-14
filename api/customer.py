from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from uagents.communication import send_message
from agent.protocol.a2acontext import A2AContext
import json
from .auth_dependencies import verify_jwt_token

custom_agent_address = 'agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up'

router = APIRouter(prefix="/api", tags=["customer"])

class ChatMessageRequest(BaseModel):
    messages: List[Dict[str, Any]]

class PaymentConfirmationRequest(BaseModel):
    txHash: str

class DisputeRequest(BaseModel):
    reason: str

@router.post('/chat/messages')
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    print(request.dict())

    msgs = request.messages
    print(msgs)
    if not msgs:
        raise HTTPException(status_code=400, detail="Messages are required")

    async def event_stream():
        async for chunk in send_message(custom_agent_address, A2AContext(messages=msgs)):
            # 将流式数据实时输出
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/plain")

@router.post('/orders/{orderId}/confirm-payment')
async def confirm_payment(
    orderId: str,
    request: PaymentConfirmationRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    tx_hash = request.txHash
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Transaction hash (txHash) is required")

    response_data = {
        "status": "PENDING_CONFIRMATION",
        "message": "Payment submitted, awaiting blockchain confirmation."
    }
    return response_data

@router.get('/orders')
async def get_my_orders(current_user: dict = Depends(verify_jwt_token)):
    mock_orders = [
        {
            "orderId": "order-abc-123",
            "description": "Large pepperoni pizza",
            "status": "AWAITING FULFILLMENT",
            "amount": "25 USDC"
        }
    ]
    return mock_orders

@router.post('/orders/{orderId}/confirm-finish')
async def confirm_order_received(
    orderId: str,
    current_user: dict = Depends(verify_jwt_token)
):
    response_data = {
        "orderId": orderId,
        "status": "COMPLETED",
        "message": "Order completed and funds released."
    }
    return response_data

@router.post('/orders/{orderId}/dispute')
async def raise_dispute(
    orderId: str,
    request: DisputeRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    reason = request.reason
    if not reason:
        raise HTTPException(status_code=400, detail="A reason for the dispute is required.")

    response_data = {
        "orderId": orderId,
        "status": "DISPUTED",
        "message": "Dispute has been raised. The funds will be frozen temporarily. Please wait for third-party to determine."
    }
    return response_data