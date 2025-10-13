from flask import Blueprint, request, jsonify
from api.auth_decorator import token_required


merchant_bp = Blueprint('merchant_api', __name__, url_prefix='/api')

@merchant_bp.route('/tasks', methods=['GET'])
@token_required(role="business") 
def get_assigned_tasks():


    mock_tasks = [
        {
            "orderId": "order-abc-123",
            "description": "Large pepperoni pizza",
            "status": "AWAITING FULFILLMENT",
            "payout": "25 USDC"
        }
    ]
    return jsonify(mock_tasks), 200

@merchant_bp.route('/tasks/<string:orderId>/status', methods=['POST'])
@token_required() 
def update_task_status(orderId):

    data = request.get_json()
    new_status = data.get('status') 
    if not new_status:
        return jsonify({"error": "A new status is required."}), 400

    response_data = {
        "orderId": orderId,
        "status": new_status,
        "message": "Status updated successfully."
    }
    return jsonify(response_data), 200