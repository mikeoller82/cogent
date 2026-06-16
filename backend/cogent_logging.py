"""Structured logging for Cogent.

Analogous to Hermes' hermes_logging.py — rotating file handlers,
session-context injection, component-level filtering.

Usage:
    from cogent_logging import setup_logging, set_session_context
    setup_logging()
    set_session_context("session-abc")
    logger = logging.getLogger("cogent.module_name")
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from cogent_constants import (
    BACKEND_DIR,
    ENV_LOG_DIR,
    ENV_LOG_LEVEL,
    ensure_dirs,
)

# ── Sentinel ──────────────────────────────────────────────────────────────

_logging_initialized = False

# ── Session context ───────────────────────────────────────────────────────

_session_context = threading.local()

_LOG_FORMAT = "%(asctime)s %(levelname)s%(session_tag)s %(name)s: %(message)s"
_LOG_FORMAT_VERBOSE = "%(asctime)s - %(name)s - %(levelname)s%(session_tag)s - %(message)s"


def set_session_context(session_id: Optional[str]) -> None:
    """Attach a session ID to the current thread's log records."""
    _session_context.session_id = session_id


def clear_session_context() -> None:
    _session_context.session_id = None


def _get_session_tag() -> str:
    sid = getattr(_session_context, "session_id", None)
    return f" [{sid[:12]}]" if sid else ""


# ── Record factory ────────────────────────────────────────────────────────

_ORIGINAL_RECORD_FACTORY = logging.getLogRecordFactory()


def _session_record_factory(*args, **kwargs) -> logging.LogRecord:
    record = _ORIGINAL_RECORD_FACTORY(*args, **kwargs)
    record.session_tag = _get_session_tag()
    return record


logging.setLogRecordFactory(_session_record_factory)


# ── Component filter ──────────────────────────────────────────────────────

COMPONENT_PREFIXES = {
    "server":     ("cogent.server",),
    "llm":        ("cogent.llm_service",),
    "tools":      ("cogent.tools",),
    "loop":       ("cogent.loop_engine",),
    "scheduler":  ("cogent.scheduler",),
    "skills":     ("cogent.agent_skills", "cogent.skill_forge"),
    "hooks":      ("cogent.hooks",),
    "firecrawl":  ("cogent.firecrawl_service",),
    "state":      ("cogent.state",),
    "memory":     ("cogent.memory",),
}


class ComponentFilter(logging.Filter):
    """Only pass records whose logger name starts with one of *prefixes*."""

    def __init__(self, prefixes: tuple[str, ...]) -> None:
        super().__init__()
        self._prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self._prefixes)


# ── Main setup ────────────────────────────────────────────────────────────

def setup_logging(
    *,
    log_dir: Optional[str] = None,
    level: Optional[str] = None,
    force: bool = False,
) -> Path:
    """Configure Cogent logging with rotating file handlers.

    Idempotent — subsequent calls are no-ops unless *force=True*.
    Returns the log directory path.
    """
    global _logging_initialized
    if _logging_initialized and not force:
        return _resolve_log_dir(log_dir)

    _logging_initialized = True
    log_dir_path = _resolve_log_dir(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # gatekeeper is the handler level

    _add_rotating_handler(root_logger, log_dir_path / "cogent.log", level or "INFO")
    _add_rotating_handler(root_logger, log_dir_path / "cogent-errors.log", "ERROR")
    _add_rotating_handler(
        root_logger, log_dir_path / "cogent-debug.log", "DEBUG", max_bytes=10 * 1024 * 1024
    )

    # Suppress noisy third-party loggers
    for noisy in ("apscheduler", "httpx", "httpcore", "urllib3", "motor", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return log_dir_path


def setup_verbose_logging() -> None:
    """Enable DEBUG-level console logging (for ``--verbose`` mode)."""
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(_LOG_FORMAT_VERBOSE))
    logging.getLogger().addHandler(console)


# ── Helpers ───────────────────────────────────────────────────────────────

def _resolve_log_dir(override: Optional[str] = None) -> Path:
    if override:
        return Path(override)
    env_dir = os.getenv(ENV_LOG_DIR)
    if env_dir:
        return Path(env_dir)
    ensure_dirs()
    log_dir = BACKEND_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _add_rotating_handler(
    logger: logging.Logger,
    path: Path,
    level: str,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Add a RotatingFileHandler to *logger* if one doesn't already exist."""
    # Avoid duplicates — check if a handler for this path already exists
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and h.baseFilename == str(path):
            return

    handler = RotatingFileHandler(
        str(path), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
