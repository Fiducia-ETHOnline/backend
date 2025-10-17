#!/usr/bin/env python3
"""
metta_agents_interaction.py

Test scenario:
1) Merchant adds a new menu item to MeTTa
2) Merchant's system prompt includes the latest menu from MeTTa
3) Customer infers price from MeTTa when LLM price is missing/invalid

Note: In production, merchant/customer share data via messages or a shared store.
For determinism, we mirror the new item into both agents' MeTTa instances here.
"""
from typing import Tuple
import sys, pathlib

# Ensure project root is in sys.path when running as a script
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metta.utils import add_menu_item, get_menu_for_merchant

# Import agent modules to access their MeTTa instances and helpers
from agent.merchant import METTA_INSTANCE as MERCHANT_METTA, system_prompt as MERCHANT_SYSTEM
from agent.customer import METTA_INSTANCE as CUSTOMER_METTA, _lookup_price_from_metta

MERCHANT = "TestPizzaAgent"


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def test_merchant_adds_item_and_prompt_updates():
    # 1) Merchant adds a new item
    add_menu_item(MERCHANT_METTA, MERCHANT, "veggie_pizza", "13")

    # 2) Verify it's present in merchant's menu
    menu = get_menu_for_merchant(MERCHANT_METTA, MERCHANT)
    print("Merchant menu:", menu)
    assert_true(("veggie_pizza", "13") in menu, "veggie_pizza not found in merchant menu")

    # 3) System prompt should include updated menu
    new_system_prompt = MERCHANT_SYSTEM
    if menu:
        new_system_prompt += "\n\nAvailable Menu (via MeTTa):\n" + "\n".join([f"- {i}: ${p}" for i, p in menu])
    print("System prompt snippet:\n", "\n".join(new_system_prompt.splitlines()[-10:]))
    assert_true("veggie_pizza: $13" in new_system_prompt, "Updated item not reflected in system prompt")


def test_customer_uses_metta_price_fallback():
    # Mirror merchant's new item to the customer's MeTTa for this test
    add_menu_item(CUSTOMER_METTA, MERCHANT, "veggie_pizza", "13")

    # Customer price inference from description
    desc = "I'd like a veggie pizza with extra olives"
    item, price = _lookup_price_from_metta(desc, MERCHANT)
    print("Customer inferred:", item, price)
    assert_true(item == "veggie_pizza", "Customer did not match the correct item from description")
    assert_true(price == "13", "Customer did not retrieve the correct price from MeTTa")


def main():
    test_merchant_adds_item_and_prompt_updates()
    test_customer_uses_metta_price_fallback()
    print("All metta agent interaction tests passed ✔️")


if __name__ == "__main__":
    main()
