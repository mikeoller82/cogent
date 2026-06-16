"""Cogent Gateway — message delivery router for the React UI.

Simplified analog of Hermes' multi-platform gateway. Routes messages
and events exclusively to Cogent's own SSE-based frontend.
"""
from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set

logger = logging.getLogger("cogent.gateway")


class DeliveryTarget(str, Enum):
    SSE = "sse"          # Server-Sent Events to the React UI
    WEBHOOK = "webhook"  # External webhook
    LOG = "log"          # Log only (no delivery)


@dataclass
class DeliveryEvent:
    """An event to deliver to connected clients."""
    type: str  # 'message', 'status', 'tool_result', 'artifact', 'error', 'heartbeat'
    data: Dict[str, Any]
    session_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data)}\n\n"


class DeliveryRouter:
    """Routes events to registered delivery targets.

    In Cogent's case, this is primarily the SSE stream to the React frontend.
    Future: add webhook targets, log targets.
    """

    def __init__(self):
        self._sse_queues: Dict[str, asyncio.Queue] = {}  # session_id -> Queue
        self._targets: List[DeliveryTarget] = [DeliveryTarget.SSE]

    def register_sse_client(self, session_id: str) -> asyncio.Queue:
        """Register an SSE client for a session. Returns the queue they should read from."""
        if session_id not in self._sse_queues:
            self._sse_queues[session_id] = asyncio.Queue(maxsize=1000)
        return self._sse_queues[session_id]

    def unregister_sse_client(self, session_id: str) -> None:
        self._sse_queues.pop(session_id, None)

    async def deliver(self, event: DeliveryEvent) -> None:
        """Deliver an event to all registered targets for its session."""
        if DeliveryTarget.SSE in self._targets and event.session_id in self._sse_queues:
            try:
                await self._sse_queues[event.session_id].put(event)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for %s, dropping event", event.session_id)

    async def sse_generator(self, session_id: str) -> AsyncGenerator[str, None]:
        """Async generator that yields SSE events for a session."""
        queue = self.register_sse_client(session_id)
        try:
            # Send initial connection event
            yield DeliveryEvent(
                type="connected",
                data={"session_id": session_id, "status": "connected"},
                session_id=session_id,
            ).to_sse()

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield DeliveryEvent(
                        type="heartbeat",
                        data={"timestamp": datetime.now(timezone.utc).isoformat()},
                        session_id=session_id,
                    ).to_sse()
        finally:
            self.unregister_sse_client(session_id)


# Singleton router
_router: Optional[DeliveryRouter] = None


def get_router() -> DeliveryRouter:
    global _router
    if _router is None:
        _router = DeliveryRouter()
    return _router
