from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address
import json
from .auth_dependencies import create_access_token
from blockchain.merchant_nft import is_merchant, get_merchant_id

NONCE_STORE = {}

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    address: str
    signature: str

def get_nonce(address: str):
    global NONCE_STORE

    nonce = f"{secrets.token_hex(8)}"
    NONCE_STORE[address.lower()] = nonce
    print(NONCE_STORE)
    return nonce

@router.get('/challenge')
async def get_challenge(address: str = Query(..., description="Wallet address")):
    wallet_address = address.lower()

    response_data = {
        "message": f"Sign this message to log in to Fiducia. Domain:a2a.com Nonce: {get_nonce(wallet_address)}"
    }
    print(response_data)
    return response_data

@router.post('/login')
async def login_with_signature(request: LoginRequest):
    global NONCE_STORE
    address = request.address
    signature = request.signature

    if not address or not signature:
        raise HTTPException(status_code=400, detail="Address and signature are required")

    nonce = NONCE_STORE.get(address.lower())
    print(NONCE_STORE)
    print(address.lower())
    if not nonce:
        raise HTTPException(status_code=400, detail="Nonce not found or expired")

    encoded_msg = encode_defunct(text=nonce)
    recovered_address = Account.recover_message(encoded_msg, signature=signature)

    if to_checksum_address(recovered_address) != to_checksum_address(address):
        raise HTTPException(status_code=401, detail="Invalid signature")

    NONCE_STORE.pop(address.lower(), None)
    role = 'merchant' if is_merchant(address) else 'customer'
    claims = {
        'address': recovered_address,
        'role': role
    }
    if role == 'merchant':
        claims['merchant_id'] = get_merchant_id(address)
    token = create_access_token(claims)

    response_data = {
        "token": token,
        "user": {
            "address": address,
            "role": role,
            **({"merchant_id": claims.get('merchant_id')} if role == 'merchant' else {})
        }
    }
    return response_data