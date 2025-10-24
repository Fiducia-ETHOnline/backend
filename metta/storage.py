import os
from typing import Iterable

# Simple line-based storage and loader for MeTTa facts.
# Each fact is written as a single S-expression per line, e.g.:
# (menu 1 cheese_pizza)
# (item-display cheese_pizza "cheese pizza")
# (price cheese_pizza "5")
# (merchant-wallet 1 "0x...")

DEFAULT_DIR = os.getenv("METTA_STORAGE_DIR", "metta_store")


def ensure_dir(path: str = DEFAULT_DIR) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def merchant_file(merchant_label: str, base_dir: str = DEFAULT_DIR) -> str:
    ensure_dir(base_dir)
    safe = str(merchant_label).strip().replace(" ", "_")
    return os.path.join(base_dir, f"merchant_{safe}.metta")


def _quote(s: str) -> str:
    # Escape double quotes; MeTTa uses ASCII form with quotes for strings
    return '"' + str(s).replace('"', '\\"') + '"'


def append_fact_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        if not line.endswith("\n"):
            line += "\n"
        f.write(line)


def append_menu_item(path: str, merchant_label: str, slug: str, display_name: str, price: str) -> None:
    # (menu <merchant> <slug>)
    append_fact_line(path, f"(menu {merchant_label} {slug})")
    # (item-display <slug> "<display>")
    append_fact_line(path, f"(item-display {slug} {_quote(display_name)})")
    # (price <slug> "<price>")
    append_fact_line(path, f"(price {slug} {_quote(price)})")


def append_price(path: str, slug: str, price: str) -> None:
    append_fact_line(path, f"(price {slug} {_quote(price)})")


def append_remove_item(path: str, merchant_label: str, slug: str) -> None:
    append_fact_line(path, f"(removed-menu {merchant_label} {slug})")


def append_wallet(path: str, merchant_label: str, wallet: str) -> None:
    append_fact_line(path, f"(merchant-wallet {merchant_label} {_quote(wallet)})")


def append_desc(path: str, merchant_label: str, desc: str) -> None:
    append_fact_line(path, f"(merchant-desc {merchant_label} {_quote(desc)})")


def append_hours(path: str, merchant_label: str, hours: str) -> None:
    append_fact_line(path, f"(merchant-hours {merchant_label} {_quote(hours)})")


def append_location(path: str, merchant_label: str, location: str) -> None:
    append_fact_line(path, f"(merchant-location {merchant_label} {_quote(location)})")


def append_item_desc(path: str, slug: str, text: str) -> None:
    append_fact_line(path, f"(item-desc {slug} {_quote(text)})")


def load_merchant_into(metta, merchant_label: str, base_dir: str = DEFAULT_DIR) -> None:
    """Load all facts for a merchant into the provided MeTTa instance by running each line.
    Safe to call multiple times; MeTTa append semantics handle duplicates.
    """
    path = merchant_file(merchant_label, base_dir)
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    metta.run(line)
                except Exception:
                    # Skip malformed lines
                    continue
    except Exception:
        # Ignore load errors to avoid breaking read paths
        pass
