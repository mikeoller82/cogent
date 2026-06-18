"""Virtual Provider — rate limiter + automatic fallback chain for LLM providers.

When the active provider returns 429 Rate Limited, Cogent automatically
falls back to the next provider in the priority chain and reports the switch
back to the UI.  A configurable delay (randomised in a range) is enforced
between every request to stay within fair-use quotas.

Usage::

    from cogent_providers import VirtualProvider
    vp = VirtualProvider()
    content = vp.chat(messages)

Config (``config.yaml``)::

    rate_limit:
      enabled: true
      min_delay_ms: 5000
      max_delay_ms: 7000

    providers:
      - name: kilocode
        base_url: https://api.kilo.ai/api/gateway/chat/completions
        model: nvidia/nemotron-3-ultra-550b-a55b:free
        api_key_env: KILOCODE_API_KEY
        priority: 1
    - name: kilocode
        base_url: https://api.kilo.ai/api/gateway/chat/completions
        model: nex-agi/nex-n2-pro:free
        api_key_env: KILOCODE_API_KEY
        priority: 2
    - name: openrouter
        base_url: https://openrouter.ai/api/v1/chat/completions
        model: openrouter/owl-alpha
        api_key_env: OPENROUTER_API_KEY
        priority: 3

The provider list sorted by priority forms the fallback chain.
"""

from __future__ import annotations

import asyncio
import os
import time
import random
import logging
from typing import List, Dict, Any, Optional

import requests

try:
    import ollama as _ollama
    HAS_OLLAMA = True
except ImportError:
    _ollama = None  # type: ignore
    HAS_OLLAMA = False

from cogent_config import get_config

logger = logging.getLogger("cogent.providers")


def _load_providers() -> List[Dict[str, Any]]:
    """Read the provider list from config and sort by priority."""
    cfg = get_config()
    provs: list = cfg.providers
    sorted_provs = sorted(provs, key=lambda p: p.get("priority", 99))
    return sorted_provs


def _pick_api_key(entry: Dict[str, Any]) -> Optional[str]:
    """Read the API key for a provider entry from its env-var name."""
    env_var = entry.get("api_key_env", "")
    if not env_var:
        return None
    return os.environ.get(env_var)


class RateLimiter:
    """Simple token-bucket-inspired rate limiter.

    Enforces a randomised delay between successive requests so that free-tier
    quotas are not accidentally exceeded.
    """

    def __init__(self, enabled: bool = True,
                 min_delay_ms: int = 5000,
                 max_delay_ms: int = 7000) -> None:
        self.enabled = enabled
        self.min_delay = min_delay_ms / 1000.0
        self.max_delay = max_delay_ms / 1000.0
        self._last_ts: float = 0.0

    async def wait_if_needed(self) -> float:
        """Wait (non-blocking) until the minimum inter-request delay has elapsed.

        Returns the delay that was actually applied (seconds).
        """
        if not self.enabled:
            return 0.0

        now = time.monotonic()
        elapsed = now - self._last_ts
        target = random.uniform(self.min_delay, self.max_delay)

        if elapsed < target:
            sleep_for = target - elapsed
            await asyncio.sleep(sleep_for)
            self._last_ts = time.monotonic()
            return sleep_for

        self._last_ts = now
        return 0.0

    def reset(self) -> None:
        self._last_ts = 0.0


class VirtualProvider:
    """Multi-provider chat completions with rate limiting and fallback.

    Uses a priority-sorted provider chain.  When the current provider returns a
    429 status, the next provider in the chain is tried automatically.
    """

    def __init__(self) -> None:
        self._providers: List[Dict[str, Any]] = []
        self._rate_limiter = RateLimiter()
        self._current_idx: int = 0
        self._fallback_log: List[str] = []
        self.reload_config()

    # ── Public API ──────────────────────────────────────────────────────

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Send a chat-completion request through the provider chain (async).

        Returns the response text.

        Raises RuntimeError when every provider in the chain has been
        exhausted.
        """
        last_error: Optional[str] = None

        for attempt in range(len(self._providers)):
            idx = (self._current_idx + attempt) % len(self._providers)
            entry = self._providers[idx]

            api_key = _pick_api_key(entry)
            if not api_key:
                logger.warning("Provider %s skipped — no API key", entry.get("name"))
                if attempt == 0:
                    self._fallback(entry.get("name", "?"), "missing API key")
                continue

            # Rate limit before hitting this provider (non-blocking)
            await self._rate_limiter.wait_if_needed()

            # Post is sync (requests / ollama); run in thread to avoid blocking the event loop
            try:
                result = await asyncio.to_thread(self._post, entry, api_key, messages, **kwargs)
                logger.info("Provider %s returned type=%s len=%d",
                            entry.get("name"), type(result).__name__,
                            len(result) if isinstance(result, str) else -1)
                return result
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                body = exc.response.text[:300] if exc.response is not None else ""
                logger.warning(
                    "Provider %s HTTP %d — %s",
                    entry.get("name"), status, body,
                )

                if status == 429:
                    reason = f"429 rate limited: {body}"
                    last_error = f"{entry.get('name', '?')}: {reason}"
                    self._fallback(entry.get("name", "?"), reason)
                    continue

                if status >= 500:
                    reason = f"{status} server error"
                    last_error = f"{entry.get('name', '?')}: {reason}"
                    self._fallback(entry.get("name", "?"), reason)
                    continue

                raise

            except requests.ConnectionError as exc:
                logger.warning("Provider %s connection error — %s",
                               entry.get("name"), exc)
                last_error = f"{entry.get('name', '?')}: connection error: {exc}"
                self._fallback(entry.get("name", "?"), f"connection error: {exc}")
                continue

            except RuntimeError as exc:
                logger.warning("Provider %s RuntimeError — %s", entry.get("name"), exc)
                last_error = f"{entry.get('name', '?')}: malformed response: {exc}"
                self._fallback(entry.get("name", "?"), f"malformed response: {exc}")
                continue

        raise RuntimeError(
            f"All providers exhausted. Last error: {last_error or '(no details)'}"
        )

    # ── Status queries ──────────────────────────────────────────────────

    @property
    def active_provider_name(self) -> str:
        entry = self._providers[self._current_idx] if self._providers else {}
        return entry.get("name", "none")

    @property
    def fallback_events(self) -> List[str]:
        return list(self._fallback_log)

    def drain_fallback_events(self) -> List[str]:
        events = self._fallback_log
        self._fallback_log = []
        return events

    # ── Config reload ───────────────────────────────────────────────────

    def reload_config(self) -> None:
        cfg = get_config()
        self._providers = _load_providers()
        self._rate_limiter = RateLimiter(
            enabled=cfg.rate_limit_enabled,
            min_delay_ms=cfg.rate_limit_min_delay_ms,
            max_delay_ms=cfg.rate_limit_max_delay_ms,
        )
        self._current_idx = 0

    # ── Internals ───────────────────────────────────────────────────────

    def _fallback(self, from_name: str, reason: str) -> None:
        """Advance to the next provider and log the fallback."""
        self._current_idx = (self._current_idx + 1) % len(self._providers)
        next_name = self._providers[self._current_idx].get("name", "?") if self._providers else "?"
        msg = f"{from_name} → {next_name}: {reason}"
        self._fallback_log.append(msg)
        logger.info("Provider fallback: %s", msg)

    def _post(self, entry: Dict[str, Any], api_key: str,
              messages: List[Dict[str, str]], **kwargs) -> str:
        """Perform the actual API call to the provider.

        Dispatches to the appropriate backend based on the ``library``
        field in the provider entry:

        * ``None`` / ``"openai"`` (default) — OpenAI-compatible HTTP POST
        * ``"ollama"`` — local Ollama via the ``ollama`` Python library
        * ``"ollama-cloud"`` — Ollama Cloud via the ``ollama`` library
        """
        library = entry.get("library")

        if library in ("ollama", "ollama-cloud"):
            if not HAS_OLLAMA:
                raise RuntimeError(
                    f"Provider {entry.get('name')} requires 'ollama' package — "
                    f"run: pip install ollama"
                )
            return self._post_ollama(entry, messages, **kwargs)

        # Default: OpenAI-compatible HTTP POST
        return self._post_http(entry, api_key, messages, **kwargs)

    def _post_http(self, entry: Dict[str, Any], api_key: str,
                   messages: List[Dict[str, str]], **kwargs) -> str:
        """OpenAI-compatible HTTP POST backend."""
        url = entry.get("base_url", "")
        model = entry.get("model", "")
        max_tokens = kwargs.get("max_tokens", 4000)

        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=kwargs.get("timeout", 120),
        )

        if resp.status_code >= 400:
            raise requests.HTTPError(response=resp)

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(
                f"Provider {entry.get('name')} response missing choices[0].message.content"
            )
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Provider {entry.get('name')} response had empty content"
            )
        return content

    def _post_ollama(self, entry: Dict[str, Any],
                     messages: List[Dict[str, str]], **kwargs) -> str:
        """Call a model via the ``ollama`` Python library (local or cloud)."""
        library = entry.get("library", "ollama")
        model = entry.get("model", "")
        api_key = _pick_api_key(entry)

        if library == "ollama-cloud":
            host = entry.get("base_url", "https://cloud.ollama.ai")
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            client = _ollama.Client(host=host, headers=headers)
            response = client.chat(model=model, messages=messages)
        elif api_key:
            # Local Ollama with API key (proxied or authenticated)
            host = entry.get("base_url", "http://localhost:11434")
            client = _ollama.Client(
                host=host,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response = client.chat(model=model, messages=messages)
        else:
            # Plain local Ollama — no auth needed
            response = _ollama.chat(model=model, messages=messages)

        content = response.message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Provider {entry.get('name')} returned empty content"
            )
        return content

    # ── Config reload ───────────────────────────────────────────────────

# ── Module-level singleton ──────────────────────────────────────────────

_provider: Optional[VirtualProvider] = None


def get_provider(*, reload: bool = False) -> VirtualProvider:
    """Return the global VirtualProvider singleton."""
    global _provider
    if _provider is None or reload:
        _provider = VirtualProvider()
    return _provider
