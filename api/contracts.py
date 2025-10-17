from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse,Response
from pydantic import BaseModel
from typing import List, Dict, Any
from uagents.query import send_sync_message,query
from agent.protocol.a3acontext import A3AContext,A3AResponse
import json
from .auth_dependencies import verify_jwt_token
from eth_utils import to_checksum_address
from blockchain.a3atoken_contract import A3ATokenContract
from api.blockchain import *
from web3 import Web3

router = APIRouter(prefix="/api/contract", tags=["contract"])

# token_contract = A3ATokenContract()

@router.post('/pyusd')
async def send_chat_message(
    current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['PYUSD_ADDRESS']

@router.post('/atatoken')
async def send_chat_message(
    current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['A3ATOKEN_ADDRESS']

@router.post('/order')
async def send_chat_message(
    current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['CONTRACT_URL']
