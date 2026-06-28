"""Subagent — individual agent execution with tool loop, budget, and timeout."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

from agent import context_compressor as cc
from cogent_budget import IterationBudget

from .types import (
    SubagentRole, SubagentStatus, SubagentResult,
)

logger = logging.getLogger("cogent.subagent.subagent")

_TOOL_OPEN_RE = re.compile(r"<tool>\s*", re.DOTALL)
_TOOL_CLOSE_RE = re.compile(r"\s*</tool>", re.DOTALL)
_TOOL_TAG_RE = re.compile(r"</?tool>", re.IGNORECASE)


def _sanitize_tool_result(raw: str) -> str:
    """Strip accidental <tool> / </tool> tags from tool output."""
    return _TOOL_TAG_RE.sub("", raw)

# ── Tool dispatch table (mirrors llm_service._execute_tool) ────────────────

_TOOL_DISPATCH: Dict[str, Callable] = {}


def _register_tools() -> None:
    """Populate the tool dispatch table lazily."""
    if _TOOL_DISPATCH:
        return
    import tools as tool_impls
    import agent_reach_tools as art

    _TOOL_DISPATCH.update({
        "web_search": lambda args: tool_impls.web_search(
            args.get("query", ""), int(args.get("max_results", 5))),
        "web_scrape": lambda args: tool_impls.web_scrape(args.get("url", "")),
        "youtube_transcript": lambda args: art.youtube_transcript(args.get("url", "")),
        "github_repo_info": lambda args: art.github_repo_info(args.get("repo", "")),
        "github_search": lambda args: art.github_search(
            args.get("query", ""), int(args.get("limit", 5))),
        "github_search_code": lambda args: art.github_search_code(
            args.get("query", ""), int(args.get("limit", 5))),
        "rss_read": lambda args: art.rss_read(
            args.get("url", ""), int(args.get("limit", 10))),
        "v2ex_hot_topics": lambda args: art.v2ex_hot_topics(
            int(args.get("limit", 20))),
        "v2ex_topic_detail": lambda args: art.v2ex_topic_detail(
            int(args.get("topic_id", 0))),
        "bilibili_search": lambda args: art.bilibili_search(
            args.get("query", ""), int(args.get("limit", 5))),
        "run_shell": lambda args: tool_impls.run_shell(
            args.get("command", ""), int(args.get("timeout", 30))),
        "process_media": lambda args: tool_impls.process_media(
            args.get("action", "info"), args.get("input", ""),
            output=args.get("output", ""),
            start=args.get("start", ""),
            duration=args.get("duration", ""),
            format=args.get("format", ""),
            quality=int(args.get("quality", 80)),
        ),
        "capture_screenshot": lambda args: tool_impls.capture_screenshot(
            output=args.get("output", ""),
            delay=int(args.get("delay", 1)),
        ),
        "file_write": lambda args: tool_impls.file_write(
            args.get("path", ""), args.get("content", ""),
            mode=args.get("mode", "w"),
        ),
        "glob_files": lambda args: tool_impls.glob_files(
            args.get("pattern", ""), path=args.get("path", "")),
        "grep_files": lambda args: tool_impls.grep_files(
            args.get("pattern", ""),
            include=args.get("include", ""),
            path=args.get("path", ""),
            output_mode=args.get("output_mode", "files_with_matches"),
            case_insensitive=bool(args.get("-i", False)),
        ),
    })


def _parse_tool_call(text: str) -> tuple:
    """Find the first complete JSON object inside <tool>...</tool> tags.

    Uses json.JSONDecoder.raw_decode() which properly handles arbitrary
    brace nesting — unlike a non-greedy regex ``{.*?}`` that truncates
    on the first ``}`` inside argument values.
    """
    m = _TOOL_OPEN_RE.search(text)
    if not m:
        return None, text
    start = m.end()
    try:
        decoder = json.JSONDecoder()
        parsed, idx = decoder.raw_decode(text, start)
    except (json.JSONDecodeError, ValueError, IndexError):
        return None, text
    close_m = _TOOL_CLOSE_RE.match(text, idx)
    if not close_m:
        return None, text
    before = text[:m.start()].strip()
    return parsed, before


async def _execute_tool_call(name: str, args: dict) -> dict:
    _register_tools()
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        return {"result": f"Unknown tool: {name}"}
    try:
        result = handler(args)
        if asyncio.iscoroutine(result):
            result = await result
        return result
    except Exception as exc:
        logger.warning("Subagent tool %s error: %s", name, exc)
        return {"result": f"Tool '{name}' failed: {type(exc).__name__}: {exc}"}


class Subagent:
    """A single subagent that executes its task via LLM + tool calls.

    Each subagent has its own identity, system prompt, tool set, iteration
    budget, and timeout. It runs an autonomous loop: think → tool call →
    process result → repeat until done or budget exhausted.
    """

    def __init__(
        self,
        agent_id: str,
        role: SubagentRole,
        system_prompt: str,
        task_prompt: str,
        tool_names: List[str],
        output_schema: Optional[Dict[str, Any]] = None,
        max_iterations: int = 30,
        max_tokens: int = 64000,
        timeout_seconds: int = 300,
        provider=None,
        llm_call_fn=None,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.task_prompt = task_prompt
        self.tool_names = list(tool_names)
        self.output_schema = output_schema
        self.budget = IterationBudget(
            max_iterations=max_iterations,
            max_tokens=max_tokens,
        )
        self.timeout_seconds = timeout_seconds
        self._provider = provider
        self._llm_call_fn = llm_call_fn

        self.tool_calls_made: int = 0

    def to_spec(self) -> "SubagentSpec":
        """Return a SubagentSpec for SSE event generation."""
        from .types import SubagentSpec
        return SubagentSpec(
            id=self.agent_id,
            role=self.role,
            system_prompt=self.system_prompt,
            task_prompt=self.task_prompt,
            tool_names=self.tool_names,
            output_schema=self.output_schema,
            max_iterations=self.budget.max_iterations,
            max_tokens=self.budget.max_tokens,
            timeout_seconds=self.timeout_seconds,
        )

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Send messages to the LLM and return the response text."""
        if self._llm_call_fn is not None:
            return await self._llm_call_fn(messages)
        from cogent_providers import get_provider
        vp = get_provider()
        content = await vp.chat(messages)
        if content is None:
            raise RuntimeError("Provider returned None content")
        return content

    async def execute(
        self,
        status_callback: Optional[Callable[[str, SubagentRole, str, Optional[dict]], None]] = None,
    ) -> SubagentResult:
        """Run the subagent: autonomous LLM with tool calls.

        Args:
            status_callback: Optional callback (agent_id, role, message, event_data) for
                streaming status, tool, and tool_result events. event_data is a dict
                with extra fields like tool name, args, or summary.

        Returns:
            SubagentResult with the agent's output or error.
        """
        start_time = time.time()
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.task_prompt},
        ]

        def _status(msg: str, event_data: Optional[dict] = None) -> None:
            if status_callback:
                status_callback(self.agent_id, self.role, msg, event_data)

        def _extract_partial_output() -> str:
            """Extract the last substantive LLM response (not a tool call) as partial output."""
            for msg in reversed(messages):
                if msg["role"] == "assistant" and "<tool>" not in msg["content"]:
                    return msg["content"]
            return ""

        _status("starting")

        try:
            async with asyncio.timeout(self.timeout_seconds):
                while not self.budget.exhausted:
                    # ── Call LLM ────────────────────────────────────────
                    response = await self._call_llm(messages)
                    # Better token estimation using context_compressor
                    self.budget.record_tokens(cc.estimate_message_tokens([{"role": "assistant", "content": response}]))

                    # ── Budget warning at 75% ──────────────────────────
                    if self.budget.warn_pct >= 0.75 and self.budget.warn_pct < 0.80:
                        remaining = self.budget.iterations_remaining
                        _status(f"warning: {remaining} iterations remaining — finishing soon")

                    # ── Parse tool calls ───────────────────────────────
                    tool_call, reasoning = _parse_tool_call(response)
                    if tool_call is None:
                        _status("finalizing")
                        return SubagentResult.success(
                            agent_id=self.agent_id,
                            role=self.role,
                            output=response,
                            tool_calls=self.tool_calls_made,
                            iterations=self.budget.iterations_used,
                            tokens=self.budget.tokens_used,
                            elapsed=time.time() - start_time,
                        )

                    name = tool_call.get("name", "?")
                    args = tool_call.get("args", {})
                    _status(f"running {name}", {"tool": name, "args": args})

                    # ── Execute tool ────────────────────────────────────
                    tool_result = await _execute_tool_call(name, args)
                    self.tool_calls_made += 1

                    # ── Emit tool result event ──────────────────────────
                    result_text = tool_result.get("result", "")
                    summary = result_text[:300] if result_text else "(no output)"
                    _status(f"{name} complete", {"tool": name, "summary": summary})

                    # ── Feed result back ───────────────────────────────
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": f"<tool_result>\n{_sanitize_tool_result(result_text)}\n</tool_result>",
                    })

                    if not self.budget.consume():
                        partial = _extract_partial_output()
                        _status("budget exhausted — returning partial results")
                        return SubagentResult.failure(
                            agent_id=self.agent_id,
                            role=self.role,
                            error="Budget exhausted — partial results may be available",
                            output=partial,
                            tool_calls=self.tool_calls_made,
                            iterations=self.budget.iterations_used,
                            tokens=self.budget.tokens_used,
                            elapsed=time.time() - start_time,
                        )

        except asyncio.TimeoutError:
            logger.warning("Subagent %s timed out after %ss",
                           self.agent_id, self.timeout_seconds)
            partial = _extract_partial_output()
            return SubagentResult.failure(
                agent_id=self.agent_id, role=self.role,
                error=f"Timed out after {self.timeout_seconds}s",
                output=partial,
                iterations=self.budget.iterations_used,
                tokens=self.budget.tokens_used,
                elapsed=time.time() - start_time,
            )
        except Exception as exc:
            logger.exception("Subagent %s failed", self.agent_id)
            partial = _extract_partial_output()
            return SubagentResult.failure(
                agent_id=self.agent_id, role=self.role,
                error=f"{type(exc).__name__}: {exc}",
                output=partial,
                iterations=self.budget.iterations_used,
                tokens=self.budget.tokens_used,
                elapsed=time.time() - start_time,
            )
