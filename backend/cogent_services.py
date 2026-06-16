"""Auxiliary service router for side-task LLM calls.

Analogous to Hermes' ``auxiliary_client.py`` — provides a single
resolution chain for vision analysis, web extraction, and context
compression tasks that may use a different model than the main chat.

Resolution order (``auto`` mode):
  1. Configured auxiliary provider (``config.yaml auxiliary.*.provider``)
  2. Main provider (the chat model)
  3. Fallback: KiloCode with the default model

Usage::

    from cogent_services import auxiliary_complete

    # Use configured auxiliary provider for compression
    summary = await auxiliary_complete(
        task="compression",
        messages=[{"role": "user", "content": "Summarise this: ..."}],
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from cogent_config import get_config
from cogent_providers import KiloCodeProvider, ProviderProfile, get_provider

logger = logging.getLogger("cogent.services")

# Task types recognised in ``config.yaml auxiliary:``
_TASK_TYPES = ("vision", "web_extract", "compression", "skills_hub", "approval",
               "mcp", "title_generation")


async def auxiliary_complete(
    task: str,
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 120,
) -> str:
    """Send a completion through the best available provider for *task*.

    Resolution:
      1. Explicit ``auxiliary.<task>.provider`` + ``auxiliary.<task>.model``
         from ``config.yaml``.
      2. Main provider fallback.

    Args:
        task: One of the recognised task types.
        messages: Chat messages for the LLM.
        model: Override model name.
        max_tokens: Override max tokens.
        timeout: Request timeout in seconds.

    Returns:
        The response text.
    """
    cfg = get_config()
    aux_cfg = cfg.raw().get("auxiliary", {}).get(task, {})

    # Resolve provider
    provider_name = aux_cfg.get("provider", "") or cfg.model_provider
    provider = get_provider(provider_name)

    # Resolve model
    model_name = model or aux_cfg.get("model", "") or cfg.model_name

    # Resolve base_url override
    kwargs: Dict[str, Any] = {"timeout": timeout}
    aux_url = aux_cfg.get("base_url", "")
    if aux_url:
        kwargs["base_url"] = aux_url

    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    try:
        return provider.complete(messages, model=model_name, **kwargs)
    except Exception as exc:
        logger.warning("Auxiliary provider %s failed for task %s, "
                       "trying main provider: %s", provider_name, task, exc)
        # Fallback to main provider
        main = get_provider(cfg.model_provider)
        return main.complete(messages, model=cfg.model_name, **kwargs)


async def vision_analyze(image_data: str, prompt: str) -> str:
    """Analyse an image using the auxiliary vision provider.

    Args:
        image_data: Base64-encoded image data.
        prompt: What to ask about the image.

    Returns:
        The analysis text.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                },
            ],
        }
    ]
    return await auxiliary_complete("vision", messages)


async def extract_web_content(content: str, instruction: str = "") -> str:
    """Extract structured information from web content.

    Args:
        content: Raw markdown or HTML content.
        instruction: Optional extraction guidance.

    Returns:
        Extracted/structured text.
    """
    prompt = f"Extract the key information from this content:\n\n{content}"
    if instruction:
        prompt = f"{instruction}\n\n{content}"

    messages = [{"role": "user", "content": prompt}]
    return await auxiliary_complete("web_extract", messages)


async def compress_context(context: str, target_length: str = "medium") -> str:
    """Compress conversation context for window management.

    Args:
        context: The raw context text to compress.
        target_length: ``short`` | ``medium`` | ``long``.

    Returns:
        Compressed context summary.
    """
    lengths = {"short": "2-3 sentences", "medium": "one paragraph", "long": "detailed"}
    target = lengths.get(target_length, "one paragraph")

    prompt = (
        f"Compress the following conversation/context into {target}. "
        f"Keep all facts, decisions, and action items. "
        f"Preserve the original meaning and details for later recall.\n\n"
        f"{context}"
    )
    messages = [{"role": "user", "content": prompt}]
    return await auxiliary_complete("compression", messages)
