import os
from typing import Optional, List
from web3 import Web3
from web3.types import FilterParams

_VERIFY = os.getenv('MERCHANT_NFT_VERIFY', 'false').lower() == 'true'
_STANDARD = os.getenv('MERCHANT_NFT_STANDARD', 'ERC721').upper()
_NFT_ADDRESS = os.getenv('MERCHANT_NFT_ADDRESS')
_TOKEN_ID = os.getenv('MERCHANT_NFT_TOKEN_ID')  # for ERC1155
_PROVIDER_URL = os.getenv('CONTRACT_URL')
_MERCHANT_ID_ENV = os.getenv('MERCHANT_ID')  # optional merchantId for isMerchant(wallet, merchantId)

ERC721_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    # Transfer event (indexed from, to, tokenId)
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
]

ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "id", "type": "uint256"}
        ],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

# Minimal custom ABI to support contracts that expose isMerchant(address,uint256) view returns (bool)
MERCHANT_ISMERCHANT_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "wallet", "type": "address"},
            {"name": "merchantId", "type": "uint256"}
        ],
        "name": "isMerchant",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }
]

def _web3() -> Optional[Web3]:
    if not _PROVIDER_URL:
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(_PROVIDER_URL))
        return w3 if w3.is_connected() else None
    except Exception:
        return None

def _contract(w3: Web3):
    if not _NFT_ADDRESS:
        return None
    # Build an ABI that includes both the standard balanceOf and optional isMerchant
    if _STANDARD == 'ERC1155':
        base_abi = ERC1155_ABI
    else:
        base_abi = ERC721_ABI
    abi = base_abi + MERCHANT_ISMERCHANT_ABI
    try:
        return w3.eth.contract(address=Web3.to_checksum_address(_NFT_ADDRESS), abi=abi)
    except Exception:
        return None

def is_merchant(address: str, merchant_id: Optional[int | str] = None) -> bool:
    """Return True if address is a merchant.

    Behavior:
    - If MERCHANT_NFT_VERIFY is false, returns True (dev mode).
    - If contract exposes isMerchant(wallet, merchantId) and merchant_id (arg or MERCHANT_ID env) is provided,
      call it and return the result.
    - Otherwise, fall back to ERC-721/1155 balanceOf > 0 check.
    """
    if not _VERIFY:
        return True
    w3 = _web3()
    if not w3:
        return False
    c = _contract(w3)
    if not c:
        return False
    try:
        # Prefer custom isMerchant if available and we have a merchantId
        mid = merchant_id if merchant_id is not None else _MERCHANT_ID_ENV
        # If none provided, attempt to derive from owned tokenId (ERC-721)
        if mid is None:
            derived = get_merchant_id(address)
            # Use only if numeric (tokenId)
            if isinstance(derived, str) and derived.isdigit():
                mid = derived
        if mid is not None and hasattr(c.functions, 'isMerchant'):
            try:
                result = c.functions.isMerchant(
                    Web3.to_checksum_address(address), int(str(mid))
                ).call()
                return bool(result)
            except Exception:
                # fall through to balanceOf
                pass
        # Fallback to balanceOf
        if _STANDARD == 'ERC1155':
            if not _TOKEN_ID:
                return False
            bal = c.functions.balanceOf(Web3.to_checksum_address(address), int(_TOKEN_ID)).call()
        else:
            bal = c.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return int(bal) > 0
    except Exception:
        return False

def get_merchant_id(address: str) -> str:
    """Derive merchant_id from the NFT holding where possible.

    Priority:
    1) If MERCHANT_ID env is set, return it.
    2) If ERC-721 and provider is available, scan Transfer events to compute current owned tokenIds and
       return the first tokenId as the merchant_id (string).
    3) Fallback to the wallet checksum address as a stable identifier.
    """
    # 1) Env override
    if _MERCHANT_ID_ENV:
        return str(_MERCHANT_ID_ENV)

    # 2) Try to compute from ERC-721 events
    try:
        if _STANDARD == 'ERC721' and _PROVIDER_URL and _NFT_ADDRESS:
            w3 = _web3()
            if w3:
                c = _contract(w3)
                if c and hasattr(c.events, 'Transfer'):
                    owner = Web3.to_checksum_address(address)
                    # Build log filter for all Transfer events of this contract
                    params: FilterParams = {
                        'fromBlock': 0,
                        'toBlock': 'latest',
                        'address': Web3.to_checksum_address(_NFT_ADDRESS),
                        # topics[0] = Transfer signature; leave None to not restrict and use ABI decoder
                    }
                    logs = w3.eth.get_logs(params)  # may be heavy but OK for dev
                    owned: set[int] = set()
                    for log in logs:
                        try:
                            evt = c.events.Transfer().process_log(log)
                            frm = Web3.to_checksum_address(evt['args']['from'])
                            to = Web3.to_checksum_address(evt['args']['to'])
                            tid = int(evt['args']['tokenId'])
                            if to == owner:
                                owned.add(tid)
                            if frm == owner and tid in owned:
                                owned.remove(tid)
                        except Exception:
                            continue
                    if owned:
                        # Return the smallest tokenId for determinism
                        return str(min(owned))
    except Exception:
        # fall through to fallback
        pass

    # 3) Fallback to checksum address
    try:
        return Web3.to_checksum_address(address)
    except Exception:
        return address.lower()
