"""Centralised configuration loader for Cogent.

Analogous to Hermes' config.yaml + runtime config resolution.

Layers (later overrides earlier):
  1. Defaults (embedded in this module)
  2. ``config.yaml`` at project root
  3. Environment variables (``COGENT_*`` prefix or per-key overrides)
  4. In-process overrides via :func:`set_override`
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from cogent_constants import (
    CONFIG_PATH,
    DEFAULT_CHAT_COMPLETIONS_URL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MODEL,
    DEFAULT_WORKSPACE,
    ENV_DB_NAME,
    ENV_FIRECRAWL_API_KEY,
    ENV_FIRECRAWL_BASE_URL,
    ENV_KILOCODE_API_KEY,
    ENV_MONGO_URL,
    MAX_LOOP_ITERATIONS,
    MAX_TOOL_TURNS,
)


# ── Default config ────────────────────────────────────────────────────────
_DEFAULTS: Dict[str, Any] = {
    "model": {
        "base_url": DEFAULT_CHAT_COMPLETIONS_URL,
        "default": DEFAULT_MODEL,
        "provider": "kilocode",
    },
    "agent": {
        "max_turns": MAX_TOOL_TURNS,
        "max_iterations": MAX_LOOP_ITERATIONS,
        "verbose": False,
        "reasoning_effort": "medium",
    },
    "rate_limit": {
        "enabled": True,
        "min_delay_ms": 5000,
        "max_delay_ms": 7000,
    },
    "providers": [
        {
            "name": "kilocode",
            "base_url": "https://api.kilo.ai/api/gateway/chat/completions",
            "model": "nex-agi/nex-n2-pro:free",
            "api_key_env": "KILOCODE_API_KEY",
            "priority": 1,
        },
        {
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "model": "google/gemini-2.0-flash-exp:free",
            "api_key_env": "OPENROUTER_API_KEY",
            "priority": 2,
        },
        {
            "name": "opencode-zen",
            "base_url": "https://opencode.ai/zen/v1/chat/completions",
            "model": "deepseek-v4-flash-free",
            "api_key_env": "OPENCODE_API_KEY",
            "priority": 3,
        },
        {
            "name": "ollama-local",
            "library": "ollama",
            "model": "qwen3.6",
            "api_key_env": "OLLAMA_API_KEY",
            "priority": 4,
        },
        {
            "name": "ollama-cloud",
            "library": "ollama-cloud",
            "base_url": "https://cloud.ollama.ai",
            "model": "glm-5.2:cloud",
            "api_key_env": "OLLAMA_API_KEY",
            "priority": 5,
        },
    ],
    "workspace": {
        "default": DEFAULT_WORKSPACE,
    },
    "logging": {
        "level": DEFAULT_LOG_LEVEL,
        "dir": "",
    },
    "web": {
        "search_backend": "firecrawl",
        "scrape_backend": "firecrawl",
    },
    "checkpoints": {
        "enabled": True,
        "max_snapshots": 10,
    },
    "auxiliary": {
        "vision": {"provider": "auto"},
        "web_extract": {"provider": "auto"},
        "compression": {"provider": "auto"},
    },
}

# Environment-variable overrides: KEY -> config path (dot-separated)
_ENV_MAP: Dict[str, str] = {
    ENV_KILOCODE_API_KEY: "model.api_key",
    ENV_MONGO_URL: "database.mongo_url",
    ENV_DB_NAME: "database.db_name",
    ENV_FIRECRAWL_API_KEY: "web.firecrawl_api_key",
    ENV_FIRECRAWL_BASE_URL: "web.firecrawl_base_url",
}


# ── In-process overrides ──────────────────────────────────────────────────

_overrides: Dict[str, Any] = {}


def set_override(key: str, value: Any) -> None:
    """Set a runtime override (e.g. for testing). Use dot-separated *key*."""
    _overrides[key] = value


def clear_overrides() -> None:
    _overrides.clear()


# ── Config class ──────────────────────────────────────────────────────────

class CogentConfig:
    """Immutable view over merged config layers."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    # Models
    @property
    def model_name(self) -> str:
        return self._data.get("model", {}).get("default", DEFAULT_MODEL)

    @property
    def model_base_url(self) -> str:
        return self._data.get("model", {}).get("base_url", DEFAULT_CHAT_COMPLETIONS_URL)

    @property
    def model_api_key(self) -> str:
        return self._data.get("model", {}).get("api_key", "")


    # Rate limit
    @property
    def rate_limit_enabled(self) -> bool:
        return bool(self._data.get("rate_limit", {}).get("enabled", True))

    @property
    def rate_limit_min_delay_ms(self) -> int:
        return int(self._data.get("rate_limit", {}).get("min_delay_ms", 5000))

    @property
    def rate_limit_max_delay_ms(self) -> int:
        return int(self._data.get("rate_limit", {}).get("max_delay_ms", 7000))

    # Virtual Provider chain
    @property
    def providers(self) -> list:
        return list(self._data.get("providers", []))

    @property
    def active_provider(self) -> str:
        return self._data.get("_active_provider", self.model_provider)

    @property
    def model_provider(self) -> str:
        return self._data.get("model", {}).get("provider", "kilocode")

    # Agent
    @property
    def max_turns(self) -> int:
        return int(self._data.get("agent", {}).get("max_turns", MAX_TOOL_TURNS))

    @property
    def max_iterations(self) -> int:
        return int(self._data.get("agent", {}).get("max_iterations", MAX_LOOP_ITERATIONS))

    @property
    def agent_verbose(self) -> bool:
        return bool(self._data.get("agent", {}).get("verbose", False))

    @property
    def reasoning_effort(self) -> str:
        return self._data.get("agent", {}).get("reasoning_effort", "medium")

    # Database
    @property
    def mongo_url(self) -> str:
        return self._data.get("database", {}).get("mongo_url", "")

    @property
    def db_name(self) -> str:
        return self._data.get("database", {}).get("db_name", "cogent")

    # Workspace
    @property
    def default_workspace(self) -> str:
        return self._data.get("workspace", {}).get("default", DEFAULT_WORKSPACE)

    # Web
    @property
    def firecrawl_api_key(self) -> str:
        return self._data.get("web", {}).get("firecrawl_api_key", "")

    @property
    def firecrawl_base_url(self) -> str:
        return self._data.get("web", {}).get("firecrawl_base_url", "")

    @property
    def search_backend(self) -> str:
        return self._data.get("web", {}).get("search_backend", "firecrawl")

    # Logging
    @property
    def log_level(self) -> str:
        return self._data.get("logging", {}).get("level", DEFAULT_LOG_LEVEL)

    @property
    def log_dir(self) -> str:
        return self._data.get("logging", {}).get("dir", "")

    # Raw access
    def raw(self) -> Dict[str, Any]:
        return dict(self._data)


# ── Loader ────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursive dict merge — *override* wins."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _dot_set(d: dict, dotted: str, value: Any) -> None:
    """Set a value at a dot-separated path in a nested dict."""
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def load_config(path: Optional[Path] = None, *, apply_env: bool = True) -> CogentConfig:
    """Load config from YAML + env vars + overrides.

    Args:
        path: Path to ``config.yaml``. Defaults to :data:`CONFIG_PATH`.
        apply_env: When True, environment variables override YAML values.
    """
    cfg: Dict[str, Any] = dict(_DEFAULTS)

    # Layer 1: file
    config_file = path or CONFIG_PATH
    if config_file.is_file():
        with open(config_file, encoding="utf-8") as f:
            file_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, file_cfg)

    # Layer 2: environment
    if apply_env:
        for env_var, config_key in _ENV_MAP.items():
            val = os.environ.get(env_var)
            if val:
                _dot_set(cfg, config_key, val)

    # Layer 3: runtime overrides
    for key, val in _overrides.items():
        _dot_set(cfg, key, val)

    return CogentConfig(cfg)


# ── Singleton shortcut ────────────────────────────────────────────────────

_config: Optional[CogentConfig] = None


def get_config(*, reload: bool = False) -> CogentConfig:
    """Return the global config singleton, loading it on first call."""
    global _config
    if _config is None or reload:
        _config = load_config()
    return _config
