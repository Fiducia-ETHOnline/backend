from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .auth_dependencies import verify_jwt_token

router = APIRouter(prefix="/api", tags=["merchant"])

class UpdateStatusRequest(BaseModel):
    status: str

@router.get('/tasks')
async def get_assigned_tasks(current_user: dict = Depends(verify_jwt_token)):
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