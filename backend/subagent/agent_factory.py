"""Agent factory — creates typed subagents with role-appropriate tools and prompts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .types import (
    SubagentRole, SubtaskSpec, SubagentSpec,
)
from .subagent import Subagent

logger = logging.getLogger("cogent.subagent.agent_factory")

# ── Tool maps: which tools each role can use ───────────────────────────────

ROLE_TOOLS: Dict[SubagentRole, List[str]] = {
    SubagentRole.RESEARCHER: [
        "web_search", "web_scrape", "youtube_transcript",
        "github_search", "github_repo_info", "github_search_code",
        "rss_read", "v2ex_hot_topics", "v2ex_topic_detail",
        "bilibili_search",
    ],
    SubagentRole.CODER: [
        "glob_files", "grep_files", "run_shell", "file_write",
        "process_media", "capture_screenshot", "generate_webapp",
    ],
    SubagentRole.VALIDATOR: [],  # Pure LLM evaluation, no tools
    SubagentRole.EXPLORER: [
        "glob_files", "grep_files", "run_shell",
    ],
    SubagentRole.SYNTHESIZER: [],  # Aggregation only
}

# ── Role descriptions for system prompt ────────────────────────────────────

ROLE_DESCRIPTIONS: Dict[SubagentRole, str] = {
    SubagentRole.RESEARCHER: (
        "You are a RESEARCHER — an expert at gathering information from the "
        "web and other data sources. Your job is to find accurate, up-to-date "
        "information and present it clearly. Use web_search, web_scrape, and "
        "other research tools to collect data. Cite your sources."
    ),
    SubagentRole.CODER: (
        "You are a CODER — an expert software engineer. Your job is to write, "
        "analyze, and debug code. Use glob_files and grep_files to explore "
        "the codebase, run_shell to execute commands, and file_write to create "
        "or modify files. Produce working, clean, well-structured code."
    ),
    SubagentRole.VALIDATOR: (
        "You are a VALIDATOR — an expert reviewer and critic. Your job is to "
        "analyze outputs for correctness, completeness, security issues, and "
        "edge cases. You do NOT use tools. You produce structured reports with "
        "findings and recommendations."
    ),
    SubagentRole.EXPLORER: (
        "You are an EXPLORER — an expert at navigating and understanding "
        "codebases. Your job is to read code, find relevant files, and map out "
        "the structure of projects. Use glob_files and grep_files to discover "
        "and inspect code. Present your findings as structured maps."
    ),
    SubagentRole.SYNTHESIZER: (
        "You are a SYNTHESIZER — an expert at combining multiple sources of "
        "information into a coherent, well-structured output. Your job is to "
        "take the results from other agents and assemble them into the final "
        "deliverable. You do NOT use tools. Focus on clarity, completeness, "
        "and logical flow."
    ),
}


class AgentFactory:
    """Creates Subagent instances from SubtaskSpecs.

    Each subagent receives:
    - A role-specific system prompt
    - A filtered set of tools based on its role
    - An IterationBudget for token/iteration limits
    - An optional output schema
    """

    def __init__(self, provider=None, llm_call_fn=None):
        self._provider = provider
        self._llm_call_fn = llm_call_fn

    def create_agent(self, spec: SubtaskSpec) -> Subagent:
        """Create a Subagent from a SubtaskSpec."""
        tool_names = spec.tools or ROLE_TOOLS.get(spec.role, [])
        system_prompt = self._build_system_prompt(spec.role, tool_names)

        return Subagent(
            agent_id=spec.id,
            role=spec.role,
            system_prompt=system_prompt,
            task_prompt=spec.prompt,
            tool_names=tool_names,
            output_schema=spec.output_schema,
            max_iterations=spec.max_iterations,
            max_tokens=spec.max_tokens,
            timeout_seconds=spec.timeout_seconds,
            provider=self._provider,
            llm_call_fn=self._llm_call_fn,
        )

    def _build_system_prompt(self, role: SubagentRole,
                             tool_names: List[str]) -> str:
        """Build a role-specific system prompt."""
        role_desc = ROLE_DESCRIPTIONS.get(role, "You are a helpful assistant.")
        tool_block = self._format_tool_block(tool_names)

        return (
            f"{role_desc}\n\n"
            f"{tool_block}\n\n"
            "You must output tool calls as:\n"
            "<tool>{\"name\": \"tool_name\", \"args\": {...}}</tool>\n\n"
            "After each tool result, continue working. "
            "When you are done, output your final answer without any tool tags. "
            "Be thorough and specific."
        )

    def _format_tool_block(self, tool_names: List[str]) -> str:
        """Generate the available-tools section for the system prompt."""
        if not tool_names:
            return "You do not have any tools available. Provide your analysis directly."
        names_str = ", ".join(tool_names)
        return (
            f"You have access to these tools: {names_str}\n\n"
            "Tool usage format:\n"
            '<tool>{"name": "<tool_name>", "args": {...}}</tool>\n\n'
            "Each tool call goes on its own line. "
            "Wait for the result before making the next call. "
            "You can make multiple sequential calls."
        )
