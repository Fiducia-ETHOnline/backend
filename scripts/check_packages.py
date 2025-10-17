#!/usr/bin/env python3
"""
check_packages.py
A simple checker that tries to import all key dependencies and reports status.
Usage:
  python3 scripts/check_packages.py

Exits with code 0 if all packages are present, non-zero otherwise.
"""
import importlib
import sys
from typing import List, Tuple

# (pip_name, import_name) pairs
REQUIRED: List[Tuple[str, str]] = [
    ("fastapi", "fastapi"),
    ("uvicorn[standard]", "uvicorn"),
    ("python-jose[cryptography]", "jose"),
    ("python-multipart", "multipart"),
    ("uagents==0.22.10", "uagents"),
    ("uagents-core", "uagents_core"),
    ("openai", "openai"),
    ("requests", "requests"),
    ("web3", "web3"),
    ("eth-account", "eth_account"),
    ("pydantic[dotenv]", "pydantic"),
    ("PyJWT", "jwt"),
    ("lighthouseweb3", "lighthouseweb3"),
    ("multiformats", "multiformats"),
    ("python-dotenv", "dotenv"),
    ("hyperon", "hyperon"),
]


def main() -> int:
    print("Checking Python packages...\n")
    missing = []
    for pip_name, import_name in REQUIRED:
        try:
            mod = importlib.import_module(import_name)
            ver = getattr(mod, "__version__", None)
            ver_str = f" v{ver}" if ver else ""
            print(f"[OK] {import_name}{ver_str}")
        except Exception as e:
            print(f"[MISSING] {import_name} (install via: pip install {pip_name})")
            missing.append((pip_name, import_name, str(e)))
    
    if missing:
        print("\nSome packages are missing. Suggested installs:")
        for pip_name, import_name, _ in missing:
            print(f"  pip install {pip_name}")
        print("\nTip: On macOS with managed Python, you may need --user or a virtualenv:")
        print("  python3 -m pip install --user <pkg>")
        return 1
    else:
        print("\nAll required packages are installed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
