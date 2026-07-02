"""Mixture-of-Agents (MoA) engine for Cogent.

Implements the MoA framework from togethercomputer/MoA:
- Fan out to N reference models in parallel
- Aggregate their responses into a single high-quality output
- Optionally repeat for multiple layers

Only used for the main agent output loop. Evaluation and reflection
continue to use single-model calls for speed and cost.

Usage::

    from cogent_moa import moa_chat
    result = await moa_chat(messages)
"""

from __future__ import annotations

import asyncio
import logging
import time
import random
from typing import Any, Dict, List, Optional

import requests

from cogent_config import get_config
from cogent_providers import _pick_api_key

logger = logging.getLogger("cogent.moa")

AGGREGATOR_SYSTEM_PROMPT = (
    "You have been provided with a set of responses from various open-source models "
    "to the latest user query. Your task is to synthesize these responses into a single, "
    "high-quality response. It is crucial to critically evaluate the information provided "
    "in these responses, recognizing that some of it may be biased or incorrect. Your "
    "response should not simply replicate the given answers but should offer a refined, "
    "accurate, and comprehensive reply to the instruction. Ensure your response is "
    "well-structured, coherent, and adheres to the highest standards of accuracy and "
    "reliability.\n\nResponses from models:"
)


def _find_provider(name: str) -> Optional[Dict[str, Any]]:
    """Look up a provider entry by name from the full config list."""
    cfg = get_config()
    for entry in cfg.providers:
        if entry.get("name") == name:
            return entry
    return None


def _post_to_provider(
    entry: Dict[str, Any],
    api_key: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 16000,
    timeout: int = 180,
) -> str:
    """Send a single chat-completion request to a provider (no fallback).

    Handles both OpenAI-compatible HTTP and ollama-cloud backends.
    Returns the response text or raises RuntimeError.
    """
    library = entry.get("library")

    if library in ("ollama", "ollama-cloud"):
        try:
            import ollama as _ollama
        except ImportError:
            raise RuntimeError(
                f"Provider {entry.get('name')} requires 'ollama' package — "
                f"run: pip install ollama"
            )

        if library == "ollama-cloud":
            host = entry.get("base_url", "https://cloud.ollama.ai")
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            client = _ollama.Client(host=host, headers=headers)
            response = client.chat(
                model=entry.get("model", ""),
                messages=messages,
            )
        elif api_key:
            host = entry.get("base_url", "http://localhost:11434")
            client = _ollama.Client(
                host=host,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response = client.chat(
                model=entry.get("model", ""),
                messages=messages,
            )
        else:
            response = _ollama.chat(
                model=entry.get("model", ""),
                messages=messages,
            )

        content = response.message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Provider {entry.get('name')} returned empty content"
            )
        return content

    # Default: OpenAI-compatible HTTP POST
    url = entry.get("base_url", "")
    model = entry.get("model", "")

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
        timeout=timeout,
    )

    if resp.status_code >= 400:
        raise requests.HTTPError(response=resp)

    data = resp.json()
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        body_preview = resp.text[:500]
        raise RuntimeError(
            f"Provider {entry.get('name')} response missing choices[0].message — "
            f"body: {body_preview}"
        )

    content = msg.get("content") or ""
    if not content.strip():
        reasoning = msg.get("reasoning_content") or ""
        if reasoning.strip():
            content = reasoning
        else:
            raise RuntimeError(
                f"Provider {entry.get('name')} returned empty content"
            )
    return content


async def _call_reference(
    entry: Dict[str, Any],
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Call a single reference provider with retries.

    Returns the response text, or None if all retries failed.
    """
    name = entry.get("name", "?")
    api_key = _pick_api_key(entry)
    if not api_key:
        logger.warning("MoA reference %s skipped — no API key", name)
        return None

    for attempt, sleep_time in enumerate([1, 2, 4]):
        try:
            result = await asyncio.to_thread(
                _post_to_provider,
                entry,
                api_key,
                messages,
                max_tokens=max_tokens,
            )
            logger.info("MoA reference %s returned %d chars", name, len(result))
            return result
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429:
                logger.warning(
                    "MoA reference %s 429 rate limited (attempt %d) — retrying in %ds",
                    name, attempt + 1, sleep_time,
                )
                await asyncio.sleep(sleep_time)
                continue
            logger.warning("MoA reference %s HTTP %d — skipping", name, status)
            return None
        except (RuntimeError, requests.Timeout, requests.ConnectionError) as exc:
            logger.warning("MoA reference %s error — %s", name, exc)
            if attempt < len([1, 2, 4]) - 1:
                await asyncio.sleep(sleep_time)
                continue
            return None

    return None


def _extract_user_prompt(messages: List[Dict[str, str]]) -> str:
    """Extract the last user message content from the messages list."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _build_aggregator_messages(
    user_prompt: str,
    reference_responses: List[str],
) -> List[Dict[str, str]]:
    """Build the messages for the aggregator call.

    Includes the aggregator system prompt with all reference responses,
    plus the original user prompt.
    """
    numbered = "\n".join(
        f"{i + 1}. {resp}" for i, resp in enumerate(reference_responses)
    )
    system_content = AGGREGATOR_SYSTEM_PROMPT + "\n" + numbered

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_prompt},
    ]


async def moa_chat(
    messages: List[Dict[str, str]],
    *,
    reference_providers: Optional[List[str]] = None,
    aggregator_provider: Optional[str] = None,
    layers: Optional[int] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """Run the Mixture-of-Agents pipeline.

    1. Fan out to all reference providers in parallel
    2. Collect successful responses
    3. Aggregate via the aggregator model
    4. Optionally repeat for multiple layers

    Falls back to a single-model response if all reference calls fail.

    Args:
        messages: The chat messages (system + user).
        reference_providers: Provider names to fan out to. Defaults to config.
        aggregator_provider: Provider name for aggregation. Defaults to config.
        layers: Number of aggregation layers. Defaults to config (2).
        max_tokens: Max tokens per call. Defaults to config.
        temperature: Sampling temperature. Defaults to config.

    Returns:
        The final aggregated response text.
    """
    cfg = get_config()
    ref_names = reference_providers or cfg.moa_reference_providers
    agg_name = aggregator_provider or cfg.moa_aggregator_provider
    num_layers = layers or cfg.moa_layers
    tok = max_tokens or cfg.moa_max_tokens
    temp = temperature or cfg.moa_temperature

    user_prompt = _extract_user_prompt(messages)

    # Look up provider entries
    ref_entries = []
    for name in ref_names:
        entry = _find_provider(name)
        if entry:
            ref_entries.append(entry)
        else:
            logger.warning("MoA: reference provider '%s' not found in config — skipping", name)

    agg_entry = _find_provider(agg_name)
    if not agg_entry:
        raise RuntimeError(f"MoA: aggregator provider '{agg_name}' not found in config")

    if not ref_entries:
        raise RuntimeError("MoA: no valid reference providers found in config")

    logger.info(
        "MoA starting: %d references, %d layers, aggregator=%s",
        len(ref_entries), num_layers, agg_name,
    )

    # ── Layer 1: fan out to reference models ───────────────────────────
    # Add a small stagger to avoid thundering herd on free-tier APIs
    async def _staggered_call(entry: Dict[str, Any], delay: float) -> Optional[str]:
        await asyncio.sleep(delay)
        return await _call_reference(entry, messages, tok, temp)

    stagger_range = min(2.0, 0.5 * len(ref_entries))
    tasks = [
        _staggered_call(entry, i * random.uniform(0.3, stagger_range))
        for i, entry in enumerate(ref_entries)
    ]
    results: List[str] = []
    raw_results = await asyncio.gather(*tasks)

    for i, result in enumerate(raw_results):
        if result:
            results.append(result)
        else:
            logger.warning("MoA: reference %s failed — continuing with %d responses",
                          ref_entries[i].get("name", "?"), len(results))

    if not results:
        raise RuntimeError("MoA: all reference model calls failed")

    logger.info("MoA layer 1: %d/%d references succeeded", len(results), len(ref_entries))

    # ── Layers 2+: aggregate through the aggregator model ──────────────
    current_responses = results

    for layer in range(1, num_layers):
        logger.info("MoA layer %d/%d: aggregating %d responses", layer + 1, num_layers, len(current_responses))

        agg_messages = _build_aggregator_messages(user_prompt, current_responses)
        agg_api_key = _pick_api_key(agg_entry)

        if not agg_api_key:
            logger.warning("MoA: aggregator '%s' has no API key — using last reference response", agg_name)
            break

        try:
            aggregated = await asyncio.to_thread(
                _post_to_provider,
                agg_entry,
                agg_api_key,
                agg_messages,
                max_tokens=tok,
            )
            logger.info("MoA layer %d aggregation: %d chars", layer + 1, len(aggregated))
        except Exception as exc:
            logger.warning("MoA: aggregator failed at layer %d — %s", layer + 1, exc)
            break

        # For multi-layer: the aggregated output becomes a new reference response
        current_responses = [aggregated]

    final = current_responses[-1] if current_responses else results[-1]
    logger.info("MoA complete: %d chars output", len(final))
    return final
