"""Headroom integration — compress messages before LLM calls.

Wraps headroom-ai's compress() function to work with Cogent's message format
and provider chain.  Graceful fallback when headroom-ai is not installed.

60-95% fewer tokens, same answers.  Reversible (CCR) — originals cached.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from cogent_config import get_config

logger = logging.getLogger("cogent.headroom")

HAS_HEADROOM = False
try:
    from headroom import compress as _headroom_compress
    from headroom.compress import CompressConfig
    HAS_HEADROOM = True
except ImportError:
    pass


def compress_messages(
    messages: List[Dict[str, Any]],
    level: str | None = None,
) -> List[Dict[str, Any]]:
    """Compress a message list through Headroom.

    Args:
        messages: Standard OpenAI-format message list (role + content).
        level: Compression level from config (``"off"`` | ``"auto"`` |
            ``"aggressive"``).  Falls back to config value when ``None``.

    Returns:
        Compressed messages when headroom is enabled and installed;
        original messages otherwise.
    """
    cfg = get_config()
    if not cfg.headroom_enabled:
        return messages

    if level is None:
        level = cfg.headroom_compression_level

    if not HAS_HEADROOM:
        logger.warning("headroom-ai not installed — skipping compression")
        return messages

    if level == "off":
        return messages

    try:
        # Pass explicit config so user messages are compressed (headroom-ai
        # defaults to False, meaning only system messages get compressed).
        # Lower min_tokens_to_compress from 250 → 50 and protect_recent
        # from 4 → 2 so compression actually triggers on real conversations.
        if level == "aggressive":
            hr_cfg = CompressConfig(
                compress_user_messages=True,
                min_tokens_to_compress=30,
                protect_recent=1,
                target_ratio=0.5,
            )
        else:
            hr_cfg = CompressConfig(
                compress_user_messages=True,
                min_tokens_to_compress=50,
                protect_recent=2,
                target_ratio=0.6,
            )
        result = _headroom_compress(messages, model="auto", config=hr_cfg)

        original_len = len(str(messages))
        compressed_len = len(str(result.messages))

        if result.messages and compressed_len < original_len:
            savings = (1 - compressed_len / original_len) * 100
            logger.info(
                "Headroom: %d chars → %d chars (%.0f%% savings)",
                original_len, compressed_len, savings,
            )
            return result.messages

        logger.info("Headroom: no compression applied (output larger than input)")
        return messages

    except Exception as exc:
        logger.warning("Headroom compression failed: %s", exc)
        return messages
