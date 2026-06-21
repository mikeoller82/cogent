"""Well-known paths, directories, and constants for Cogent.

Analogous to Hermes' hermes_constants.py — centralised path resolution
so no module hardcodes relative paths or environment-variable names.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ── Project root discovery ────────────────────────────────────────────────

def _discover_project_root() -> Path:
    """Walk up from this file to find the project root (cogent/)."""
    here = Path(__file__).resolve().parent  # backend/
    # backend/ is one level below the project root
    marker = here / ".." / "AGENT.md"
    if marker.resolve().is_file():
        return marker.resolve().parent
    # fallback: two levels up from this file
    return here.parent


PROJECT_ROOT: Path = _discover_project_root()
BACKEND_DIR: Path = PROJECT_ROOT / "backend"
FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"
MEMORY_DIR: Path = PROJECT_ROOT / "memory"
SKILLS_DIR: Path = PROJECT_ROOT / ".cogent" / "skills"
HOOKS_DIR: Path = BACKEND_DIR / "hooks"
SESSIONS_DIR: Path = MEMORY_DIR / "sessions"
LOOPS_DIR: Path = MEMORY_DIR / "loops"
MEMORIES_DIR: Path = MEMORY_DIR / "memories"
ARTIFACTS_DIR: Path = BACKEND_DIR / "artifacts"
UPLOADS_DIR: Path = BACKEND_DIR / "uploads"
CONFIG_PATH: Path = PROJECT_ROOT / "config.yaml"


# ── Env-var names (single source of truth) ────────────────────────────────

ENV_KILOCODE_API_KEY = "KILOCODE_API_KEY"
ENV_MONGO_URL = "MONGO_URL"
ENV_DB_NAME = "DB_NAME"
ENV_FIRECRAWL_API_KEY = "FIRECRAWL_API_KEY"
ENV_FIRECRAWL_BASE_URL = "FIRECRAWL_BASE_URL"
ENV_LOG_LEVEL = "COGENT_LOG_LEVEL"
ENV_LOG_DIR = "COGENT_LOG_DIR"


# ── Defaults ──────────────────────────────────────────────────────────────

DEFAULT_MODEL = "nex-agi/nex-n2-pro:free"
DEFAULT_CHAT_COMPLETIONS_URL = "https://api.kilo.ai/api/gateway/chat/completions"
DEFAULT_WORKSPACE = "default"
DEFAULT_LOG_LEVEL = "INFO"
MAX_TOOL_TURNS = 25
MAX_LOOP_ITERATIONS = 10


# ── Platform helpers ──────────────────────────────────────────────────────

def is_linux() -> bool:
    return sys.platform == "linux"

def is_macos() -> bool:
    return sys.platform == "darwin"

def is_windows() -> bool:
    return sys.platform == "win32"

def is_container() -> bool:
    """Return True when running inside a Docker/Podman container."""
    cgroup = Path("/proc/1/cgroup")
    if cgroup.is_file():
        try:
            text = cgroup.read_text(encoding="utf-8")
            if "docker" in text or "podman" in text:
                return True
        except OSError:
            pass
    return Path("/.dockerenv").is_file()


# ── Convenience ───────────────────────────────────────────────────────────

def ensure_dirs() -> None:
    """Create all well-known directories that should exist on disk."""
    for d in (MEMORY_DIR, LOOPS_DIR, MEMORIES_DIR, SESSIONS_DIR,
              ARTIFACTS_DIR, UPLOADS_DIR, HOOKS_DIR):
        d.mkdir(parents=True, exist_ok=True)
