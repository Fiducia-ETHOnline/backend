from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address
import json
from .auth_dependencies import create_access_token

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

    token = create_access_token({
        'address': recovered_address,
        'role': 'customer'
    })

    response_data = {
        "token": token,
        "user": {
            "address": address,
            "role": "customer"
        }
    }
    return response_data