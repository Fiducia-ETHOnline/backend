from flask import Blueprint, request, jsonify


auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')

@auth_bp.route('/challenge', methods=['GET'])
def get_challenge():

    
    wallet_address = request.args.get('address')
    if not wallet_address:
        return jsonify({"error": "Wallet address is required"}), 400
    
    
    response_data = {
        "message": f"Sign this message to log in to Fiducia. Domain:***.com Nonce: 12345xyz"
    }
    return jsonify(response_data), 200

@auth_bp.route('/login', methods=['POST'])
def login_with_signature():
    
    data = request.get_json()
    address = data.get('address') 
    signature = data.get('signature') 

    if not address or not signature:
        return jsonify({"error": "Address and signature are required"}), 400

    
    response_data = {
        "token": f"fake_jwt_token_for_{address}",
        "user": {
            "address": address,
            "role": "customer" 
        }
    }
    return jsonify(response_data), 200