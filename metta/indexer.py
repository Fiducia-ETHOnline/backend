import os
import re
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

from .storage import DEFAULT_DIR


def _tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    # Split on non-alphanumeric
    return [t for t in re.split(r"[^a-z0-9]+", text) if t]


def _iter_merchant_files(base_dir: str = DEFAULT_DIR):
    if not os.path.isdir(base_dir):
        return
    for name in os.listdir(base_dir):
        if not name.startswith("merchant_") or not name.endswith(".metta"):
            continue
        path = os.path.join(base_dir, name)
        # merchant_<id>.metta → <id>
        mid = name[len("merchant_") : -len(".metta")]
        yield mid, path


def build_index(base_dir: str = DEFAULT_DIR) -> Dict[str, Dict]:
    """Scan all merchant_*.metta files and build a keyword index.

    Returns a dict keyed by merchant_id with fields:
    - keywords: Counter of keyword → freq
    - items: list of item display names
    - desc/hours/location/wallet
    """
    index: Dict[str, Dict] = {}
    for merchant_id, path in _iter_merchant_files(base_dir):
        keywords: Counter = Counter()
        items: List[str] = []
        slug_to_display: Dict[str, str] = {}
        desc = hours = location = wallet = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    # (item-display slug "display name")
                    if line.startswith("(item-display "):
                        try:
                            # naive parse: (item-display <slug> "<display>")
                            parts = line[len("(item-display ") : -1]
                            slug, display = parts.split(" ", 1)
                            display = display.strip()
                            if display.startswith('"') and display.endswith('"'):
                                display = display[1:-1]
                            slug_to_display[slug] = display
                        except Exception:
                            pass
                    # (menu <merchant> <slug>)
                    elif line.startswith("(menu "):
                        try:
                            parts = line[len("(menu ") : -1].split()
                            # parts: [merchant_id, slug]
                            if len(parts) >= 2:
                                slug = parts[1]
                                display = slug_to_display.get(slug, slug)
                                items.append(display)
                                for t in _tokenize(display):
                                    keywords[t] += 1
                        except Exception:
                            pass
                    elif line.startswith("(merchant-desc "):
                        try:
                            content = line[len("(merchant-desc ") : -1]
                            # merchant desc → first token is merchant_id
                            _, text = content.split(" ", 1)
                            text = text.strip()
                            if text.startswith('"') and text.endswith('"'):
                                text = text[1:-1]
                            desc = text
                            for t in _tokenize(text):
                                keywords[t] += 1
                        except Exception:
                            pass
                    elif line.startswith("(merchant-hours "):
                        try:
                            content = line[len("(merchant-hours ") : -1]
                            _, text = content.split(" ", 1)
                            text = text.strip()
                            if text.startswith('"') and text.endswith('"'):
                                text = text[1:-1]
                            hours = text
                        except Exception:
                            pass
                    elif line.startswith("(merchant-location "):
                        try:
                            content = line[len("(merchant-location ") : -1]
                            _, text = content.split(" ", 1)
                            text = text.strip()
                            if text.startswith('"') and text.endswith('"'):
                                text = text[1:-1]
                            location = text
                            for t in _tokenize(text):
                                keywords[t] += 1
                        except Exception:
                            pass
                    elif line.startswith("(merchant-wallet "):
                        try:
                            content = line[len("(merchant-wallet ") : -1]
                            _, text = content.split(" ", 1)
                            text = text.strip()
                            if text.startswith('"') and text.endswith('"'):
                                text = text[1:-1]
                            wallet = text
                        except Exception:
                            pass
        except FileNotFoundError:
            continue
        index[merchant_id] = {
            "keywords": keywords,
            "items": items,
            "desc": desc,
            "hours": hours,
            "location": location,
            "wallet": wallet,
        }
    return index


def _index_path(base_dir: str = DEFAULT_DIR) -> str:
    return os.path.join(base_dir, "index.json")


def _latest_metta_mtime(base_dir: str = DEFAULT_DIR) -> float:
    latest = 0.0
    for _, path in _iter_merchant_files(base_dir):
        try:
            m = os.path.getmtime(path)
            if m > latest:
                latest = m
        except FileNotFoundError:
            continue
    return latest


def index_is_stale(base_dir: str = DEFAULT_DIR) -> bool:
    idx_path = _index_path(base_dir)
    if not os.path.exists(idx_path):
        return True
    try:
        idx_mtime = os.path.getmtime(idx_path)
    except Exception:
        return True
    return idx_mtime < _latest_metta_mtime(base_dir)


def save_index(index: Dict[str, Dict], base_dir: str = DEFAULT_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    path = _index_path(base_dir)
    # Convert Counters to plain dicts
    serializable = {}
    for mid, data in index.items():
        d = dict(data)
        kw = d.get("keywords")
        if isinstance(kw, Counter):
            d["keywords"] = dict(kw)
        serializable[mid] = d
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "base_dir": base_dir,
            "index": serializable,
        }, f)
    return path


def load_index(base_dir: str = DEFAULT_DIR) -> Dict[str, Dict] | None:
    path = _index_path(base_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
            idx = obj.get("index") or {}
            # Rehydrate keyword Counters
            for mid, data in idx.items():
                if isinstance(data, dict) and isinstance(data.get("keywords"), dict):
                    data["keywords"] = Counter(data["keywords"])
            return idx
    except Exception:
        return None


def search_merchants(query: str, base_dir: str = DEFAULT_DIR, top_k: int = 5) -> List[Dict]:
    """Simple keyword match over merchant index.

    Uses a cached index at base_dir/index.json when fresh; rebuilds if stale.
    """
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    idx = None
    try:
        if index_is_stale(base_dir):
            idx = build_index(base_dir)
            save_index(idx, base_dir)
        else:
            idx = load_index(base_dir) or build_index(base_dir)
            if idx is not None and not isinstance(idx, dict):
                idx = build_index(base_dir)
    except Exception:
        idx = build_index(base_dir)
    scored: List[Tuple[str, int]] = []
    for mid, data in idx.items():
        kw: Counter = data.get("keywords", Counter())
        score = sum(kw.get(t, 0) for t in q_tokens)
        if score > 0:
            scored.append((mid, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    results: List[Dict] = []
    for mid, score in scored[:top_k]:
        d = idx[mid]
        results.append({
            "merchant_id": mid,
            "score": score,
            "items": d.get("items", [])[:5],
            "desc": d.get("desc"),
            "location": d.get("location"),
        })
    return results
