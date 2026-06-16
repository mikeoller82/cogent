"""Background process registry for Cogent.

Analogous to Hermes' ``processes.json`` and ``spawn-trees/`` —
tracks spawned subprocesses so they can be monitored, logged,
and killed on shutdown.

Stored in ``memory/processes.json``.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import MEMORY_DIR

logger = logging.getLogger("cogent.processes")

# ── Data ─────────────────────────────────────────────────────────────────

@dataclass
class ProcessEntry:
    pid: int
    label: str = ""
    command: str = ""
    started_at: float = 0.0
    status: str = "running"  # running, done, killed, error
    exit_code: Optional[int] = None
    tags: List[str] = field(default_factory=list)


# ── Storage ──────────────────────────────────────────────────────────────

_lock = threading.Lock()


def _processes_path() -> Path:
    return MEMORY_DIR / "processes.json"


def _load() -> Dict[str, ProcessEntry]:
    path = _processes_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {pid: ProcessEntry(**e) for pid, e in data.items()}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt processes.json, starting fresh")
        return {}


def _save(entries: Dict[str, ProcessEntry]) -> None:
    data = {pid: asdict(e) for pid, e in entries.items()}
    path = _processes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── CRUD ─────────────────────────────────────────────────────────────────

def register_process(pid: int, label: str = "",
                     command: str = "",
                     tags: Optional[List[str]] = None) -> str:
    """Register a background process and return its id."""
    import uuid
    pid_str = str(uuid.uuid4())[:12]
    entry = ProcessEntry(
        pid=pid, label=label, command=command,
        started_at=time.time(), tags=tags or [],
    )
    with _lock:
        entries = _load()
        entries[pid_str] = entry
        _save(entries)
    logger.info("Process registered: %s (PID %d, %s)", pid_str, pid, label)
    return pid_str


def update_status(entry_id: str, status: str,
                  exit_code: Optional[int] = None) -> bool:
    with _lock:
        entries = _load()
        entry = entries.get(entry_id)
        if not entry:
            return False
        entry.status = status
        if exit_code is not None:
            entry.exit_code = exit_code
        entries[entry_id] = entry
        _save(entries)
    return True


def list_processes(status: Optional[str] = None) -> List[ProcessEntry]:
    with _lock:
        entries = list(_load().values())
    if status:
        entries = [e for e in entries if e.status == status]
    entries.sort(key=lambda e: e.started_at, reverse=True)
    return entries


def get_process(entry_id: str) -> Optional[ProcessEntry]:
    with _lock:
        return _load().get(entry_id)


def reap_stale(max_age: float = 86400) -> int:
    """Mark processes older than *max_age* seconds as killed."""
    now = time.time()
    count = 0
    with _lock:
        entries = _load()
        for pid, entry in list(entries.items()):
            if entry.status == "running" and (now - entry.started_at) > max_age:
                entry.status = "killed"
                entry.exit_code = -1
                entries[pid] = entry
                count += 1
        _save(entries)
    if count:
        logger.info("Reaped %d stale process(es)", count)
    return count


def kill_process(entry_id: str, sig: int = signal.SIGTERM) -> bool:
    """Send a signal to a registered process. Returns True if killed."""
    with _lock:
        entries = _load()
        entry = entries.get(entry_id)
        if not entry:
            return False
        try:
            os.kill(entry.pid, sig)
            entry.status = "killed"
            entries[entry_id] = entry
            _save(entries)
            logger.info("Process %s (PID %d) killed with signal %d",
                        entry_id, entry.pid, sig)
            return True
        except ProcessLookupError:
            entry.status = "done"
            entries[entry_id] = entry
            _save(entries)
            return True
        except PermissionError:
            logger.warning("Cannot kill process %d: permission denied", entry.pid)
            return False


def kill_all() -> int:
    """Kill all running processes. Returns count of processes signalled."""
    count = 0
    for entry in list_processes(status="running"):
        if kill_process(
            [k for k, v in _load().items() if v.pid == entry.pid][0]
            if any(k for k, v in _load().items() if v.pid == entry.pid)
            else ""
        ):
            count += 1
    return count


def process_summary() -> str:
    """Return a summary of running processes for the system prompt."""
    running = list_processes(status="running")
    if not running:
        return "No running processes."
    lines = [f"Running processes ({len(running)}):"]
    for p in running[:10]:
        age = time.time() - p.started_at
        lines.append(f"- {p.label} (PID {p.pid}, {age:.0f}s)")
    return "\n".join(lines)
