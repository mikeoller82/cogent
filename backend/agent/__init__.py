"""Cogent agent subsystem — turn context, compression, and bootstrap."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .turn_context import TurnContext
    from .context_compressor import compress_messages as ContextCompressor
    from .conversation_compression import summarize_conversation as ConversationCompression
    from .agent_init import bootstrap_agent


def __getattr__(name: str):
    if name == "TurnContext":
        from .turn_context import TurnContext
        return TurnContext
    if name == "ContextCompressor":
        from .context_compressor import compress_messages
        return compress_messages
    if name == "ConversationCompression":
        from .conversation_compression import summarize_conversation
        return summarize_conversation
    if name == "bootstrap_agent":
        from .agent_init import bootstrap_agent
        return bootstrap_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TurnContext", "ContextCompressor", "ConversationCompression", "bootstrap_agent"]
