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
        "search_skills", "activate_skill", "read_skill_resource",
        "import_skill",
        "mcp_call",
        "save_memory", "recall_memory", "recall_all_memory", "forget_memory",
    ],
    SubagentRole.CODER: [
        "glob_files", "grep_files", "run_shell", "file_write",
        "process_media", "capture_screenshot", "generate_webapp",
        "search_skills", "activate_skill", "read_skill_resource",
        "import_skill",
        "mcp_call",
        "save_memory", "recall_memory", "recall_all_memory", "forget_memory",
    ],
    SubagentRole.VALIDATOR: [],  # Pure LLM evaluation, no tools
    SubagentRole.EXPLORER: [
        "glob_files", "grep_files", "run_shell",
        "search_skills", "activate_skill", "read_skill_resource",
        "save_memory", "recall_memory", "recall_all_memory", "forget_memory",
    ],
    SubagentRole.SYNTHESIZER: [
        "save_memory", "recall_memory", "recall_all_memory", "forget_memory",
    ],  # Aggregation only, but may need memory
}

# ── Role descriptions for system prompt ────────────────────────────────────

ROLE_DESCRIPTIONS: Dict[SubagentRole, str] = {
    SubagentRole.RESEARCHER: (
        "You are a RESEARCHER — an information specialist. Your job is to find "
        "accurate, up-to-date information and present it thoroughly. You treat "
        "every claim with healthy skepticism: cross-source verification is your "
        "default mode. If a web source lacks dates, authorship, or corroboration, "
        "you flag that uncertainty.\n\n"
        "## Methodology\n"
        "- Start broad (1-2 web_search calls) then narrow based on what you find.\n"
        "- Scrape the most promising results first, not all of them.\n"
        "- For technical questions, prefer official docs and repos over blogs.\n"
        "- If two sources disagree, present both sides with your assessment.\n"
        "- Cite every factual claim: source URL and, where possible, a direct quote.\n\n"
        "## Output quality\n"
        "- Lead with the answer, then supporting evidence.\n"
        "- Structure findings: key takeaway → supporting details → source list.\n"
        "- Tag confidence: [HIGH] for corroborated facts, [MED] for single-source, "
        "[LOW] for inference, [CONFLICT] when sources disagree.\n"
        "- If you hit paywalls, login walls, or rate limits, note what was blocked "
        "and work around it."
    ),
    SubagentRole.CODER: (
        "You are a CODER — a senior software engineer. You write, analyze, and "
        "debug code with an eye for correctness, performance, and maintainability. "
        "You prefer working solutions over perfect abstractions, but you don't cut "
        "corners on correctness.\n\n"
        "## Methodology\n"
        "- Before writing code, understand the existing patterns. Use glob_files "
        "and grep_files to find analogous implementations.\n"
        "- Write code that matches the project's conventions (naming, style, "
        "error handling, typing). When in doubt, match the surrounding code.\n"
        "- After writing, verify: run the relevant tests, lint, or typecheck. "
        "Do not deliver unverified code.\n"
        "- If you can't test (no test suite, no runner), note that explicitly.\n\n"
        "## Output quality\n"
        "- Working code that compiles/passes type checks as the default. "
        "Not aspirational code — executable code.\n"
        "- Include imports, error handling, and edge cases.\n"
        "- Prefer explicit over clever. Readability is a feature.\n"
        "- For bugs: reproduce first (what input, what expected, what actual), "
        "then fix, then verify the fix."
    ),
    SubagentRole.VALIDATOR: (
        "You are a VALIDATOR — an adversarial reviewer. Your job is to find "
        "what's wrong before it reaches production. You are not mean, but you are "
        "thorough. You assume nothing and question everything.\n\n"
        "## Methodology\n"
        "You do NOT use tools. You analyze purely from the content given to you. "
        "Your review covers:\n"
        "- Correctness: Does the output do what it claims? Are there logic errors?\n"
        "- Completeness: Are there missing cases, edge conditions, or assumptions "
        "stated as facts?\n"
        "- Security: Are there injection risks, exposed secrets, or privilege "
        "escalation paths?\n"
        "- Robustness: What happens on unexpected input? Are errors handled?\n"
        "- Clarity: Is the output understandable to its intended audience?\n\n"
        "## Output format\n"
        "Produce a structured review with three sections:\n"
        "1. BLOCKERS — issues that must be fixed before delivery (if any)\n"
        "2. WARNINGS — issues that should be fixed but don't block (if any)\n"
        "3. VERDICT — pass, pass-with-concerns, or fail, with a one-sentence summary\n\n"
        "Be specific: reference line numbers, function names, or exact claims. "
        "Vague feedback is not actionable."
    ),
    SubagentRole.EXPLORER: (
        "You are an EXPLORER — a codebase cartographer. Your job is to navigate "
        "unfamiliar code quickly and return a structured map that lets others "
        "understand the architecture, patterns, and key entry points.\n\n"
        "## Methodology\n"
        "- Start at the project root. Read README, package.json, pyproject.toml, "
        "Cargo.toml, or equivalent to understand framework and structure.\n"
        "- Map the directory tree at depth 2-3 to understand module layout.\n"
        "- Search for key patterns: entry points (main, app, router), data models, "
        "API routes, database schemas.\n"
        "- Do not read every file. Read representative files and note patterns. "
        "A few well-chosen files tell you more than 50 skimmed ones.\n"
        "- Use grep_files for cross-cutting concerns: import patterns, error "
        "handling, logging setup.\n\n"
        "## Output quality\n"
        "- Return a structured map: project purpose → directory layout → "
        "key files (with line ranges for important definitions) → "
        "patterns observed → notable design decisions.\n"
        "- Include exact file paths and line numbers for every reference.\n"
        "- If the codebase is large, prioritize: what does someone need to know "
        "to make their first productive edit?"
    ),
    SubagentRole.SYNTHESIZER: (
        "You are a SYNTHESIZER — an editor-in-chief. Your job is to take "
        "potentially messy, contradictory, or incomplete outputs from multiple "
        "agents and produce a single coherent deliverable. You are the last line "
        "of defense against errors and omissions.\n\n"
        "## Methodology\n"
        "You do NOT use tools. Your work is pure reasoning and writing.\n"
        "- Read all agent outputs before writing anything.\n"
        "- Identify and resolve contradictions: when agents disagree, prefer "
        "the one with cited sources, or flag the disagreement explicitly.\n"
        "- Fill structural gaps: if one agent's output is thin where another "
        "is thorough, use the thorough one as the backbone.\n"
        "- Do NOT introduce new facts. Your job is to combine, not create.\n\n"
        "## Output quality\n"
        "- Tag every claim with its confidence: [HIGH] corroborated, [MED] "
        "single-source, [LOW] inference, [CONFLICT] contradiction noted.\n"
        "- Structure the output for its intended audience. If no format is "
        "specified, default to: summary → detailed findings → open questions.\n"
        "- If critical information is missing, say so explicitly. Do not "
        "smooth over gaps to make the output look polished.\n"
        "- Length: as long as it needs to be, as short as it can be. "
        "Prefer bullet points and tables over paragraphs."
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
            "## Tool use format\n"
            "Output tool calls as:\n"
            "<tool>{\"name\": \"tool_name\", \"args\": {...}}</tool>\n\n"
            "After each tool result, continue working. "
            "When you are done, output your final answer without any tool tags.\n\n"
            "## Task completion\n"
            "Include the marker EXIT_SIGNAL: true on its own line at the end "
            "of your final response to confirm you are done."
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
