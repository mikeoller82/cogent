"""Provider abstraction for LLM backends.

Analogous to Hermes' ``providers/`` — declares a ``ProviderProfile``
dataclass and a registry so Cogent can switch between LLM backends
without changing call sites.

Currently ships one built-in provider (KiloCode).  Additional providers
can be registered at runtime via :func:`register_provider`.

Usage::

    from cogent_providers import get_provider, register_provider

    # Built-in
    provider = get_provider("kilocode")
    response = provider.complete(messages)

    # Register custom
    register_provider(CustomProvider(name="my-llm", ...))
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from cogent_config import get_config
from cogent_constants import ENV_KILOCODE_API_KEY

logger = logging.getLogger("cogent.providers")


# ── Profile ────────────────────────────────────────────────────────────────

@dataclass
class ProviderProfile:
    """Declarative description of an LLM provider's behaviour.

    Does NOT own client construction or streaming — those are handled
    by the transport layer (:meth:`Provider.complete`).
    """
    name: str
    base_url: str = ""
    default_model: str = ""
    api_key_env: str = ""           # env var name for the API key
    supports_streaming: bool = True
    supports_vision: bool = False
    max_tokens: int = 4096
    extra_headers: Dict[str, str] = field(default_factory=dict)
    extra_body: Dict[str, Any] = field(default_factory=dict)


# ── Base Provider ─────────────────────────────────────────────────────────

class Provider:
    """Base class for an LLM provider transport.

    Subclasses override :meth:`complete` and optionally :meth:`stream`.
    """

    def __init__(self, profile: ProviderProfile) -> None:
        self.profile = profile

    def _resolve_api_key(self) -> str:
        key = os.environ.get(self.profile.api_key_env, "")
        if not key:
            # Fall back to config
            cfg = get_config()
            key = cfg.model_api_key
        return key

    def complete(self, messages: List[Dict[str, str]],
                 model: Optional[str] = None,
                 **kwargs: Any) -> str:
        """Send a chat completion request.  Returns the response text."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.profile.name


# ── KiloCode provider ────────────────────────────────────────────────────

class KiloCodeProvider(Provider):
    """Provider for KiloCode's OpenAI-compatible API."""

    def complete(self, messages: List[Dict[str, str]],
                 model: Optional[str] = None,
                 **kwargs: Any) -> str:
        cfg = get_config()
        api_key = self._resolve_api_key()
        if not api_key:
            raise RuntimeError(f"Missing API key for {self.name} "
                               f"(set {self.profile.api_key_env})")

        url = kwargs.get("base_url") or self.profile.base_url or cfg.model_base_url
        model_name = model or self.profile.default_model or cfg.model_name

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **self.profile.extra_headers,
            },
            json={
                "model": model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.profile.max_tokens),
                **self.profile.extra_body,
            },
            timeout=kwargs.get("timeout", 120),
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"{self.name} error {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"{self.name} response missing choices[0].message.content"
            ) from exc
        if not isinstance(content, str):
            raise RuntimeError(f"{self.name} response content was not text")
        return content


# ── Registry ──────────────────────────────────────────────────────────────

_registry: Dict[str, Provider] = {}
_lock = threading.Lock()


def register_provider(provider: Provider, *, alias: Optional[str] = None) -> None:
    """Register a provider instance by name."""
    with _lock:
        _registry[provider.name] = provider
        if alias:
            _registry[alias] = provider
    logger.info("Provider registered: %s", provider.name)


def get_provider(name: Optional[str] = None) -> Provider:
    """Look up a provider by name.  Defaults to the configured provider."""
    with _lock:
        if not name:
            cfg = get_config()
            name = cfg.model_provider
        provider = _registry.get(name)
        if provider:
            return provider
        raise KeyError(f"Unknown provider: {name!r}. "
                       f"Available: {list(_registry.keys())}")


def list_providers() -> List[str]:
    with _lock:
        return list(_registry.keys())


# ── Auto-register built-in providers ─────────────────────────────────────

def _init_builtins() -> None:
    cfg = get_config()
    profile = ProviderProfile(
        name="kilocode",
        base_url=cfg.model_base_url,
        default_model=cfg.model_name,
        api_key_env=ENV_KILOCODE_API_KEY,
    )
    register_provider(KiloCodeProvider(profile), alias="default")


_init_builtins()
