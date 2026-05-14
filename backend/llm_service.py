"""Tool-using LLM loop for Viktor the AI coworker.
Exposes both a one-shot run_turn and an async-generator run_turn_stream that
yields progress events: status, tool, tool_result, artifact, final.
"""
import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator

from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv

import tools as tool_impls

load_dotenv()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"
MAX_TOOL_TURNS = 6


def build_system_prompt(workspace_name: str = "your team", memory_facts: str = "") -> str:
    mem_block = f"\n\n## Known facts about the user (from memory)\n{memory_facts}\n" if memory_facts else ""
    return f"""You are Viktor — an AI coworker for {workspace_name}.

You are NOT a chatbot. You are a colleague who ships real work. You don't just describe what to do; you do it. When the user asks for an audit, you produce the PDF. When they ask for a dashboard, you build and deploy it.{mem_block}

## Tool use protocol
You have tools. To use a tool, output a fenced JSON block on its OWN LINE, exactly like this:

<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>

After the tool block, STOP generating. The system will execute the tool and send the result in the next turn. Then continue.

Issue ONE tool call per turn. You may chain multiple turns.

## Tools available
{tool_impls.tool_specs_for_prompt()}

## Style rules
- Be brief. Colleagues don't lecture.
- Lowercase casual tone unless user is formal.
- When you finish a task, tell the user what's ready in ONE sentence.
- When user shares a preference, fact, or recurring need, silently call save_memory.
- For research tasks, web_search first.
- For PDFs: write substantive content. Bullets for lists, paragraphs for narrative.
- For web apps: ship a functional single-file HTML page with inline styles. Dark theme: cream text #f5ede0 on dark #15110d, purple accent #b5a8f5.
- If the user attached files, the extracted content is in their message. Reference it directly.

Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}.
"""


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


async def _execute_tool(db, workspace_id: str, call: dict) -> dict:
    name = call.get("name")
    args = call.get("args") or {}
    try:
        if name == "web_search":
            return await tool_impls.web_search(args.get("query", ""), int(args.get("max_results", 5)))
        if name == "generate_pdf":
            return await tool_impls.generate_pdf(args.get("title", "Untitled"), args.get("sections") or [])
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
    """Streaming run. Yields events: status, tool, tool_result, artifact, final, error."""
    memory_facts = await _load_memory_facts(db, workspace_id)
    system_prompt = build_system_prompt(memory_facts=memory_facts)
    initial_messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        initial_messages.append({"role": h["role"], "content": h["content"]})

    current_user_text = user_text
    final_text = ""

    yield {"type": "status", "content": "thinking"}

    for turn in range(MAX_TOOL_TURNS):
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"{session_id}-{turn}",
            system_message=system_prompt,
            initial_messages=initial_messages.copy(),
        ).with_model(MODEL_PROVIDER, MODEL_NAME).with_params(max_tokens=4000)

        try:
            response_text = await chat.send_message(UserMessage(text=current_user_text))
        except Exception as e:
            yield {"type": "error", "content": f"LLM error: {e}"}
            final_text = f"(LLM error: {e})"
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
        yield {"type": "tool", "data": {"tool": tool_name, "args": args, "summary": ""}}
        yield {"type": "status", "content": f"running {tool_name}"}

        tool_result = await _execute_tool(db, workspace_id, call)
        summary = tool_result.get("result", "")[:300]
        yield {"type": "tool_result", "data": {"tool": tool_name, "summary": summary}}

        if "artifact" in tool_result:
            yield {"type": "artifact", "data": tool_result["artifact"]}

        current_user_text = f"<tool_result>\n{tool_result.get('result', '')}\n</tool_result>\n\nContinue."
        yield {"type": "status", "content": "thinking"}

    if not final_text:
        final_text = "(stopped after max tool turns)"
        yield {"type": "final", "content": final_text}
