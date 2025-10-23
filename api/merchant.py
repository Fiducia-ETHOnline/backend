from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .auth_dependencies import verify_jwt_token
from api.blockchain import *
from storage.lighthouse import *
from typing import List, Dict, Any
from uagents.query import send_sync_message
from agent.protocol.a3acontext import A3AContext, A3AResponse, A3AMessage
from eth_utils import to_checksum_address
import os
from dotenv import load_dotenv
load_dotenv()
router = APIRouter(prefix="/api", tags=["merchant"])

class UpdateStatusRequest(BaseModel):
    status: str

class ChatMessageRequest(BaseModel):
    messages: List[Dict[str, Any]]

merchant_agent_address = os.getenv(
    'MERCHANT_AGENT_ADDRESS',
    'agent1qf9ua6p2gz6nx47emvsf5d9840h7wpfwlcqhsqt4zz0dun8tj43l23jtuch'
)

@router.get('/tasks')
async def get_assigned_tasks(current_user: dict = Depends(verify_jwt_token)):
    # backend_ordercontract
    if current_user['role'] != 'merchant':
        raise HTTPException(status_code=401, detail="You have to be a merchant to use this api endpoint")

    # address = current_user['address']
    # # try:
    # mock_order_ids = backend_ordercontract.get_merchant_order_ids(address)
    # mock_orders =[

    # ]
    # for ids in mock_order_ids:
    #     order_detail = backend_ordercontract.get_user_order_details(address,ids)
    #     mock_orders.append({
    #         'orderId':order_detail.order_id,
    #         'cid': CIDRebuild(order_detail.prompt_hash),
    #         'status':order_detail.status_name,
    #         'amount':str(order_detail.price)+' USDC'
    #     })
    mock_tasks = [
        {
            "orderId": "order-abc-123",
            "description": "Large pepperoni pizza",
            "status": "AWAITING FULFILLMENT",
            "payout": "25 USDC"
        }
    ]
    return mock_tasks

@router.post('/tasks/{orderId}/status')
async def update_task_status(
    orderId: str,
    request: UpdateStatusRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    new_status = request.status
    if not new_status:
        raise HTTPException(status_code=400, detail="A new status is required.")

    response_data = {
        "orderId": orderId,
        "status": new_status,
        "message": "Status updated successfully."
    }
    return response_data

@router.post('/merchant/chat/messages')
async def send_merchant_chat_message(
    request: ChatMessageRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    """Forward chat to Merchant Agent. Supports admin updates by allowing role='agent'."""
    msgs = request.messages
    if not msgs:
        raise HTTPException(status_code=400, detail="Messages are required")

    wallet_msg = A3AMessage(
        role='wallet',
        content=to_checksum_address(current_user['address'])
    )
    final_msg: List[A3AMessage] = [wallet_msg]
    # pass merchant_id hint to agent, if present
    if current_user.get('merchant_id'):
        final_msg.append(A3AMessage(role='agent', content=f"merchant_id:{current_user['merchant_id']}"))
    for item in msgs:
        role = item.get('role')
        content = item.get('content')
        if role in ('user', 'assistant', 'agent', 'query_wallet') and isinstance(content, str | bytes | dict | list | type(None)):
            # Only allow 'agent' role messages from authenticated merchants
            if role == 'agent' and current_user.get('role') != 'merchant':
                raise HTTPException(status_code=403, detail="Admin updates require merchant role")
            # For query_wallet, content can be empty; normalize to empty string
            final_msg.append(A3AMessage(role=role, content=content or ""))

    resp = await send_sync_message(merchant_agent_address, A3AContext(messages=final_msg), response_type=A3AResponse)
    return resp