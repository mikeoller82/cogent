"""Full conversation compression — creates a durable summary of past sessions."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.agent.conversation_compression")


def summarize_conversation(messages: List[Dict[str, Any]], max_turns: int = 20) -> str:
    """Build a durable summary of a completed conversation.

    Returns a markdown summary suitable for storage in MEMORY.md.
    Mirrors Hermes' conversation_compression.py approach.
    """
    if not messages:
        return ""

    # Extract key exchanges
    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    tool_calls = [m for m in messages if m.get("role") == "assistant" and "tool_calls" in m]

    lines: List[str] = []
    lines.append(f"## Conversation Summary ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    lines.append(f"- Total turns: {len(messages)}")
    lines.append(f"- User messages: {len(user_messages)}")
    lines.append(f"- Assistant messages: {len(assistant_messages)}")
    lines.append(f"- Tool calls: {len(tool_calls)}")

    if len(messages) > max_turns:
        lines.append(f"- (truncated from {len(messages)} total turns)")

    # Extract last substantive exchange as key takeaway
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content.strip()) > 50:
                lines.append(f"\nLast assistant response:\n{content[:500]}")
                break

    return "\n".join(lines)
