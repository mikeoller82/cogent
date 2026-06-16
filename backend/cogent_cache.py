"""File-based caching for Cogent.

Analogous to Hermes' ``cache/`` directory — stores model metadata,
document extracts, screenshots, and other cached data under
``memory/cache/`` with TTL support.

Usage::

    from cogent_cache import cache_get, cache_set, cache_clear

    cache_set("model_catalog", {"models": [...]}, ttl=3600)
    catalog = cache_get("model_catalog")
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import MEMORY_DIR

logger = logging.getLogger("cogent.cache")

_DEFAULT_TTL = 3600  # 1 hour


def _cache_dir() -> Path:
    p = MEMORY_DIR / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_path(key: str) -> Path:
    # Sanitise key for filename
    safe_key = key.replace("/", "_").replace(" ", "_").replace(".", "_")
    return _cache_dir() / f"{safe_key}.json"


# ── Core operations ─────────────────────────────────────────────────────

def cache_set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    """Store *value* under *key* with a TTL in seconds.

    Args:
        key: Cache key (used as filename component).
        value: JSON-serialisable value to cache.
        ttl: Time-to-live in seconds (default 3600).
    """
    payload = {
        "key": key,
        "value": value,
        "created_at": time.time(),
        "ttl": ttl,
    }
    path = _cache_path(key)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def cache_get(key: str) -> Optional[Any]:
    """Retrieve a cached value. Returns None if missing or expired."""
    path = _cache_path(key)
    if not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError):
        path.unlink(missing_ok=True)
        return None

    created = payload.get("created_at", 0)
    ttl = payload.get("ttl", _DEFAULT_TTL)
    if time.time() - created > ttl:
        path.unlink(missing_ok=True)
        return None

    return payload.get("value")


def cache_delete(key: str) -> bool:
    """Remove a cached entry. Returns True if it existed."""
    path = _cache_path(key)
    if not path.is_file():
        return False
    path.unlink()
    return True


def cache_clear() -> int:
    """Remove all expired cache entries. Returns count of removed files."""
    count = 0
    now = time.time()
    for f in _cache_dir().iterdir():
        if f.suffix != ".json":
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            created = payload.get("created_at", 0)
            ttl = payload.get("ttl", _DEFAULT_TTL)
            if now - created > ttl:
                f.unlink()
                count += 1
        except (json.JSONDecodeError, TypeError):
            f.unlink(missing_ok=True)
            count += 1
    return count


def cache_list() -> List[Dict[str, Any]]:
    """List all cache entries (key, age, ttl) without loading values."""
    results: List[Dict[str, Any]] = []
    now = time.time()
    for f in _cache_dir().iterdir():
        if f.suffix != ".json":
            continue
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            created = payload.get("created_at", 0)
            ttl = payload.get("ttl", _DEFAULT_TTL)
            results.append({
                "key": payload.get("key", f.stem),
                "age": round(now - created, 1),
                "ttl": ttl,
                "expired": (now - created) > ttl,
                "size": f.stat().st_size,
            })
        except (json.JSONDecodeError, TypeError):
            pass
    results.sort(key=lambda r: r["age"], reverse=True)
    return results
