#!/usr/bin/env python3
"""
metta_dynamic_merchant.py

Tests for dynamic merchant MeTTa updates:
- Set/get merchant wallet
- Add item, update price, verify retrieval uses latest
- Remove item (tombstone) and verify it's filtered out
"""
from typing import Tuple
import sys, pathlib

# Ensure project root is in sys.path when running as a script
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metta.utils import (
    create_metta,
    add_menu_item,
    update_item_price,
    remove_menu_item,
    get_item_price,
    get_menu_for_merchant,
    set_merchant_wallet,
    get_merchant_wallet,
)

MERCHANT = "TestPizzaAgent"
MERCHANT_METTA = create_metta()


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def test_wallet_set_get():
    addr = "0xABCDEF000000000000000000000000000000ABCD"
    set_merchant_wallet(MERCHANT_METTA, MERCHANT, addr)
    got = get_merchant_wallet(MERCHANT_METTA, MERCHANT)
    print("Wallet:", got)
    assert_true(got == addr, "Merchant wallet not stored/retrieved correctly")


def test_update_price_and_remove():
    item = "special_pizza"
    add_menu_item(MERCHANT_METTA, MERCHANT, item, "10")
    # Update price
    update_item_price(MERCHANT_METTA, item, "14")
    # Debug: inspect raw matches
    raw = MERCHANT_METTA.run(f"!(match &self (price {item} $p) $p)")
    print("Raw price matches:", raw)
    price = get_item_price(MERCHANT_METTA, item)
    print("Latest price:", price)
    assert_true(price == "14", "Item price did not update to latest value")

    # Ensure menu shows updated price
    menu = dict(get_menu_for_merchant(MERCHANT_METTA, MERCHANT))
    print("Menu after update:", menu)
    assert_true(menu.get(item) == "14", "Menu did not reflect latest price")

    # Remove item and verify it's gone
    remove_menu_item(MERCHANT_METTA, MERCHANT, item)
    menu_after = dict(get_menu_for_merchant(MERCHANT_METTA, MERCHANT))
    print("Menu after removal:", menu_after)
    assert_true(item not in menu_after, "Removed item still present in menu retrieval")


def main():
    test_wallet_set_get()
    test_update_price_and_remove()
    print("All dynamic merchant MeTTa tests passed ✔️")


if __name__ == "__main__":
    main()
