from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .auth_dependencies import verify_jwt_token
from api.blockchain import *
from storage.lighthouse import *
router = APIRouter(prefix="/api", tags=["merchant"])

class UpdateStatusRequest(BaseModel):
    status: str

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