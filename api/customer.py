from flask import Blueprint, request, jsonify
from api.auth_decorator import token_required


customer_bp = Blueprint('customer_api', __name__, url_prefix='/api')

@customer_bp.route('/chat/messages', methods=['POST'])
@token_required() 
def send_chat_message():

    data = request.get_json()
    text = data.get('text') 
    if not text:
        return jsonify({"error": "Text is required"}), 400


    response_data = {
        "type": "payment",
        "orderId": "order-abc-123",
        "payload": {
            "message": "Order created! Total is 25 USDC. Please confirm payment.",
            "transaction": {
                "to": "0xContractAddress...",
                "value": "25000000",
                "data": "0x..."
            }
        }
    }
    return jsonify(response_data), 200

@customer_bp.route('/orders/<string:orderId>/confirm-payment', methods=['POST'])
@token_required() 
def confirm_payment(orderId):

    data = request.get_json()
    tx_hash = data.get('txHash') 
    if not tx_hash:
        return jsonify({"error": "Transaction hash (txHash) is required"}), 400


    response_data = {
        "status": "PENDING_CONFIRMATION",
        "message": "Payment submitted, awaiting blockchain confirmation."
    }
    return jsonify(response_data), 200

@customer_bp.route('/orders', methods=['GET'])
@token_required() 
def get_my_orders():

    mock_orders = [
        {
            "orderId": "order-abc-123",
            "description": "Large pepperoni pizza",
            "status": "AWAITING FULFILLMENT",
            "amount": "25 USDC"
        }
    ]
    return jsonify(mock_orders), 200

@customer_bp.route('/orders/<string:orderId>/confirm-finish', methods=['POST'])
@token_required() 
def confirm_order_received(orderId):


    response_data = {
        "orderId": orderId,
        "status": "COMPLETED",
        "message": "Order completed and funds released."
    }
    return jsonify(response_data), 200

@customer_bp.route('/orders/<string:orderId>/dispute', methods=['POST'])
@token_required() 
def raise_dispute(orderId):

    data = request.get_json()
    reason = data.get('reason') 
    if not reason:
        return jsonify({"error": "A reason for the dispute is required."}), 400

    
    response_data = {
        "orderId": orderId,
        "status": "DISPUTED",
        "message": "Dispute has been raised. The funds will be frozen temporarily. Please wait for third-party to determine."
    }
    return jsonify(response_data), 200