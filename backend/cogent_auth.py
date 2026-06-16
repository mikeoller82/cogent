"""Authentication token store for Cogent.

Analogous to Hermes' ``auth.json`` — stores API credentials and
auth tokens in a structured JSON file at ``memory/auth.json``.

Usage::

    from cogent_auth import get_credential, set_credential, list_credentials

    set_credential("kilocode", {"api_key": "sk-..."})
    creds = get_credential("kilocode")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import MEMORY_DIR

logger = logging.getLogger("cogent.auth")


# ── Storage ──────────────────────────────────────────────────────────────

_lock = threading.Lock()


def _auth_path() -> Path:
    return MEMORY_DIR / "auth.json"


def _load() -> Dict[str, Any]:
    path = _auth_path()
    if not path.is_file():
        return {"credentials": {}, "updated_at": time.time()}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt auth.json, starting fresh")
        return {"credentials": {}, "updated_at": time.time()}


def _save(data: Dict[str, Any]) -> None:
    data["updated_at"] = time.time()
    path = _auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── Credential CRUD ─────────────────────────────────────────────────────

def set_credential(service: str, credential: Dict[str, Any]) -> None:
    """Store a credential for *service*.

    Example::

        set_credential("kilocode", {"api_key": "sk-...", "base_url": "..."})
        set_credential("github", {"token": "ghp_..."})
    """
    with _lock:
        data = _load()
        data.setdefault("credentials", {})[service] = {
            "value": credential,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        _save(data)
    logger.info("Credential stored: %s", service)


def get_credential(service: str) -> Optional[Dict[str, Any]]:
    """Retrieve a stored credential dict for *service*."""
    with _lock:
        data = _load()
        entry = data.get("credentials", {}).get(service)
    if not entry:
        return None
    return entry.get("value")


def delete_credential(service: str) -> bool:
    with _lock:
        data = _load()
        creds = data.get("credentials", {})
        if service not in creds:
            return False
        del creds[service]
        _save(data)
    logger.info("Credential deleted: %s", service)
    return True


def list_credentials() -> List[str]:
    """Return names of all stored credentials (not the values)."""
    with _lock:
        data = _load()
        return list(data.get("credentials", {}).keys())


# ── Environment injection ───────────────────────────────────────────────

def inject_env() -> Dict[str, str]:
    """Load all credentials into environment variables for subprocesses.

    Returns a dict of env vars to set.
    """
    env: Dict[str, str] = {}
    with _lock:
        data = _load()

    for service, entry in data.get("credentials", {}).items():
        value = entry.get("value", {})
        if isinstance(value, dict):
            for key, val in value.items():
                if isinstance(val, str):
                    env_key = f"{service.upper()}_{key.upper()}"
                    env[env_key] = val
    return env


def credential_summary() -> str:
    """Return a summary of stored credentials (names only, no secrets)."""
    creds = list_credentials()
    if not creds:
        return "No stored credentials."
    return f"Stored credentials: {', '.join(creds)}"
