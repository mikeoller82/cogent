"""Formal agent protocol types — Task, Action, Result dataclasses.

Ported from CowAgent's protocol layer.  Formalises what Cogent previously
tracked as loose dicts and LoopState fields.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Task types ──────────────────────────────────────────────────────────────

class TaskType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    MIXED = "mixed"


class TaskStatus(Enum):
    INIT = "init"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A unit of work for the agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    type: TaskType = TaskType.TEXT
    status: TaskStatus = TaskStatus.INIT
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    audios: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)

    def get_text(self) -> str:
        return self.content

    def update_status(self, status: TaskStatus) -> None:
        self.status = status
        self.updated_at = time.time()


# ── Agent action types ──────────────────────────────────────────────────────

class AgentActionType(Enum):
    TOOL_USE = "tool_use"
    THINKING = "thinking"
    FINAL_ANSWER = "final_answer"


@dataclass
class ToolResult:
    """Result of a single tool execution."""
    tool_name: str
    input_params: Dict[str, Any]
    output: Any
    status: str          # "success" | "error" | "critical_error"
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class AgentAction:
    """Record of one action taken by the agent."""
    agent_id: str
    agent_name: str
    action_type: AgentActionType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    tool_result: Optional[ToolResult] = None
    thought: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Final result of an agent execution."""
    final_answer: str
    step_count: int
    status: str = "success"           # "success" | "error"
    error_message: Optional[str] = None

    @classmethod
    def success(cls, final_answer: str, step_count: int) -> AgentResult:
        return cls(final_answer=final_answer, step_count=step_count)

    @classmethod
    def error(cls, error_message: str, step_count: int = 0) -> AgentResult:
        return cls(
            final_answer=f"Error: {error_message}",
            step_count=step_count,
            status="error",
            error_message=error_message,
        )

    @property
    def is_error(self) -> bool:
        return self.status == "error"
