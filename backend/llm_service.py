"""Tool-using LLM loop for Cogent the AI coworker.
Exposes both a one-shot run_turn and an async-generator run_turn_stream that
yields progress events: status, tool, tool_result, artifact, final.
"""
import os
import re
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator

import requests
from dotenv import load_dotenv

import agent_skills
import tools as tool_impls
import agent_reach_tools as art
import loop_engine as le

load_dotenv()
KILOCODE_MODEL_NAME = "nex-agi/nex-n2-pro:free"
KILOCODE_CHAT_COMPLETIONS_URL = "https://api.kilo.ai/api/gateway/chat/completions"
MAX_TOOL_TURNS = 6

def build_system_prompt(workspace_name: str = "your team", memory_facts: str = "",
                        loop_state=None) -> str:
    mem_block = f"\n\n## Known facts about the user (from memory)\n{memory_facts}\n" if memory_facts else ""
    loop_block = le.build_loop_system_block(loop_state)
    return f"""You are Cogent — an AI coworker. Not a chatbot. A colleague who ships real work.

You don't describe what to do; you do it. Asked for an audit? Hand over the PDF. Asked for a dashboard? Build and deploy it. Told a fact about the business? Remember it.{mem_block}

## Tool use protocol
You have tools. To use a tool, output a fenced JSON block on its OWN LINE, exactly like this:

<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>

After the tool block, STOP generating. The system will execute the tool and send the result in the next turn. Then continue.

Issue ONE tool call per turn. You may chain multiple turns.

## Tools available
{tool_impls.tool_specs_for_prompt()}

{agent_skills.skill_catalog_for_prompt()}

## Style rules
- Be brief. Colleagues don't lecture.
- Use emoji tastefully to add visual punch — one emoji per section is plenty, don't overdo it.
- Lead with your conclusion or answer, then explain if needed.
- Use markdown formatting in every chat response: **bold** for key terms, `code` for filenames/commands/API calls, bullet lists for multiple items, and the occasional heading for structure.
- When the user shares a preference, fact, or recurring need, silently call save_memory.
- For research tasks, use web_search for general web searches, plus the agent-reach tools for platform-specific searches (GitHub, YouTube, V2EX, RSS, Bilibili).
- When researching a topic: combine multiple channels — GitHub for open-source tools, YouTube for video walkthroughs, V2EX for community opinions, RSS for ongoing coverage.

## Design quality (CRITICAL — your work must look designed, not generic)

### PDFs — generate_pdf
Never emit a plain wall of text. Use the rich section types to compose a real document:
- Open with a one-line `subtitle` under the title that tells the reader what they're looking at.
- Pick an `accent` color that fits the topic: purple (default / brand), green (growth, money in), amber (warnings, caution), red (alerts, money out), blue (data, neutral).
- If there are numbers, lead with a `kpis` row (2-4 cards: label + value + optional delta like "+23%" or "↓0.4pt").
- Use `callout` to highlight the single most important insight or recommendation per section.
- Use `table` for any comparison, breakdown, or list of paired data — never describe a table in prose.
- Use `bullets` for action items and lists. Use `paragraph` for narrative.
- Group sections with `heading`. Use `divider` between major parts.
- Aim for a document a CEO would actually read on a Sunday: scannable, designed, with the conclusion up top.
- Treat every PDF as a polished deliverable: premium visual hierarchy, tasteful color accents, and professional report styling.

### Web apps — generate_webapp
Plain unstyled HTML is a failure. Every web app you ship MUST have:
- A clear design system in `:root` CSS variables (palette, type scale, spacing).
- Real typography — load Google Fonts (e.g. Inter + Instrument Serif for landing pages, JetBrains Mono for tools).
- A specific aesthetic — pick one and commit: warm dark (Cogent brand: cream #f5ede0 on #15110d, accent #b5a8f5) OR clean light (off-white #fafaf5, ink #15110d, accent #7c5cf5) OR something the user asks for.
- Proper layout via CSS Grid / Flexbox, generous whitespace (2x more than feels comfortable), and visual hierarchy through size + weight contrast.
- Interactive elements with hover states, smooth transitions (200-300ms), and subtle micro-animations.
- For landing pages: hero with confident headline + italic serif accent + clear CTA, feature grid with icons (use inline SVGs), social proof or testimonial block, footer.
- For dashboards / tools: KPI tiles on a dark or light card surface, sectioned regions, real data visualizations (CSS-only bar charts, gauges, etc. are fine).
- No clip art, no center-aligned body text, no generic Bootstrap look. Borrow taste from Linear, Stripe, Vercel, Notion.
- Keep it single-file — inline `<style>` + inline `<script>`.

If the user attached files, the extracted content is in their message. Reference it directly.
Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}.
{loop_block}
"""



def _tool_action_label(name: str, args: dict) -> str:
    """Generate a human-readable label for what a tool is doing."""
    if name == "web_search":
        q = (args.get("query") or "").strip()
        return f'searching web for "{q}"' if q else "searching the web"
    elif name == "web_scrape":
        url = (args.get("url") or "").strip()
        return f"reading {url}" if url else "reading a webpage"
    elif name == "activate_skill":
        skill = (args.get("name") or "").strip()
        return f"loading skill: {skill}" if skill else "activating a skill"
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
    return f"{name.replace('_', ' ')} complete"

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


def _post_kilocode_chat(messages: List[Dict[str, str]]) -> str:
    api_key = os.environ.get("KILOCODE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing KILOCODE_API_KEY")

    response = requests.post(
        KILOCODE_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": KILOCODE_MODEL_NAME,
            "messages": messages,
            "max_tokens": 4000,
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Kilo Gateway error {response.status_code}: {response.text[:500]}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Kilo Gateway response missing choices[0].message.content")
    if not isinstance(content, str):
        raise RuntimeError("Kilo Gateway response content was not text")
    return content


async def _send_kilocode_chat(messages: List[Dict[str, str]]) -> str:
    return await asyncio.to_thread(_post_kilocode_chat, messages)


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
        return {"result": f"Unknown tool: {name}"}
    except Exception as e:
        return {"result": f"Tool error: {e}"}


async def _load_memory_facts(db, workspace_id: str) -> str:
    cursor = db.memories.find({"workspace_id": workspace_id}, {"_id": 0, "key": 1, "value": 1})
    items = await cursor.to_list(length=100)
    if not items:
        return ""
    return "\n".join(f"- {m['key']}: {m['value']}" for m in items)


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

    Yields events: status, tool, tool_result, artifact, final, error, loop.
    """
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
        for turn in range(MAX_TOOL_TURNS):
            messages = initial_messages.copy()
            messages.append({"role": "user", "content": current_user_text})
            try:
                response_text = await _send_kilocode_chat(messages)
            except Exception as e:
                yield {"type": "error", "content": f"LLM error: {e}"}
                final_text = f"(LLM error: {e})"
                le.fail_task(loop_state, f"LLM error: {e}")
                tool_loop_error = True
                break

            initial_messages.append({"role": "user", "content": current_user_text})
            initial_messages.append({"role": "assistant", "content": response_text})

            call, _ = _parse_tool_call(response_text)
            if not call:
                final_text = response_text.strip()
                yield {"type": "final", "content": final_text}
                break

            tool_name = call.get("name", "")
            args = call.get("args", {})
            label = _tool_action_label(tool_name, args)
            yield {"type": "tool", "data": {"tool": tool_name, "args": args, "label": label}}
            yield {"type": "status", "content": label}
            
            tool_result = await _execute_tool(db, workspace_id, call)
            summary = tool_result.get("result", "")[:500]
            display = _tool_display_summary(tool_name, args, summary)
            yield {"type": "tool_result", "data": {"tool": tool_name, "summary": summary, "display": display}}

            if "artifact" in tool_result:
                yield {"type": "artifact", "data": tool_result["artifact"]}

            loop_state.tokens_estimated += (len(response_text) + len(summary)) // 4
            current_user_text = f"<tool_result>\n{tool_result.get('result', '')}\n</tool_result>\n\nContinue."
            yield {"type": "status", "content": "processing results and continuing work"}
        if tool_loop_error:
            break

        le.record_attempt(loop_state, le.PHASE_EXECUTE, final_text[:200])

        # ── Verification (maker/checker split) ───────────────────────
        if final_text:
            if not loop_state.verification_criteria:
                loop_state.verification_criteria = [f"Addresses: {user_text[:100]}"]
                le.save_state(loop_state)

            le.transition(loop_state, le.PHASE_VERIFY, "Running verification pass")
            yield {"type": "loop", "data": {"phase": le.PHASE_VERIFY}}
            yield {"type": "status", "content": "verifying output quality against criteria"}

            verdict, notes = await le.run_verification(
                task=loop_state.task_description,
                output=final_text,
                criteria=loop_state.verification_criteria,
                llm_complete_fn=lambda p: _send_kilocode_chat([
                    {"role": "system", "content": "You are a strict quality verifier."},
                    {"role": "user", "content": p},
                ]),
            )

            loop_state.verification_result = verdict
            loop_state.verification_notes = notes
            le.save_state(loop_state)

            yield {"type": "loop", "data": {
                "phase": le.PHASE_VERIFY,
                "verdict": verdict,
                "notes": notes[:300],
                "iteration": loop_state.iteration,
            }}

            if verdict == "PASS":
                le.complete_task(loop_state, final_text[:200])
                yield {"type": "loop", "data": {"phase": le.PHASE_DONE}}
                break

            if loop_state.iteration >= le.MAX_ITERATIONS:
                le.complete_task(loop_state, final_text[:200])
                yield {"type": "loop", "data": {"phase": le.PHASE_DONE, "message": "Max iterations reached"}}
                break

            # Feed verification back and loop for refinement
            yield {"type": "status", "content": f"refining output after {verdict.lower()} — reworking based on feedback"}
            le.transition(loop_state, le.PHASE_PLAN, f"Refining after {verdict}")
            yield {"type": "loop", "data": {"phase": le.PHASE_PLAN, "message": f"Refining after {verdict}"}}
            current_user_text = (
                f"Your previous output was verified as **{verdict}**.\n"
                f"Verifier notes: {notes}\n\n"
                f"Refine the output to address these issues. "
                f"This is iteration {loop_state.iteration}.\n\n"
                f"Original task: {user_text}"
            )
            continue

        # No output to verify — done
        le.complete_task(loop_state, final_text[:200])
        yield {"type": "loop", "data": {"phase": le.PHASE_DONE}}
        break

    else:
        if not final_text:
            final_text = "(stopped after max iterations)"
            yield {"type": "final", "content": final_text}

    yield {"type": "status", "content": ""}
