"""Structured system prompt builder — ported from CowAgent's PromptBuilder pattern.

Composes the system prompt from ordered sections so each component (tools,
skills, memory, identity, runtime info) gets a consistent, well-defined block.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.prompt")


# ── Section builders ────────────────────────────────────────────────────────

def build_tools_section(tools: List[Dict[str, Any]]) -> str:
    """Render available tools as an XML block."""
    if not tools:
        return ""
    lines = ["<available_tools>"]
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "")[:200]
        lines.append(f'  <tool name="{name}">{desc}</tool>')
    lines.append("</available_tools>")
    return "\n".join(lines)


def build_memory_section(memory_facts: str) -> str:
    """Render long-term memory facts."""
    if not memory_facts:
        return ""
    return f"## Known facts about the user\n{memory_facts}"


def build_identity_section(identity: Optional[Dict[str, str]] = None) -> str:
    """Render agent identity/role description."""
    if not identity:
        return ""
    name = identity.get("name", "Agent")
    role = identity.get("role", "")
    desc = identity.get("description", "")
    parts = [f"You are {name}."]
    if role:
        parts.append(f"Your role: {role}")
    if desc:
        parts.append(desc)
    return "\n".join(parts)


def build_runtime_section(runtime: Optional[Dict[str, Any]] = None) -> str:
    """Render runtime information (current time, workspace, etc.)."""
    if not runtime:
        return ""
    lines = ["## Runtime context"]
    for key, val in runtime.items():
        lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def build_loop_state_section(loop_state) -> str:
    """Render current loop state for the system prompt block."""
    if loop_state is None:
        return ""
    from loop_engine import PHASE_IDLE
    if loop_state.phase == PHASE_IDLE:
        return ""
    budget_pct = int(
        (loop_state.tokens_estimated / loop_state.budget_max) * 100
    ) if loop_state.budget_max else 0

    lines = [
        "## Loop Engineering — Current State",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Phase | {loop_state.phase} |",
        f"| Iteration | {loop_state.iteration} |",
        f"| Task | {loop_state.task_description[:120]} |",
        f"| Budget used | ~{budget_pct}% |",
        f"| Last verification | {loop_state.verification_result or 'not yet run'} |",
    ]
    return "\n".join(lines)


# ── Main builder ────────────────────────────────────────────────────────────

def build_system_prompt(
    tools: Optional[List[Dict[str, Any]]] = None,
    memory_facts: str = "",
    identity: Optional[Dict[str, str]] = None,
    runtime: Optional[Dict[str, Any]] = None,
    loop_state=None,
    extra_instructions: str = "",
) -> str:
    """Compose the full system prompt from ordered sections.

    Order: identity → tools → memory → runtime → loop state → extra instructions
    """
    sections: List[str] = []

    # 1. Core identity
    identity_block = build_identity_section(identity)
    if identity_block:
        sections.append(identity_block)

    # 2. Available tools
    tools_block = build_tools_section(tools or [])
    if tools_block:
        sections.append(tools_block)

    # 3. Memory facts
    memory_block = build_memory_section(memory_facts)
    if memory_block:
        sections.append(memory_block)

    # 4. Runtime info
    runtime_block = build_runtime_section(runtime)
    if runtime_block:
        sections.append(runtime_block)

    # 5. Loop state
    loop_block = build_loop_state_section(loop_state)
    if loop_block:
        sections.append(loop_block)

    # 6. Extra instructions (Exit Signal Protocol, etc.)
    if extra_instructions:
        sections.append(extra_instructions)

    return "\n\n".join(sections)
