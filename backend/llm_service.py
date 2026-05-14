"""Tool-using LLM loop for Viktor the AI coworker.
Uses Emergent LLM key + Claude Sonnet 4.5 via emergentintegrations.
Since Claude through this lib doesn't expose native tool blocks, we use a
JSON-tagged tool-use protocol: model emits <tool>{...}</tool>, we execute,
feed result back as next user turn.
"""
import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from emergentintegrations.llm.chat import LlmChat, UserMessage
from dotenv import load_dotenv

import tools as tool_impls

load_dotenv()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"

MAX_TOOL_TURNS = 6


def build_system_prompt(workspace_name: str = "your team") -> str:
    return f"""You are Viktor — an AI coworker for {workspace_name}.

You are NOT a chatbot. You are a colleague who ships real work. You don't just describe what to do; you do it. When the user asks for an audit, you produce the PDF. When they ask for a dashboard, you build and deploy it. When they share a fact about their business, you remember it.

## Tool use protocol
You have tools. To use a tool, output a fenced JSON block on its OWN LINE, exactly like this:

<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>

After the tool block, STOP generating. The system will execute the tool and send you the result in the next turn. Then continue.

You may issue ONE tool call per turn. You may chain multiple turns (think → search → think → generate_pdf → reply).

## Tools available
{tool_impls.tool_specs_for_prompt()}

## Style rules
- Be brief. Colleagues don't lecture.
- Use lowercase casual tone unless the user is formal.
- When you finish a task, tell the user what's ready in ONE sentence. Don't recap.
- Never apologize for being an AI. Just do the work.
- When a user shares a preference, fact, or recurring need, silently call save_memory.
- For research tasks, web_search first. Always cite which result you used.
- For PDFs: write substantive content. Don't pad. Use bullets for lists, paragraphs for narrative.
- For web apps: ship a functional single-file HTML page with inline styles and a clean dark theme matching Viktor's brand (cream text #f5ede0 on dark #15110d, purple accent #b5a8f5).

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


async def run_turn(db, session_id: str, workspace_id: str, user_text: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Run one conversational turn with tool loop.

    history: list of {role: 'user'|'assistant', content: str} — prior messages (no system).
    Returns: {final_text, tool_uses: [...], artifacts: [...]}
    """
    system_prompt = build_system_prompt()
    initial_messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        initial_messages.append({"role": h["role"], "content": h["content"]})

    tool_uses = []
    artifacts = []
    current_user_text = user_text

    final_text = ""

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
            final_text = f"(LLM error: {e})"
            break

        # add this exchange to history-for-next-turn
        initial_messages.append({"role": "user", "content": current_user_text})
        initial_messages.append({"role": "assistant", "content": response_text})

        call, before_text = _parse_tool_call(response_text)
        if not call:
            final_text = response_text.strip()
            break

        # execute tool
        tool_result = await _execute_tool(db, workspace_id, call)
        tool_uses.append({
            "tool": call.get("name"),
            "args": call.get("args", {}),
            "summary": tool_result.get("result", "")[:300],
        })
        if "artifact" in tool_result:
            artifacts.append(tool_result["artifact"])

        # feed tool result back as next user message
        current_user_text = f"<tool_result>\n{tool_result.get('result', '')}\n</tool_result>\n\nContinue."

    if not final_text:
        final_text = "(stopped after max tool turns)"

    return {
        "text": final_text,
        "tool_uses": tool_uses,
        "artifacts": artifacts,
    }
