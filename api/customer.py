from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse,Response
from pydantic import BaseModel
from typing import List, Dict, Any
from uagents.query import send_sync_message,query
from agent.protocol.a3acontext import *
import json,web3
from .auth_dependencies import verify_jwt_token
from eth_utils import to_checksum_address
from api.blockchain import *
from storage.lighthouse import *
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
    # print(request.dict())
    wallet_msg =A3AMessage(
        role='wallet',
        content= to_checksum_address(current_user['address'])
    )
    msgs = request.messages
    print(msgs)
    if not msgs:
        raise HTTPException(status_code=400, detail="Messages are required")
    final_msg = []
    final_msg.append(wallet_msg)
    for item in msgs:
        final_msg.append(A3AMessage(role=item['role'],content=item['content']))
    final_msg.extend(msgs)
    resp = await send_sync_message(custom_agent_address,A3AContext(messages=final_msg),response_type=A3AResponse)
    # async def event_stream():
    #     async for chunk in send_message(custom_agent_address, A3AContext(messages=msgs)):
    #         yield f"data: {json.dumps(chunk)}\n\n"


    return resp

@router.post('/orders/{orderId}/confirm-payment')
async def confirm_payment(
    orderId: str,
    request: PaymentConfirmationRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    tx_hash = request.txHash
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Transaction hash (txHash) is required")
    try:
        status = backend_ordercontract.verify_tx(tx_hash)
    except Exception:
        return {
            'status':'NOT_FOUND',
            'message':'Payment is not found or pending on block chain'
        }
    if status:
        return {
            "status": "TRANSACTION_CONFIRMED",
            "message": "Payment is confirmed on chain"
        }
    else:
        return {
            "status": "TRANSACTION_ERROR",
            "message": "Transaction failed, payment reverted on chain"
        }
    # return response_data

@router.get('/orders')
async def get_my_orders(current_user: dict = Depends(verify_jwt_token)):
    address = current_user['address']
    # try:
    mock_order_ids = backend_ordercontract.get_user_order_ids(address)
    mock_orders =[

    ]
    for ids in mock_order_ids:
        order_detail = backend_ordercontract.get_user_order_details(address,ids)
        mock_orders.append({
            'orderId':order_detail.order_id,
            'cid': CIDRebuild(order_detail.prompt_hash),
            'status':order_detail.status_name,
            'amount':str(order_detail.price)+' USDC'
        })
    # except Exception as e:
        # raise HTTPException(status_code=400, detail="Transaction hash (txHash) is required")


    # mock_orders = [
    #     {
    #         "orderId": "order-abc-123",
    #         "description": "Large pepperoni pizza",
    #         "status": "AWAITING FULFILLMENT",
    #         "amount": "25 USDC"
    #     }
    # ]
    return mock_orders

@router.post('/orders/{orderId}/confirm-finish')
async def confirm_order_received(
    orderId: str,
    current_user: dict = Depends(verify_jwt_token)
):
    address = current_user['address']
    try:
        txhash = backend_ordercontract.finalize_order(orderId)
    except Exception as e:
        return {
            'orderId':orderId,
            'status':'FAIL_TO_FINISH',
            'message': 'Cannot perform finalize_order in smart contract'
        }
    try:
        detail = backend_ordercontract.get_order_details_by_id(orderId)
    except Exception as e:
        return {
            'orderId':orderId,
            'status':'FAIL_TO_FINISH',
            'message': 'Cannot get order detail in smart contract'
        }
    response_data = {
        "orderId": orderId,
        "status": detail.status_name,
        "message": backend_ordercontract.translate_status_to_msg(detail.status)
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