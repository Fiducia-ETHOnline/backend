from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse,Response
from pydantic import BaseModel
from typing import List, Dict, Any
from uagents.query import send_sync_message,query
from agent.protocol.a3acontext import A3AContext,A3AResponse
import json
from .auth_dependencies import verify_jwt_token
# from eth_utils import to_checksum_address
# from blockchain.a3atoken_contract import A3ATokenContract
from api.blockchain import *
from web3 import Web3

router = APIRouter(prefix="/api/contract", tags=["contract"])

# token_contract = A3ATokenContract()

@router.get('/pyusd')
async def send_pyusd_addr(
    # current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['PYUSD_ADDRESS']

@router.get('/a3atoken')
async def send_a3atoken_addr(
    # current_user: dict = Depends(verify_jwt_token)
):
    return backend_ordercontract.get_a3a_address()
    # return os.environ['A3ATOKEN_ADDRESS']

@router.get('/order')
async def send_order_contract_addr(
    # current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['AGENT_CONTRACT']

@router.get('/rpc')
async def send_rpc_addr(
    # current_user: dict = Depends(verify_jwt_token)
):
    return os.environ['CONTRACT_URL']
