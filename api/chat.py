# from flask import Blueprint, request, jsonify
# import time,secrets
# from eth_account import Account
# from eth_account.messages import encode_defunct
# from web3 import Web3
# from eth_utils import to_checksum_address
# from flask_jwt_extended import (
#     JWTManager, create_access_token, jwt_required, get_jwt_identity
# )

# auth_bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')

# @auth_bp.route('/messages', methods=['POST'])
# @jwt_required(refresh=True)
# def message_completion(messages):
#     current_user = get_jwt_identity()
#     address:str = current_user.address
#     role:str    = current_user.role
    