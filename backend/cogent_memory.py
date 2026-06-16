"""File-based long-term memory for Cogent.

Analogous to Hermes' memories/MEMORY.md and memories/USER.md —
human-readable markdown files that persist agent knowledge across sessions.

Each memory is a key=value pair stored in a markdown file with the format::

    key: value
    §
    key2: multiline value
    continues here
    §

The ``§`` (section sign) is the record delimiter.
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cogent_constants import MEMORIES_DIR, ensure_dirs

logger = logging.getLogger("cogent.memory")

_RECORD_SEP = "\n§\n"
_KEY_VALUE_RE = re.compile(r"^([^:\n]+?):\s*(.*)", re.DOTALL)


# ── File-based memory store ───────────────────────────────────────────────

class MemoryStore:
    """A single markdown-backed memory file.

    Each file stores a series of records separated by ``§``.
    Format per record::

        key: value text
        can span multiple lines
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    # ── Reading ────────────────────────────────────────────────────────

    def read_all(self) -> Dict[str, str]:
        """Return all records as {key: value}."""
        records: Dict[str, str] = {}
        if not self._path.is_file():
            return records

        text = self._path.read_text(encoding="utf-8")
        for block in text.split(_RECORD_SEP):
            block = block.strip()
            if not block:
                continue
            m = _KEY_VALUE_RE.match(block)
            if m:
                records[m.group(1).strip()] = m.group(2).strip()
        return records

    def get(self, key: str) -> Optional[str]:
        return self.read_all().get(key)

    def find(self, query: str, case_sensitive: bool = False) -> Dict[str, str]:
        """Return records whose key *or* value contains *query*."""
        results: Dict[str, str] = {}
        query_lower = query.lower() if not case_sensitive else query
        for k, v in self.read_all().items():
            if not case_sensitive:
                if query_lower in k.lower() or query_lower in v.lower():
                    results[k] = v
            else:
                if query in k or query in v:
                    results[k] = v
        return results

    # ── Writing ────────────────────────────────────────────────────────

    def set(self, key: str, value: str) -> None:
        """Upsert a record. Replaces the value if *key* already exists."""
        with self._lock:
            records = self.read_all()
            records[key] = value
            self._write_records(records)

    def delete(self, key: str) -> bool:
        """Remove *key* from memory. Returns True if it existed."""
        with self._lock:
            records = self.read_all()
            if key not in records:
                return False
            del records[key]
            self._write_records(records)
            return True

    def clear(self) -> None:
        with self._lock:
            self._path.write_text("", encoding="utf-8")

    def count(self) -> int:
        return len(self.read_all())

    def keys(self) -> List[str]:
        return list(self.read_all().keys())

    def as_text(self, prefix: str = "- ") -> str:
        """Return all records formatted as a bulleted markdown list."""
        lines: List[str] = []
        for k, v in self.read_all().items():
            # Truncate long values for preview
            preview = v[:120].replace("\n", " ") + ("…" if len(v) > 120 else "")
            lines.append(f"{prefix}**{k}:** {preview}")
        return "\n".join(lines)

    # ── Internals ──────────────────────────────────────────────────────

    def _write_records(self, records: Dict[str, str]) -> None:
        ensure_dirs()
        blocks: List[str] = []
        for key, value in records.items():
            # Normalise: ensure value doesn't start with accidental indent
            val = value.strip()
            blocks.append(f"{key}: {val}")
        self._path.write_text(_RECORD_SEP.join(blocks) + "\n", encoding="utf-8")

    @property
    def path(self) -> Path:
        return self._path


# ── Well-known stores ─────────────────────────────────────────────────────

# MEMORY.md — general agent knowledge (learned facts)
memory_store = MemoryStore(MEMORIES_DIR / "MEMORY.md")
# USER.md — user-specific preferences and context
user_store = MemoryStore(MEMORIES_DIR / "USER.md")


# ── Convenience API (matches Hermes pattern) ──────────────────────────────

def remember(key: str, value: str) -> None:
    """Save a fact to the agent's long-term memory."""
    memory_store.set(key, value)
    logger.info("Memory saved: %s", key)


def recall(key: str) -> Optional[str]:
    """Retrieve a specific fact from memory."""
    return memory_store.get(key)


def recall_all() -> Dict[str, str]:
    """Retrieve all stored facts."""
    return memory_store.read_all()


def forget(key: str) -> bool:
    """Remove a fact from memory."""
    return memory_store.delete(key)


def remember_user(key: str, value: str) -> None:
    """Save a user-specific preference or context."""
    user_store.set(key, value)


def recall_user(key: str) -> Optional[str]:
    return user_store.get(key)


def memory_summary() -> str:
    """Return a formatted block of all memories for the system prompt."""
    lines: List[str] = []
    mems = memory_store.read_all()
    if mems:
        lines.append("## Agent Memory")
        for k, v in mems.items():
            lines.append(f"- {k}: {v[:200].replace(chr(10), ' ')}")
    prefs = user_store.read_all()
    if prefs:
        lines.append("## User Preferences")
        for k, v in prefs.items():
            lines.append(f"- {k}: {v[:200].replace(chr(10), ' ')}")
    return "\n".join(lines)
