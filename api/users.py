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
from web3 import Web3
custom_agent_address = 'agent1qvuadg2lwxfyjkuzny0mj6v7v4xkecdk2at3fgvrwjr7mpjtcqqq2j0y8up'

router = APIRouter(prefix="/api/user", tags=["user"])

token_contract = A3ATokenContract()

@router.post('/a3atoken/balance')
async def send_chat_message(
    current_user: dict = Depends(verify_jwt_token)
):
    return token_contract.check_a3a_balance(Web3.to_checksum_address(current_user['address']))

@router.post('/a3atoken/allowance')
async def send_chat_message(
    current_user: dict = Depends(verify_jwt_token)
):
    return token_contract.check_a3a_allowance(Web3.to_checksum_address(current_user['address']))
