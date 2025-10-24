import os
import sys
import shutil

# Ensure repository root is importable
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from metta.indexer import build_index, save_index, load_index, search_merchants, index_is_stale

BASE = 'metta_store_test'

def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

def setup_demo_store():
    if os.path.isdir(BASE):
        shutil.rmtree(BASE)
    os.makedirs(BASE, exist_ok=True)
    # Merchant 1: pizza in Brooklyn
    _write(os.path.join(BASE, 'merchant_1.metta'), """
(item-display cheese_pizza "cheese pizza")
(menu 1 cheese_pizza)
(price cheese_pizza "5")
(merchant-desc 1 "New York slices")
(merchant-location 1 "Brooklyn")
""")
    # Merchant 2: burritos in Queens
    _write(os.path.join(BASE, 'merchant_2.metta'), """
(item-display chicken_burrito "chicken burrito")
(menu 2 chicken_burrito)
(price chicken_burrito "9")
(merchant-desc 2 "Authentic burritos")
(merchant-location 2 "Queens")
""")


def run():
    setup_demo_store()
    # Build and save index
    idx = build_index(BASE)
    assert '1' in idx and '2' in idx, 'Both merchants should be in index'
    save_index(idx, BASE)
    assert load_index(BASE) is not None, 'Index should be loadable from disk'
    assert not index_is_stale(BASE), 'Index should be fresh immediately after save'

    # Search pizza in Brooklyn -> expect merchant 1 to rank first
    res = search_merchants('best pizza in brooklyn', BASE)
    assert res and res[0]['merchant_id'] == '1', 'Merchant 1 should rank for pizza in Brooklyn'
    print('PASS: pizza in brooklyn ->', res[0])

    # Search burrito -> expect merchant 2 to rank first
    res2 = search_merchants('cheap burrito', BASE)
    assert res2 and res2[0]['merchant_id'] == '2', 'Merchant 2 should rank for burrito'
    print('PASS: cheap burrito ->', res2[0])

if __name__ == '__main__':
    run()
