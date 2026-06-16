"""Per-turn context — captures state for a single LLM interaction turn."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TurnContext:
    """Holds all state for one LLM turn: messages, tools used, token counts, timing."""
    session_id: str
    turn_number: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    started_at: float = 0.0
    elapsed: float = 0.0
    error: Optional[str] = None

    def start_timer(self) -> None:
        self.started_at = time.time()

    def stop_timer(self) -> None:
        self.elapsed = time.time() - self.started_at

    def snapshot(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "tool_calls": len(self.tool_calls),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "elapsed": round(self.elapsed, 3),
            "error": self.error,
        }
