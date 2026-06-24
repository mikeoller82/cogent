"""Subagent protocol types — enums, dataclasses, SSE event helpers."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SubagentRole(str, Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    VALIDATOR = "validator"
    EXPLORER = "explorer"
    SYNTHESIZER = "synthesizer"


class SubagentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubtaskSpec:
    """A single subtask from the planning decomposition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: SubagentRole = SubagentRole.RESEARCHER
    prompt: str = ""
    tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    output_schema: Optional[Dict[str, Any]] = None
    max_iterations: int = 15
    max_tokens: int = 32000
    timeout_seconds: int = 120


@dataclass
class SubagentSpec:
    """Full specification for a subagent to be spawned."""
    id: str
    role: SubagentRole
    system_prompt: str
    task_prompt: str
    tool_names: List[str]
    output_schema: Optional[Dict[str, Any]]
    max_iterations: int
    max_tokens: int
    timeout_seconds: int


@dataclass
class SubagentResult:
    """Result from a completed subagent."""
    agent_id: str
    role: SubagentRole
    status: SubagentStatus
    output: str = ""
    error: Optional[str] = None
    tool_calls_made: int = 0
    iterations_used: int = 0
    tokens_estimated: int = 0
    elapsed_seconds: float = 0.0

    @classmethod
    def success(cls, agent_id: str, role: SubagentRole, output: str,
                tool_calls: int = 0, iterations: int = 0, tokens: int = 0,
                elapsed: float = 0.0) -> SubagentResult:
        return cls(
            agent_id=agent_id, role=role, status=SubagentStatus.COMPLETED,
            output=output, tool_calls_made=tool_calls,
            iterations_used=iterations, tokens_estimated=tokens,
            elapsed_seconds=elapsed,
        )

    @classmethod
    def failure(cls, agent_id: str, role: SubagentRole, error: str,
                iterations: int = 0, tokens: int = 0, elapsed: float = 0.0) -> SubagentResult:
        return cls(
            agent_id=agent_id, role=role, status=SubagentStatus.FAILED,
            error=error, iterations_used=iterations,
            tokens_estimated=tokens, elapsed_seconds=elapsed,
        )


@dataclass
class DecompositionPlan:
    """Result of the planning pass — subtasks + reasoning."""
    subtasks: List[SubtaskSpec] = field(default_factory=list)
    reasoning: str = ""
    parallel_possible: bool = True


# ── SSE event helpers ──────────────────────────────────────────────────────


def sse_orchestrator_plan(plan: DecompositionPlan) -> dict:
    return {
        "type": "orchestrator_plan",
        "data": {
            "reasoning": plan.reasoning,
            "subtasks": [
                {
                    "id": s.id, "role": s.role.value,
                    "prompt": s.prompt[:120],
                    "dependencies": s.dependencies,
                }
                for s in plan.subtasks
            ],
        },
    }


def sse_subagent_start(spec: SubagentSpec) -> dict:
    return {
        "type": "subagent_start",
        "data": {
            "agent_id": spec.id,
            "role": spec.role.value,
            "task": spec.task_prompt[:200],
        },
    }


def sse_subagent_status(agent_id: str, role: SubagentRole, content: str) -> dict:
    return {
        "type": "subagent_status",
        "data": {"agent_id": agent_id, "role": role.value, "content": content},
    }


def sse_subagent_tool(agent_id: str, role: SubagentRole, tool_name: str, args: dict) -> dict:
    return {
        "type": "subagent_tool",
        "data": {
            "agent_id": agent_id, "role": role.value,
            "name": tool_name, "args": args,
        },
    }


def sse_subagent_tool_result(agent_id: str, role: SubagentRole,
                             tool_name: str, summary: str) -> dict:
    return {
        "type": "subagent_tool_result",
        "data": {
            "agent_id": agent_id, "role": role.value,
            "name": tool_name, "summary": summary,
        },
    }


def sse_subagent_complete(result: SubagentResult) -> dict:
    return {
        "type": "subagent_complete",
        "data": {
            "agent_id": result.agent_id,
            "role": result.role.value,
            "status": result.status.value,
            "summary": result.output[:200],
            "tool_calls": result.tool_calls_made,
            "elapsed": round(result.elapsed_seconds, 2),
        },
    }


def sse_subagent_fail(result: SubagentResult) -> dict:
    return {
        "type": "subagent_fail",
        "data": {
            "agent_id": result.agent_id,
            "role": result.role.value,
            "error": (result.error or "")[:300],
        },
    }
