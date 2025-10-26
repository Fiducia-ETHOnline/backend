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
from dotenv import load_dotenv
load_dotenv()
custom_agent_address = os.getenv('CUSTOMER_AGENT_ADDRESS','agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up')

router = APIRouter(prefix="/api", tags=["customer"])

class BuyA3ARequest(BaseModel):
    pyusd:float

class ChatMessageRequest(BaseModel):
    messages: List[Dict[str, Any]]
    # Optional explicit merchant selection from the client/UI
    merchantId: str | None = None

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
        role='wallet' if current_user['role'] =='customer' else 'merchant_wallet',
        content= to_checksum_address(current_user['address'])
    )
    msgs = request.messages
    print(msgs)
    if not msgs:
        raise HTTPException(status_code=400, detail="Messages are required")
    final_msg = []
    final_msg.append(wallet_msg)
    for item in msgs:
        role = item.get('role')
        content = item.get('content')
        if role in ('user', 'assistant'):
            final_msg.append(A3AMessage(role=role, content=content))
        # Allow clients to pass an explicit merchant_id hint as an agent-role message
        elif role == 'agent' and isinstance(content, str) and content.startswith('merchant_id:'):
            final_msg.append(A3AMessage(role='agent', content=content))
    # If the authenticated user is a merchant, pass merchant_id hint so downstream agents scope correctly
    if current_user.get('merchant_id'):
        final_msg.append(A3AMessage(role='agent', content=f"merchant_id:{current_user['merchant_id']}"))
    # If the client provided merchantId explicitly, append/override with that hint last
    if request.merchantId:
        final_msg.append(A3AMessage(role='agent', content=f"merchant_id:{request.merchantId}"))
    # final_msg.extend(msgs)
    resp = await send_sync_message(custom_agent_address,A3AContext(messages=final_msg),response_type=A3AResponse)
    # async def event_stream():
    #     async for chunk in send_message(custom_agent_address, A3AContext(messages=msgs)):
    #         yield f"data: {json.dumps(chunk)}\n\n"


    return resp
@router.post('/token/buya3a')
async def buya3a_token(
    request: BuyA3ARequest,
    current_user: dict = Depends(verify_jwt_token)
):
    try:
        transact =backend_ordercontract.build_buy_a3a_token(request.pyusd,current_user['address'])
    except Exception as e:
        return {
            'status':str(e),
            'transaction':''
        }

    return {
        'status':'ok',
        'transaction':json.dumps(transact)
    }

@router.post('/orders/{orderId}/confirm-payment')
async def confirm_payment(
    orderId: str,
    request: PaymentConfirmationRequest,
    current_user: dict = Depends(verify_jwt_token)
):
    if current_user['role']=='merchant':
        # return{
            return {
            'status':'NOT_A_CUSTOMER',
            'message': 'You must be a customer to use this api!'
            }
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
    role = current_user['role']
    # try:
    mock_order_ids = backend_ordercontract.get_user_order_ids(address) if role =='customer' else backend_ordercontract.get_merchant_order_ids(address)
    mock_orders =[

    ]
    for ids in mock_order_ids:
        order_detail = backend_ordercontract.get_user_order_details(address,ids) if role=='customer' else backend_ordercontract.get_merchant_order_details(address,ids)
        mock_orders.append({
            'orderId':order_detail.order_id,
            'cid': CIDRebuild(order_detail.prompt_hash),
            'status':order_detail.status_name,
            'amount':str(order_detail.price)+' pyUSD'
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
    if current_user['role']=='merchant':
        # return{
            return {
            'orderId':orderId,
            'status':'NOT_A_CUSTOMER',
            'message': 'You must be a customer to use this api!'
            }
        # }
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

@router.get('/orders/{orderId}/details')
async def get_order_details(orderId: str, current_user: dict = Depends(verify_jwt_token)):
    """Return on-chain order details for quick verification of routing.

    Useful fields: buyer, seller, price (pyUSD), paid (pyUSD), status, status_name.
    """
    try:
        d = backend_ordercontract.get_order_details_by_id(orderId)
        return {
            'orderId': d.order_id,
            'buyer': d.buyer,
            'seller': d.seller,
            'price': d.price,
            'paid': d.paid,
            'status': d.status,
            'status_name': d.status_name,
            'prompt_hash': d.prompt_hash,
            'answer_hash': d.answer_hash,
            'timestamp': d.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch order details: {e}")

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