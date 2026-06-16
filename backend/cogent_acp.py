"""Cogent ACP — Agent Communication Protocol adapter.

Minimal implementation of the ACP specification for agents to communicate
with other agents. Mirrors Hermes' acp_adapter/ structure.
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("cogent.acp")


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ACPMessage:
    """A single message in the ACP protocol."""
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ACPRequest:
    """An ACP request — the full message thread + configuration."""
    messages: List[ACPMessage]
    model: str = "default"
    max_tokens: int = 4096
    temperature: float = 0.7
    tools: List[Dict[str, Any]] = field(default_factory=list)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in self.messages
            ],
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "tools": self.tools,
            "session_id": self.session_id,
        }


@dataclass
class ACPResponse:
    """An ACP response."""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    error: Optional[str] = None


async def handle_acp_request(request: ACPRequest) -> ACPResponse:
    """Handle an ACP request by routing to Cogent's LLM service.

    This is the main entry point for ACP communication. For now, it
    validates the request and returns a basic response; full integration
    with llm_service.run_turn comes in a future version.
    """
    if not request.messages:
        return ACPResponse(content="", error="No messages in request")

    logger.info("ACP request: %d messages, %d tools",
                len(request.messages), len(request.tools))

    # Basic echo for now — full LLM routing will replace this
    last_msg = request.messages[-1]
    return ACPResponse(
        content=f"[ACP] Received: {len(request.messages)} messages. Last role: {last_msg.role.value}",
        usage={"input_tokens": 0, "output_tokens": 0},
    )


def acp_request_from_dict(data: Dict[str, Any]) -> ACPRequest:
    """Parse an ACP request from a JSON/dict."""
    messages = []
    for m in data.get("messages", []):
        messages.append(ACPMessage(
            role=MessageRole(m.get("role", "user")),
            content=m.get("content", ""),
            tool_calls=m.get("tool_calls"),
            tool_call_id=m.get("tool_call_id"),
        ))
    return ACPRequest(
        messages=messages,
        model=data.get("model", "default"),
        max_tokens=data.get("max_tokens", 4096),
        temperature=data.get("temperature", 0.7),
        tools=data.get("tools", []),
        session_id=data.get("session_id"),
    )
