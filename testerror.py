from eth_utils import keccak

errors = [
    "InvalidSeller()",
    "InvalidPrice()",
    "AlreadyAnswered()",
    "NotAuthorized()",
]

for e in errors:
    sig = keccak(text=e).hex()[:10]
    print(e, "=>", sig)
