from flask import Blueprint, request, jsonify
import time,secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from eth_utils import to_checksum_address
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
NONCE_STORE={}




auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')
def get_nonce(address):
    global NONCE_STORE
    # 随机生成 nonce
    nonce = f"{secrets.token_hex(8)}"
    NONCE_STORE[address] = nonce
    print(NONCE_STORE)
    return nonce
@auth_bp.route('/challenge', methods=['GET'])
def get_challenge():

    
    wallet_address = request.args.get('address')
    if not wallet_address:
        return jsonify({"error": "Wallet address is required"}), 400
    wallet_address = wallet_address.lower()
    
    response_data = {
        "message": f"Sign this message to log in to Fiducia. Domain:a2a.com Nonce: {get_nonce(wallet_address)}"
    }
    print(response_data)
    return jsonify(response_data), 200

@auth_bp.route('/login', methods=['POST'])
def login_with_signature():
    global NONCE_STORE
    data = request.get_json()
    address:str = data.get('address') 
    signature:str = data.get('signature') 

    if not address or not signature:
        return jsonify({"error": "Address and signature are required"}), 400
    
    nonce = NONCE_STORE.get(address.lower())
    print(NONCE_STORE)
    print(address.lower())
    if not nonce:
        return jsonify({"error": "nonce not found or expired"}), 400

    encoded_msg = encode_defunct(text=nonce)
    recovered_address = Account.recover_message(encoded_msg, signature=signature)


    if to_checksum_address(recovered_address) != to_checksum_address(address):
        return jsonify({"error": "Invalid signature"}), 401

    NONCE_STORE.pop(address.lower(), None)

    token = create_access_token(identity={
        'address':recovered_address,
        'role':'customer'
    })
    # return jsonify({"ok": True, "token": token, "address": address})

    
    response_data = {
        "token": token,
        "user": {
            "address": address,
            "role": "customer" 
        }
    }
    return jsonify(response_data), 200