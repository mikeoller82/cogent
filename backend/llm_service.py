"""Tool-using LLM loop for Cogent the AI coworker.
Exposes both a one-shot run_turn and an async-generator run_turn_stream that
yields progress events: status, tool, tool_result, artifact, final.
"""
import os
import re
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator

import requests
from dotenv import load_dotenv

import agent_skills
import tools as tool_impls
import agent_reach_tools as art
import cogent_prompt
import cogent_commands
from agent import context_compressor as cc
import loop_engine as le

from cogent_config import get_config
from cogent_logging import set_session_context
from cogent_memory import memory_summary
from cogent_providers import get_provider

load_dotenv()
_cfg = get_config()
KILOCODE_MODEL_NAME = _cfg.model_name
KILOCODE_CHAT_COMPLETIONS_URL = _cfg.model_base_url

logger = logging.getLogger("cogent.llm_service")

# Message compression threshold: auto-compress when messages exceed this count
COMPRESS_AFTER_TURNS = 30  # compress messages after this many exchange turns
MAX_TOOL_TURNS = _cfg.max_turns

def build_system_prompt(workspace_name: str = "your team", memory_facts: str = "",
                        loop_state=None) -> str:
    """Assemble the system prompt from SOUL.md + tools + skills + commands + loop state."""
    soul_path = Path(__file__).parent.parent / "SOUL.md"
    soul_content = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""

    loop_block = le.build_loop_system_block(loop_state)
    tools_block = tool_impls.tool_specs_for_prompt()
    skills_block = agent_skills.skill_catalog_for_prompt()
    commands_block = cogent_commands.command_catalog_for_prompt()

    return cogent_prompt.build_system_prompt(
        soul_content=soul_content,
        memory_facts=memory_facts,
        tools_specs=tools_block,
        skills_catalog=skills_block,
        commands_catalog=commands_block,
        loop_block=loop_block,
    )



def _tool_action_label(name: str, args: dict) -> str:
    """Generate a human-readable label for what a tool is doing."""
    if name == "web_search":
        q = (args.get("query") or "").strip()
        return f'searching web for "{q}"' if q else "searching the web"
    elif name == "web_scrape":
        url = (args.get("url") or "").strip()
        return f"reading {url}" if url else "reading a webpage"
    elif name == "search_skills":
        q = (args.get("query") or "").strip()
        return f'searching skills for "{q}"' if q else "searching skills"
    elif name == "search_skills":
        return "skill search complete"
    elif name == "activate_skill":
        skill = (args.get("name") or "").strip()
        return f'skill "{skill}" ready' if skill else "skill activated"
    elif name == "read_skill_resource":
        path = (args.get("path") or "").strip()
        return f"reading {path} from skill" if path else "reading skill resource"
    elif name == "generate_pdf":
        title = (args.get("title") or "").strip()
        return f'generating PDF: "{title}"' if title else "generating PDF"
    elif name == "generate_webapp":
        title = (args.get("title") or "").strip()
        return f'building web app: "{title}"' if title else "building web app"
    elif name == "save_memory":
        key = (args.get("key") or "").strip()
        return f"saving: {key}" if key else "saving to memory"
    elif name == "schedule_task":
        task_name = (args.get("name") or "").strip()
        return f'scheduling: "{task_name}"' if task_name else "scheduling a task"
    elif name == "import_skill":
        repo = (args.get("repo_url") or "").strip()
        return f"importing skills from {repo}" if repo else "importing skills"
    elif name == "youtube_transcript":
        url = (args.get("url") or "").strip()
        return f"fetching transcript from {url}" if url else "fetching YouTube transcript"
    elif name == "github_repo_info":
        repo = (args.get("repo") or "").strip()
        return f"looking up repo: {repo}" if repo else "looking up GitHub repo"
    elif name == "github_search":
        q = (args.get("query") or "").strip()
        return f'searching GitHub for "{q}"' if q else "searching GitHub"
    elif name == "rss_read":
        url = (args.get("url") or "").strip()
        return f"reading feed from {url}" if url else "reading RSS feed"
    elif name == "v2ex_hot_topics":
        return "fetching V2EX hot topics"
    elif name == "bilibili_search":
        q = (args.get("query") or "").strip()
        return f'searching Bilibili for "{q}"' if q else "searching Bilibili"
    elif name == "get_loop_state":
        return "checking loop state"
    elif name == "glob_files":
        pat = (args.get("pattern") or "").strip()
        return f'searching files with pattern "{pat}"' if pat else "searching files"
    elif name == "grep_files":
        pat = (args.get("pattern") or "").strip()
        return f'searching contents for "{pat}"' if pat else "searching file contents"
    elif name == "plugin_install":
        pn = (args.get("plugin_name") or "").strip()
        return f'installing plugin "{pn}"' if pn else "installing plugin"
    elif name == "plugin_list":
        return "listing installed plugins"
    elif name == "plugin_describe":
        pn = (args.get("name") or "").strip()
        return f'describing plugin "{pn}"' if pn else "describing plugin"
    elif name == "run_command":
        cmd = (args.get("command") or "").strip()
        return f'running command "{cmd}"' if cmd else "running command"
    return name.replace("_", " ")


def _tool_display_summary(name: str, args: dict, raw_summary: str) -> str:
    """Generate a one-line summary of what a tool returned, for the frontend status bar."""
    if name == "web_search":
        q = (args.get("query") or "").strip()
        count = raw_summary.count("\n[") + (1 if raw_summary.startswith("[") else 0)
        return f'found {count} results for "{q}"' if count else "search completed"
    elif name == "web_scrape":
        return "page content extracted"
    elif name == "activate_skill":
        skill = (args.get("name") or "").strip()
        return f'skill "{skill}" ready' if skill else "skill activated"
    elif name == "generate_pdf":
        return "PDF generated"
    elif name == "generate_webapp":
        return "web app deployed"
    elif name == "save_memory":
        return "saved"
    elif name == "schedule_task":
        return "task scheduled"
    elif name == "import_skill":
        return "skills imported"
    elif name == "youtube_transcript":
        return "transcript fetched"
    elif name == "github_repo_info":
        return "repo info retrieved"
    elif name == "github_search":
        q = (args.get("query") or "").strip()
        return f'GitHub results for "{q}"' if q else "GitHub search done"
    elif name in ("rss_read", "v2ex_hot_topics", "bilibili_search"):
        return "results retrieved"
    elif name == "glob_files":
        return "file search complete"
    elif name == "grep_files":
        return "content search complete"
    elif name == "plugin_install":
        return "plugin installed"
    elif name == "plugin_list":
        return "plugins listed"
    elif name == "plugin_describe":
        return "plugin info retrieved"
    elif name == "run_command":
        return "command executed"
    return f"{name.replace('_', ' ')} complete"


def _build_synthesis_prompt(
    user_text: str,
    research_findings: list[str],
    reason: str = "",
) -> str:
    """Build synthesis prompt that grounds the LLM in research data."""
    parts = []
    if research_findings:
        parts.append(
            "=== RESEARCH DATA (ground truth — base your answer on this) ===\n"
            + "\n\n".join(research_findings)
            + "\n=== END RESEARCH DATA ==="
        )
    instruction = (
        "IMPORTANT: Your answer MUST be grounded in the research data above. "
        "Do NOT rely on your training data or prior knowledge for facts, figures, "
        "or claims. The research data is the ground truth for this task. "
        "If the research data is insufficient to fully answer, say so clearly.\n\n"
        "No more tool calls — write your complete answer.\n"
        "When done, include EXIT_SIGNAL: true at the end."
    )
    if reason:
        parts.append(f"Note: {reason}")
    parts.append(instruction)
    parts.append(f"Original task: {user_text}")
    return "\n\n".join(parts)


def _looks_like_plan(text: str) -> bool:
    """Detect if LLM response describes a plan/promise without executing it.
    Only triggers on explicit future-tense promises using tools.
    Safe: short final answers, status updates, simple confirmations.
    """
    plan_phrases = [
        "i will", "i'll", "i'm going to", "let me",
        "my plan is", "the plan is", "here is my plan", "here's my plan",
        "first, i'll", "first i'll",
    ]
    lower = text.lower().strip()
    # Must be reasonably short (plans are brief, deliverables are long)
    # AND contain explicit plan language
    if len(text) < 200 and any(p in lower for p in plan_phrases):
        return True
    return False
TOOL_RE = re.compile(r"<tool>\s*(\{.*?\})\s*</tool>", re.DOTALL)


def _parse_tool_call(text: str):
    m = TOOL_RE.search(text)
    if not m:
        return None, text
    raw = m.group(1)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, text
    before = text[: m.start()].strip()
    return parsed, before

async def _call_llm(messages: List[Dict[str, str]], **kwargs) -> str:
    """Send a chat-completion request via the VirtualProvider fallback chain (async).

    Returns the response text.  Raises RuntimeError when all providers
    are exhausted or a non-retryable error occurs.
    """
    vp = get_provider()
    content = await vp.chat(messages, **kwargs)
    if content is None:
        raise RuntimeError("Provider returned None content")
    return content


async def _send_kilocode_chat(messages: List[Dict[str, str]]) -> str:
    return await _call_llm(messages)


def _collect_provider_events() -> List[str]:
    """Return and clear any provider-fallback events since last check."""
    vp = get_provider()
    return vp.drain_fallback_events()


# backward-compatible alias for existing callers
# backward-compatible sync wrapper for existing tests / callers
def _post_kilocode_chat(messages: List[Dict[str, str]], **kwargs) -> str:
    """Synchronous wrapper around ``_send_kilocode_chat``."""
    return asyncio.run(_send_kilocode_chat(messages))

async def _execute_tool(db, workspace_id: str, call: dict) -> dict:
    name = call.get("name")
    args = call.get("args") or {}
    try:
        if name == "web_search":
            return await tool_impls.web_search(args.get("query", ""), int(args.get("max_results", 5)))
        if name == "web_scrape":
            return await tool_impls.web_scrape(args.get("url", ""))
        if name == "generate_pdf":
            return await tool_impls.generate_pdf(
                args.get("title", "Untitled"),
                args.get("sections") or [],
                subtitle=args.get("subtitle", ""),
                accent=args.get("accent", "purple"),
            )
        if name == "generate_webapp":
            return await tool_impls.generate_webapp(args.get("title", "App"), args.get("html", ""))
        if name == "save_memory":
            return await tool_impls.save_memory(db, workspace_id, args.get("key", ""), args.get("value", ""))
        if name == "recall_memory":
            return await tool_impls.recall_memory(db, workspace_id)
        if name == "schedule_task":
            return await tool_impls.schedule_task(
                db, workspace_id,
                args.get("name", "task"),
                args.get("cadence", "weekly"),
                args.get("time", "09:00"),
                args.get("prompt", ""),
            )
        if name == "search_skills":
            return await tool_impls.search_skills(
                args.get("query", ""),
                int(args.get("max_results", 10)),
            )
        if name == "activate_skill":
            return await tool_impls.activate_skill(args.get("name", ""))
        if name == "read_skill_resource":
            return await tool_impls.read_skill_resource(args.get("skill_name", ""), args.get("path", ""))
        if name == "import_skill":
            return await tool_impls.import_skill(
                args.get("repo_url", ""),
                force=bool(args.get("force", False)),
            )
        if name == "agent_reach_doctor":
            return await art.agent_reach_doctor()
        if name == "youtube_transcript":
            return await art.youtube_transcript(args.get("url", ""))
        if name == "github_repo_info":
            return await art.github_repo_info(args.get("repo", ""))
        if name == "github_search":
            return await art.github_search(args.get("query", ""), int(args.get("limit", 5)))
        if name == "github_search_code":
            return await art.github_search_code(args.get("query", ""), int(args.get("limit", 5)))
        if name == "v2ex_hot_topics":
            return await art.v2ex_hot_topics(int(args.get("limit", 20)))
        if name == "v2ex_topic_detail":
            return await art.v2ex_topic_detail(int(args.get("topic_id", 0)))
        if name == "rss_read":
            return await art.rss_read(args.get("url", ""), int(args.get("limit", 10)))
        if name == "bilibili_search":
            return await art.bilibili_search(args.get("query", ""), int(args.get("limit", 5)))
        if name == "run_shell":
            return await tool_impls.run_shell(args.get("command", ""), int(args.get("timeout", 30)))
        if name == "process_media":
            return await tool_impls.process_media(
                args.get("action", "info"),
                args.get("input", ""),
                output=args.get("output", ""),
                start=args.get("start", ""),
                duration=args.get("duration", ""),
                format=args.get("format", ""),
                quality=int(args.get("quality", 80)),
            )
        if name == "capture_screenshot":
            return await tool_impls.capture_screenshot(
                output=args.get("output", ""),
                delay=int(args.get("delay", 1)),
            )
        if name == "file_write":
            return await tool_impls.file_write(
                args.get("path", ""),
                args.get("content", ""),
                mode=args.get("mode", "w"),
            )
        if name == "glob_files":
            return await tool_impls.glob_files(
                args.get("pattern", ""),
                path=args.get("path", ""),
            )
        if name == "grep_files":
            return await tool_impls.grep_files(
                args.get("pattern", ""),
                include=args.get("include", ""),
                path=args.get("path", ""),
                output_mode=args.get("output_mode", "files_with_matches"),
                case_insensitive=bool(args.get("-i", False)),
            )
        if name == "plugin_install":
            return await tool_impls.plugin_install(
                args.get("repo_url", ""),
                args.get("plugin_name", ""),
            )
        if name == "plugin_list":
            return await tool_impls.plugin_list()
        if name == "plugin_describe":
            return await tool_impls.plugin_describe(args.get("name", ""))
        if name == "run_command":
            return await tool_impls.run_command(args.get("command", ""))
        return {"result": f"Unknown tool: {name}"}
    except (ValueError, TypeError, KeyError) as e:
        # Validation / bad-args errors — tell the LLM clearly so it can fix the call
        logger.warning("Tool %s validation error: %s", name, e)
        return {"result": f"Tool '{name}' received invalid arguments: {e}"}
    except (requests.ConnectionError, requests.Timeout, OSError) as e:
        # Network / resource errors — may be transient
        logger.warning("Tool %s network error: %s", name, e)
        return {"result": f"Tool '{name}' failed with network error: {e}"}
    except asyncio.TimeoutError as e:
        logger.warning("Tool %s timed out: %s", name, e)
        return {"result": f"Tool '{name}' timed out. The operation may still be running."}
    except Exception as e:
        # Unexpected errors — log full traceback for debugging
        logger.exception("Tool %s unexpected error", name)
        return {"result": f"Tool '{name}' failed: {type(e).__name__}: {e}"}


async def _load_memory_facts(db, workspace_id: str) -> str:
    """Load memory facts from both DB and file-based stores."""
    parts = []

    # DB memory (MongoDB)
    cursor = db.memories.find({"workspace_id": workspace_id}, {"_id": 0, "key": 1, "value": 1})
    items = await cursor.to_list(length=100)
    if items:
        parts.append("# Database Memory")
        parts.extend(f"- {m['key']}: {m['value']}" for m in items)

    # File-based memory (MEMORY.md + USER.md)
    file_memory = memory_summary()
    if file_memory:
        parts.append(file_memory)

    return "\n".join(parts)


async def run_turn(db, session_id: str, workspace_id: str, user_text: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
    """One-shot non-streaming run. Returns final result dict."""
    tool_uses = []
    artifacts = []
    final_text = ""

    async for event in run_turn_stream(db, session_id, workspace_id, user_text, history):
        et = event.get("type")
        if et == "tool":
            tool_uses.append(event["data"])
        elif et == "artifact":
            artifacts.append(event["data"])
        elif et == "final":
            final_text = event["content"]

    return {"text": final_text, "tool_uses": tool_uses, "artifacts": artifacts}


async def run_turn_stream(db, session_id: str, workspace_id: str, user_text: str, history: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming run wrapped in a Plan→Execute→Verify loop.

    Yields events: status, tool, tool_result, artifact, final, error, loop, reasoning.
    - reasoning: raw LLM response text for display in thinking log
    - auto-continue: when LLM plans without executing or tool turns exhausted,
      automatically re-prompts to keep working (up to CONTINUE_MAX times)
    """
    set_session_context(session_id)
    # ── Load loop state ──────────────────────────────────────────────
    loop_state = le.load_state(session_id)
    is_new_task = loop_state.phase in (le.PHASE_IDLE, le.PHASE_DONE, le.PHASE_ERROR)
    if is_new_task:
        le.begin_task(loop_state, user_text)
    else:
        loop_state.task_description = user_text or loop_state.task_description
        le.save_state(loop_state)

    yield {"type": "loop", "data": {"phase": loop_state.phase, "iteration": loop_state.iteration}}

    memory_facts = await _load_memory_facts(db, workspace_id)
    system_prompt = build_system_prompt(memory_facts=memory_facts, loop_state=loop_state)
    initial_messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        initial_messages.append({"role": h["role"], "content": h["content"]})

    current_user_text = user_text
    final_text = ""
    tool_loop_error = False
    research_findings: list[str] = []

    # ── Main refinement loop ─────────────────────────────────────────
    while loop_state.iteration < le.MAX_ITERATIONS:
        if loop_state.budget_exhausted:
            yield {"type": "loop", "data": {"phase": le.PHASE_ERROR, "message": "Budget exhausted"}}
            final_text = "(stopped — token budget exceeded)"
            yield {"type": "final", "content": final_text}
            le.fail_task(loop_state, "Budget exhausted")
            break

        le.transition(loop_state, le.PHASE_EXECUTE, "Starting execution turn")
        yield {"type": "loop", "data": {"phase": le.PHASE_EXECUTE, "iteration": loop_state.iteration}}
        yield {"type": "status", "content": "analyzing request and planning approach"}
        
        # ── Tool-calling loop ────────────────────────────────────────
        tool_loop_error = False
        made_tool_calls = False
        max_turns = MAX_TOOL_TURNS
        sub_phase = "gather"       # "gather" | "synthesize"
        gather_turns = 0
        synthesize_turns = 0
        web_search_budget_msg = (
            "Search budget exceeded (%d web_search + %d web_scrape calls allowed per task). "
            "Use the results you already have or rely on what you know."
        )
        for turn in range(max_turns):
            messages = initial_messages.copy()
            messages.append({"role": "user", "content": current_user_text})
            try:
                response_text = await _send_kilocode_chat(messages)

                # Emit any provider-fallback events since the last call
                for ev in _collect_provider_events():
                    yield {"type": "provider", "content": ev}
            except Exception as e:
                error_msg = str(e).lower()
                is_overflow = any(kw in error_msg for kw in [
                    "context length", "maximum context", "prompt is too long",
                    "context overflow", "too large", "tokens exceed", "request_too_large",
                ])

                if is_overflow and turn > 0:
                    # Trim context and retry once
                    yield {"type": "reasoning", "content": "[context overflow — trimming and retrying]"}
                    yield {"type": "status", "content": "context overflow detected, trimming messages"}
                    # Keep system + last 2 exchanges
                    trimmed = initial_messages[:1]
                    if len(initial_messages) > 3:
                        trimmed += initial_messages[-2:]
                    initial_messages = trimmed
                    try:
                        response_text = await _send_kilocode_chat(initial_messages + [
                            {"role": "user", "content": current_user_text},
                        ])
                        yield {"type": "reasoning", "content": response_text}
                    except Exception as e2:
                        yield {"type": "error", "content": f"LLM error after overflow retry: {e2}"}
                        final_text = f"(LLM error after overflow: {e2})"
                        le.fail_task(loop_state, f"LLM error: {e2}")
                        tool_loop_error = True
                        break
                else:
                    yield {"type": "error", "content": f"LLM error: {e}"}
                    final_text = f"(LLM error: {e})"
                    le.fail_task(loop_state, f"LLM error: {e}")
                    tool_loop_error = True
                    break

            # ── Emit reasoning event with raw LLM output ─────────────
            yield {"type": "reasoning", "content": response_text}

            initial_messages.append({"role": "user", "content": current_user_text})
            initial_messages.append({"role": "assistant", "content": response_text})

            # ── Auto-compress if messages exceed threshold ───────────
            if len(initial_messages) > COMPRESS_AFTER_TURNS:
                compressed = cc.compress_messages(initial_messages, max_tokens=64000)
                if len(compressed) < len(initial_messages):
                    yield {"type": "reasoning", "content": (
                        f"[compressed: {len(initial_messages)} -> {len(compressed)} messages]"
                    )}
                    initial_messages = compressed

            call, _ = _parse_tool_call(response_text)

            # ── Phase-aware response dispatch ─────────────────────────
            # GATHER: tools execute, text flows freely, no re-prompts.
            # SYNTHESIZE: tool calls blocked, text captured as output.

            if sub_phase == "gather":
                gather_turns += 1

                if not call:
                    # Check for ready signal → advance to synthesis
                    if le.parse_ready_signal(response_text):
                        yield {"type": "reasoning", "content": (
                            "[gather complete — advancing to synthesis phase]"
                        )}
                        yield {"type": "status", "content": "gathering complete, now synthesizing answer"}
                        sub_phase = "synthesize"
                        current_user_text = _build_synthesis_prompt(
                            user_text, research_findings,
                            reason="You have gathered all the data you need.",
                        )
                        continue

                    # Check gather turn limit → auto-advance to synthesis
                    if gather_turns >= le.GATHER_MAX_TURNS:
                        yield {"type": "reasoning", "content": (
                            f"[gather turn limit {gather_turns}/{le.GATHER_MAX_TURNS}"
                            " — advancing to synthesis]"
                        )}
                        yield {"type": "status", "content": "gather phase complete, synthesizing answer"}
                        sub_phase = "synthesize"
                        current_user_text = _build_synthesis_prompt(
                            user_text, research_findings,
                            reason="Gather phase reached its turn limit. Synthesize from what you have.",
                        )
                        continue

                    # Free text in gather — yield as reasoning, no re-prompt
                    current_user_text = (
                        "Continue gathering data using the available tools "
                        "(search, scrape, read, etc.). "
                        "Signal READY_FOR_EVALUATION: true when you have "
                        "enough data to answer.\n\n"
                        f"Original task: {user_text}"
                    )
                    continue

                # Tool call in gather — falls through to execution below

            elif sub_phase == "synthesize":
                synthesize_turns += 1

                if call:
                    # Hard block — no tool calls in synthesis phase
                    yield {"type": "reasoning", "content": (
                        "[tool call blocked — synthesis phase, no tools allowed]"
                    )}
                    current_user_text = _build_synthesis_prompt(
                        user_text, research_findings,
                        reason="No tool calls are allowed in synthesis phase.",
                    )
                    continue

                # Text response in synthesis — check completion
                ralph_status = le.parse_ralph_status_block(response_text)
                if ralph_status.get("exit_signal"):
                    yield {"type": "reasoning", "content": (
                        "[LLM signaled completion — processing final answer]"
                    )}
                    final_text = response_text.strip()
                    loop_state.consecutive_no_tool_responses = 0
                    le.save_state(loop_state)
                    break

                # Accept text as output (may refine in subsequent turns)
                final_text = response_text.strip()
                yield {"type": "reasoning", "content": (
                    f"[synthesis output ({synthesize_turns}/{le.SYNTHESIZE_MAX_TURNS})]"
                )}

                if synthesize_turns >= le.SYNTHESIZE_MAX_TURNS:
                    yield {"type": "reasoning", "content": (
                        "[synthesis turn limit — accepting final output]"
                    )}
                    break

                current_user_text = _build_synthesis_prompt(
                    user_text, research_findings,
                    reason="Refine your answer or signal completion.",
                )
                continue

            # ── Tool execution (gather phase with a real tool call) ────

            made_tool_calls = True
            tool_name = call.get("name", "")
            args = call.get("args", {})
            if loop_state.consecutive_no_tool_responses > 0:
                loop_state.consecutive_no_tool_responses = 0
                le.save_state(loop_state)

            # ── CowAgent-style loop detection ──────────────────
            should_stop, stop_reason, is_critical = le.check_tool_loop(loop_state, tool_name, args)
            if should_stop:
                loop_state.tool_loop_detected_stop = True
                loop_state.decisions.append(f"Tool loop guardrail: {stop_reason}")
                le.save_state(loop_state)
                yield {"type": "reasoning", "content": f"[tool-loop guardrail] {stop_reason}"}
                yield {"type": "status", "content": "loop detected, stopping tool execution"}
                if is_critical:
                    final_text = f"(stopped: {stop_reason})"
                    yield {"type": "final", "content": final_text}
                    le.fail_task(loop_state, stop_reason)
                    tool_loop_error = True
                else:
                    # Soft stop: skip tool call, break to outer loop
                    final_text = f"(loop stopped: {stop_reason})"
                break

            label = _tool_action_label(tool_name, args)
            yield {"type": "tool", "data": {"tool": tool_name, "args": args, "label": label}}
            yield {"type": "status", "content": label}

            # ── Web search budget ────────────────────────────────────
            if tool_name == "web_search":
                loop_state.web_search_count += 1
                le.save_state(loop_state)
                if loop_state.web_search_count > le.MAX_WEB_SEARCH_CALLS:
                    msg = web_search_budget_msg % (le.MAX_WEB_SEARCH_CALLS, le.MAX_WEB_SCRAPE_CALLS)
                    yield {"type": "tool_result", "data": {"tool": tool_name, "summary": msg, "display": msg}}
                    yield {"type": "reasoning", "content": f"[web search budget] {msg}"}
                    initial_messages.append({"role": "user", "content": f"<system>{msg}</system>"})
                    current_user_text = f"<tool_result>\n{msg}\n</tool_result>\n\nContinue."
                    continue
            elif tool_name == "web_scrape":
                loop_state.web_scrape_count += 1
                le.save_state(loop_state)
                if loop_state.web_scrape_count > le.MAX_WEB_SCRAPE_CALLS:
                    msg = web_search_budget_msg % (le.MAX_WEB_SEARCH_CALLS, le.MAX_WEB_SCRAPE_CALLS)
                    yield {"type": "tool_result", "data": {"tool": tool_name, "summary": msg, "display": msg}}
                    yield {"type": "reasoning", "content": f"[web scrape budget] {msg}"}
                    initial_messages.append({"role": "user", "content": f"<system>{msg}</system>"})
                    current_user_text = f"<tool_result>\n{msg}\n</tool_result>\n\nContinue."
                    continue

            tool_result = await _execute_tool(db, workspace_id, call)
            is_success = tool_result.get("result", "").find("Error") != 0
            le.record_tool_result(loop_state, tool_name, args, is_success)

            summary = tool_result.get("result", "")[:500]
            display = _tool_display_summary(tool_name, args, summary)
            yield {"type": "tool_result", "data": {"tool": tool_name, "summary": summary, "display": display}}

            if "artifact" in tool_result:
                yield {"type": "artifact", "data": tool_result["artifact"]}
                loop_state.artifact_produced = True
                le.save_state(loop_state)

            loop_state.tokens_estimated += (len(response_text) + len(summary)) // 4

            # ── Observation recording (Loop Engineering) ─────────────
            obs = le.Observation(
                status="success" if is_success else "failure",
                action_type=tool_name,
                target=str(list(args.values())[0] if args else ""),
                input_summary=json.dumps(args)[:200],
                output_summary=str(tool_result.get("result", ""))[:200],
                error="" if is_success else str(tool_result.get("result", ""))[:200],
            )
            le.record_observation(loop_state, obs)
            le.update_risk_level(loop_state, tool_name, args)

            current_user_text = f"<tool_result>\n{tool_result.get('result', '')}\n</tool_result>\n\nContinue gathering data."

            # ── Accumulate research data for synthesis grounding ─────
            if tool_name in ("web_search", "web_scrape", "youtube_transcript", "github_search", "rss_read"):
                result_text = tool_result.get("result", "")
                if result_text.strip():
                    research_findings.append(
                        f"## Source: {tool_name}\n"
                        f"**Query/Args:** `{json.dumps(args)}`\n\n"
                        f"{result_text}"
                    )

            yield {"type": "status", "content": "processing results and continuing work"}

        if tool_loop_error:
            if not final_text:
                final_text = "(error before any response)"
            yield {"type": "final", "content": final_text}
            break

        # ── Tool turns exhausted — phase-aware handling ──────────────
        if not final_text:
            if sub_phase == "gather":
                # Still gathering but turns exhausted → advance to synthesis
                yield {"type": "reasoning", "content": (
                    "[gather turns exhausted — advancing to synthesis phase]"
                )}
                yield {"type": "status", "content": "gather complete, synthesizing answer"}
                sub_phase = "synthesize"
                current_user_text = _build_synthesis_prompt(
                    user_text, research_findings,
                    reason="Tool calls are exhausted for this phase. Synthesize from what you have.",
                )
                continue  # Re-enter outer while, restart for loop in synthesize

            if loop_state.continue_count >= le.CONTINUE_MAX:
                # Budget fully exhausted — force a summary before stopping
                yield {"type": "status", "content": "reached max turns, requesting summary"}
                yield {"type": "reasoning", "content": "[max turns reached — forcing LLM to summarize]"}
                force_summary_messages = initial_messages.copy()
                force_summary_messages.append({
                    "role": "user",
                    "content": (
                        "You have reached the maximum number of execution steps for this turn. "
                        "Summarize what you accomplished and provide your final response.\n\n"
                        f"Original task: {user_text}"
                    ),
                })
                try:
                    summary_text = await _send_kilocode_chat(force_summary_messages)
                    final_text = summary_text.strip()
                    yield {"type": "reasoning", "content": summary_text}
                except Exception:
                    final_text = f"(reached max steps for this turn. Original task: {user_text})"
            else:
                # Budget remaining — auto-continue
                loop_state.continue_count += 1
                le.save_state(loop_state)
                note = f"[auto-continue: tool turns exhausted, continuing ({loop_state.continue_count}/{le.CONTINUE_MAX})]"
                yield {"type": "reasoning", "content": note}
                yield {"type": "status", "content": "continuing execution"}
                current_user_text = (
                    "Your tool calls completed but the task is not finished. "
                    "Continue working — make more tool calls to complete the task.\n\n"
                    f"Original task: {user_text}"
                )
                continue  # Re-enter tool loop

        le.record_attempt(loop_state, le.PHASE_EXECUTE, (final_text or "")[:200])

        # ── Tool-loop guardrail — feed back, never exit ───────────
        if loop_state.tool_loop_detected_stop:
            loop_state.tool_loop_detected_stop = False  # reset for next iteration
            yield {"type": "reasoning", "content": "[tool-loop guardrail] — same tool/args repeating, try a different approach"}
            le.transition(loop_state, le.PHASE_PLAN, "Tool loop detected, try different approach")
            yield {"type": "loop", "data": {"phase": le.PHASE_PLAN, "message": "Tool loop detected, switch tactics"}}
            current_user_text = (
                "You were calling the same tool with the same arguments repeatedly. "
                "Stop and try a completely different approach.\n\n"
                f"Original task: {user_text}"
            )
            continue

        # ── Response analysis (Ralph-style) ──────────────────────────
        analysis = le.analyze_response_text(final_text or "")
        loop_state.last_asking_questions = analysis["asking_questions"]
        le.update_exit_signals(loop_state, analysis)

        # ── Check exit signal saturation before running expensive evaluation ──
        exit_reason = le.should_exit_gracefully(loop_state)
        if exit_reason:
            yield {"type": "reasoning", "content": f"[exit signal saturation: {exit_reason}]"}
            le.complete_task(loop_state, final_text[:200])
            yield {"type": "loop", "data": {"phase": le.PHASE_DONE}}
            yield {"type": "final", "content": final_text}
            break

        # ── Evaluation + Controller + Reflection + Trace (Loop Engineering) ──
        if final_text:
            if not loop_state.verification_criteria:
                loop_state.verification_criteria = [f"Addresses: {user_text[:100]}"]
                le.save_state(loop_state)

            le.transition(loop_state, le.PHASE_VERIFY, "Running evaluation pass")
            yield {"type": "loop", "data": {"phase": le.PHASE_VERIFY}}
            yield {"type": "status", "content": "verifying output quality against criteria"}

            # Enhanced evaluator with 4 signals (confidence, progress, drift, risk)
            eval_signals = await le.run_evaluation(
                task=loop_state.task_description,
                output=final_text,
                criteria=loop_state.verification_criteria,
                llm_complete_fn=lambda p: _send_kilocode_chat([
                    {"role": "system", "content": "You are a strict quality evaluator."},
                    {"role": "user", "content": p},
                ]),
                recent_observations=loop_state.observations,
            )

            verdict = eval_signals.verdict
            notes = eval_signals.notes

            loop_state.verification_result = verdict
            loop_state.verification_notes = notes
            le.save_state(loop_state)

            yield {"type": "loop", "data": {
                "phase": le.PHASE_VERIFY,
                "verdict": verdict,
                "notes": notes[:300],
                "iteration": loop_state.iteration,
                "signals": {
                    "confidence": eval_signals.confidence,
                    "progress": eval_signals.progress,
                    "drift": eval_signals.drift,
                    "risk": eval_signals.risk,
                },
            }}

            # Controller decision based on evaluator signals + policies
            controller_decision = le.controller_step(loop_state, eval_signals, analysis)

            # Record loop trace (Appendix B schema)
            le.record_loop_trace(loop_state, eval_signals, controller_decision, analysis)

            # ── ONLY exit on 100% complete (PASS verification) ────────
            if verdict == "PASS":
                le.complete_task(loop_state, final_text[:200])
                yield {"type": "loop", "data": {"phase": le.PHASE_DONE}}
                yield {"type": "final", "content": final_text}
                break

            # ── Trust explicit EXIT_SIGNAL even if evaluator disagrees ──
            if analysis.get("explicit_exit_signal"):
                yield {"type": "reasoning", "content": "[LLM explicitly signaled completion — exiting despite evaluator verdict]"}
                le.complete_task(loop_state, final_text[:200])
                yield {"type": "loop", "data": {"phase": le.PHASE_DONE}}
                yield {"type": "final", "content": final_text}
                break

            # ── Reflection pass (Loop Engineering) ─────────────────────
            if verdict in ("FAIL", "PARTIAL"):
                lesson = await le.run_reflection(
                    task=loop_state.task_description,
                    output=final_text,
                    verdict=verdict,
                    verifier_notes=notes,
                    attempts_count=loop_state.iteration,
                    llm_complete_fn=lambda p: _send_kilocode_chat([
                        {"role": "system", "content": "You are a reflective analyst."},
                        {"role": "user", "content": p},
                    ]),
                )
                if lesson:
                    le.store_reflective_lesson(loop_state, lesson)
                    yield {"type": "reasoning", "content": f"[reflection] {lesson}"}

            # ── Controller-guided refinement ─────────────────────────
            feedback = (
                f"Your previous output was verified as **{verdict}**.\n"
                f"Verifier notes: {notes}\n"
            )

            if controller_decision == "escalate":
                feedback += (
                    "\n⚠️ The system recommends escalation — the loop is stuck or high-risk. "
                    "Change approach entirely or ask for human review.\n"
                )
                le.escalate_task(loop_state, f"Controller escalated after {verdict}: {notes[:100]}")

            yield {"type": "status", "content": f"refining output after {verdict.lower()} — {controller_decision}"}
            le.transition(loop_state, le.PHASE_PLAN, f"Refining after {verdict} ({controller_decision})")
            yield {"type": "loop", "data": {"phase": le.PHASE_PLAN, "message": f"Refining after {verdict}"}}

            feedback += (
                f"\nCall more tools to gather the information needed to complete the task. "
                f"Use the available tools to do the actual work — do not just rewrite your output.\n"
                f"This is iteration {loop_state.iteration}.\n\n"
                f"Original task: {user_text}"
            )
            current_user_text = feedback
            continue

        # ── No output to verify — feed back and continue ─────────────
        le.transition(loop_state, le.PHASE_PLAN, "No output generated, retrying")
        yield {"type": "loop", "data": {"phase": le.PHASE_PLAN, "message": "No output generated"}}
        current_user_text = (
            f"You did not produce any output. Please actually execute the work and provide a result.\n\n"
            f"Original task: {user_text}"
        )
        continue
    else:
        if not final_text:
            final_text = "(stopped after max iterations)"
            yield {"type": "final", "content": final_text}

    yield {"type": "status", "content": ""}
