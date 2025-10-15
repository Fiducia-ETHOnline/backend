"""
Utility functions for blockchain operations
"""

from web3 import Web3
import re
from typing import Dict, Any, List
import json

def is_valid_ethereum_address(address: str) -> bool:
    """
    Validate Ethereum address format
    
    Args:
        address: Ethereum address to validate
        
    Returns:
        True if valid address format
    """
    if not address:
        return False
    
    # Check if it's a valid hex string with 0x prefix and 40 hex characters
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, address))

def to_checksum_address(address: str) -> str:
    """
    Convert address to checksum format
    
    Args:
        address: Ethereum address
        
    Returns:
        Checksum address
    """
    return Web3.to_checksum_address(address)

def wei_to_eth(wei: int) -> float:
    """Convert wei to ETH"""
    return Web3.from_wei(wei, 'ether')

def eth_to_wei(eth: float) -> int:
    """Convert ETH to wei"""
    return Web3.to_wei(eth, 'ether')

def format_transaction_receipt(receipt: Dict) -> Dict[str, Any]:
    """
    Format transaction receipt for API response
    
    Args:
        receipt: Raw transaction receipt
        
    Returns:
        Formatted receipt
    """
    return {
        "transaction_hash": receipt.get("transactionHash", "").hex() if receipt.get("transactionHash") else "",
        "block_number": receipt.get("blockNumber"),
        "gas_used": receipt.get("gasUsed"),
        "status": "success" if receipt.get("status") == 1 else "failed",
        "from_address": receipt.get("from"),
        "to_address": receipt.get("to"),
        "logs": [
            {
                "address": log.get("address"),
                "topics": [topic.hex() for topic in log.get("topics", [])],
                "data": log.get("data")
            }
            for log in receipt.get("logs", [])
        ]
    }

def load_abi_from_file(file_path: str) -> List[Dict]:
    """
    Load ABI from JSON file
    
    Args:
        file_path: Path to ABI JSON file
        
    Returns:
        ABI as list of dictionaries
    """
    try:
        with open(file_path, 'r') as f:
            abi = json.load(f)
        return abi
    except FileNotFoundError:
        raise FileNotFoundError(f"ABI file not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in ABI file: {file_path}")

def validate_abi(abi: List[Dict]) -> bool:
    """
    Basic validation for ABI format
    
    Args:
        abi: Contract ABI
        
    Returns:
        True if ABI appears valid
    """
    if not isinstance(abi, list):
        return False
    
    for item in abi:
        if not isinstance(item, dict):
            return False
        if "type" not in item:
            return False
    
    return True