"""Context compression — summarize old turns to fit within token budgets."""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.agent.context_compressor")

# Rough token counter (4 chars ~ 1 token for English text)
def _estimate_tokens(text: str) -> int:
    return len(text) // 4

def estimate_message_tokens(messages: List[Dict[str, Any]]) -> int:
    """Estimate total tokens in a message list."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += _estimate_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += _estimate_tokens(part.get("text", ""))
        total += 50  # overhead per message
    return total

def compress_messages(messages: List[Dict[str, Any]], max_tokens: int = 32000) -> List[Dict[str, Any]]:
    """Compress message list to fit within max_tokens by summarizing middle turns.

    Strategy (matching Hermes):
    - Always keep the system prompt (first message) — protected
    - Always keep the last N messages (default 4) — protected
    - Summarize everything between into a single synthetic message
    - If still over budget, also summarize the protected tail
    """
    if not messages or estimate_message_tokens(messages) <= max_tokens:
        return messages

    # Protected turns: first (system) + last 4
    protected_head = 1
    protected_tail = min(4, len(messages) - protected_head)

    head = messages[:protected_head]
    middle = messages[protected_head:len(messages)-protected_tail]
    tail = messages[len(messages)-protected_tail:] if protected_tail > 0 else []

    if not middle:
        # Still over budget — need to summarize the tail too
        return messages[:1] + [{"role": "system", "content": "[Earlier conversation compressed for token budget]"}] + tail[-2:]

    # Summarize middle
    summary_tokens = _estimate_tokens(str(middle))
    summary = f"[Conversation history: {len(middle)} earlier turns compressed. Estimated {summary_tokens} tokens of prior context.]"

    result = head + [{"role": "system", "content": summary}] + tail

    if estimate_message_tokens(result) > max_tokens and len(tail) > 2:
        # Still over — also compress the tail
        result = head + [{"role": "system", "content": summary}] + tail[-2:]

    logger.info("Compressed %d messages to %d (budget %d tokens)",
                len(messages), len(result), max_tokens)
    return result
