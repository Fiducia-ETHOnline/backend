"""
Custom exceptions for blockchain operations
"""

class BlockchainException(Exception):
    """Base exception for blockchain operations"""
    pass

class ContractNotInitializedException(BlockchainException):
    """Raised when trying to use contract before initialization"""
    pass

class TransactionFailedException(BlockchainException):
    """Raised when a transaction fails"""
    def __init__(self, message: str, tx_hash: str = None):
        super().__init__(message)
        self.tx_hash = tx_hash

class InsufficientFundsException(BlockchainException):
    """Raised when account has insufficient funds"""
    pass

class InvalidAddressException(BlockchainException):
    """Raised when an invalid Ethereum address is provided"""
    pass

class GasEstimationException(BlockchainException):
    """Raised when gas estimation fails"""
    pass

class NetworkConnectionException(BlockchainException):
    """Raised when there's a network connection issue"""
    pass