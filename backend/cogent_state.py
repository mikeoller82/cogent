"""Session state management for Cogent.

Analogous to Hermes' hermes_state.py — lightweight JSON-file-backed
state for sessions, metadata, and lifecycle tracking.

Sessions are stored as individual JSON files in ``memory/sessions/``
with a parallel ``sessions.json`` index for fast listing.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import SESSIONS_DIR, ensure_dirs

logger = logging.getLogger("cogent.state")


# ── Session metadata ──────────────────────────────────────────────────────

@dataclass
class SessionMeta:
    """Minimal metadata tracked per session."""
    id: str
    title: str = ""
    workspace_id: str = "default"
    created_at: float = 0.0
    updated_at: float = 0.0
    message_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Session index ─────────────────────────────────────────────────────────

_index_lock = threading.Lock()


def _index_path() -> Path:
    ensure_dirs()
    return SESSIONS_DIR / "sessions.json"


def _load_index() -> Dict[str, SessionMeta]:
    path = _index_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {sid: SessionMeta(**m) for sid, m in data.items()}
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Corrupt session index, rebuilding: %s", exc)
        return _rebuild_index()


def _save_index(index: Dict[str, SessionMeta]) -> None:
    data = {sid: asdict(m) for sid, m in index.items()}
    path = _index_path()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _rebuild_index() -> Dict[str, SessionMeta]:
    """Scan session/ directory and rebuild the index from individual files."""
    index: Dict[str, SessionMeta] = {}
    for f in SESSIONS_DIR.iterdir():
        if f.suffix == ".json" and f.stem != "sessions":
            try:
                meta = json.loads(f.read_text(encoding="utf-8"))
                sid = meta.get("id", f.stem)
                index[sid] = SessionMeta(**meta)
            except (json.JSONDecodeError, TypeError):
                continue
    _save_index(index)
    return index


# ── Public API ────────────────────────────────────────────────────────────

def create_session(session_id: str, title: str = "",
                   workspace_id: str = "default") -> SessionMeta:
    """Register a new session in the index."""
    now = time.time()
    meta = SessionMeta(
        id=session_id,
        title=title,
        workspace_id=workspace_id,
        created_at=now,
        updated_at=now,
    )
    with _index_lock:
        index = _load_index()
        index[session_id] = meta
        _save_index(index)
    _write_session_file(meta)
    logger.info("Session created: %s (%s)", session_id[:12], title or "untitled")
    return meta


def touch_session(session_id: str, *, message_count: Optional[int] = None,
                  tags: Optional[List[str]] = None) -> None:
    """Update a session's timestamp and optional fields."""
    with _index_lock:
        index = _load_index()
        meta = index.get(session_id)
        if not meta:
            logger.warning("Touching unknown session: %s", session_id[:12])
            return
        meta.updated_at = time.time()
        if message_count is not None:
            meta.message_count = message_count
        if tags is not None:
            meta.tags = tags
        index[session_id] = meta
        _save_index(index)
        _write_session_file(meta)


def get_session(session_id: str) -> Optional[SessionMeta]:
    with _index_lock:
        return _load_index().get(session_id)


def list_sessions(workspace_id: str = "default",
                  limit: int = 200) -> List[SessionMeta]:
    with _index_lock:
        index = _load_index()
    sessions = [m for m in index.values() if m.workspace_id == workspace_id]
    sessions.sort(key=lambda m: m.updated_at, reverse=True)
    return sessions[:limit]


def delete_session(session_id: str) -> None:
    with _index_lock:
        index = _load_index()
        index.pop(session_id, None)
        _save_index(index)
    # Remove individual file
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.is_file():
        path.unlink()
    logger.info("Session deleted: %s", session_id[:12])


def session_count(workspace_id: str = "default") -> int:
    with _index_lock:
        index = _load_index()
    return sum(1 for m in index.values() if m.workspace_id == workspace_id)


# ── Per-session file storage (for richer data than the index) ─────────────

def _session_file_path(session_id: str) -> Path:
    ensure_dirs()
    return SESSIONS_DIR / f"{session_id}.json"


def _write_session_file(meta: SessionMeta) -> None:
    path = _session_file_path(meta.id)
    path.write_text(json.dumps(asdict(meta), indent=2, default=str), encoding="utf-8")


def write_session_data(session_id: str, data: Dict[str, Any]) -> None:
    """Write arbitrary JSON-serialisable data alongside session metadata."""
    path = _session_file_path(session_id)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}
    existing.update(data)
    existing["id"] = session_id
    path.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
    touch_session(session_id)


def read_session_data(session_id: str) -> Dict[str, Any]:
    """Return stored data for a session (empty dict if missing)."""
    path = _session_file_path(session_id)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Corrupt session file: %s", path)
        return {}
