"""Tool implementations for the AI coworker.
Each tool returns a dict with 'result' (string for LLM) and optional 'artifact' (dict for client).
"""
import os
import uuid
import json
import html
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import asyncio
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

ARTIFACTS_DIR = Path("/app/backend/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------- Tool definitions (for the LLM system prompt) ----------------
TOOL_SPECS = [
    {
        "name": "web_search",
        "description": "Search the live internet via DuckDuckGo. Use for current news, facts, competitor research, market data, anything time-sensitive.",
        "args": {"query": "string - the search query", "max_results": "integer, optional (default 5)"},
    },
    {
        "name": "generate_pdf",
        "description": "Generate a real downloadable PDF report. Use for board updates, audits, research briefs, anything the user wants to send/save.",
        "args": {
            "title": "string - the document title",
            "sections": "array of {heading: string, body: string}. Body supports markdown-lite: paragraphs separated by blank lines, lines starting with '- ' become bullets.",
        },
    },
    {
        "name": "generate_webapp",
        "description": "Generate a single-file HTML web app (HTML + inline CSS + inline JS) and deploy it. Returns a live URL the user can open. Use for dashboards, internal tools, demo apps.",
        "args": {
            "title": "string",
            "html": "string - complete <!DOCTYPE html> document with inline <style> and <script>",
        },
    },
    {
        "name": "save_memory",
        "description": "Persist a fact about the user/team/business so you remember it across all future conversations. Use when the user shares preferences, business context, tone, integrations, recurring patterns.",
        "args": {
            "key": "string - short identifier like 'company_name', 'tone_preference'",
            "value": "string - the fact to remember",
        },
    },
    {
        "name": "recall_memory",
        "description": "List everything you remember about the user. Call this proactively at the start of a complex task to load context.",
        "args": {},
    },
    {
        "name": "schedule_task",
        "description": "Schedule a recurring task that you'll run automatically. Example: 'Every Monday 9am, audit my Meta Ads and PDF the report.'",
        "args": {
            "name": "string - human-readable task name",
            "cadence": "string - one of: daily, weekly, monthly",
            "time": "string - HH:MM 24-hour, e.g. '09:00'",
            "prompt": "string - the instruction to execute each run",
        },
    },
]


def tool_specs_for_prompt() -> str:
    return json.dumps(TOOL_SPECS, indent=2)


# ---------------- Implementations ----------------
async def web_search(query: str, max_results: int = 5) -> dict:
    def _run():
        from ddgs import DDGS
        try:
            with DDGS() as ddg:
                results = list(ddg.text(query, max_results=max_results))
            return results
        except Exception as e:
            return {"_error": str(e)}

    results = await asyncio.to_thread(_run)
    if isinstance(results, dict) and "_error" in results:
        return {"result": f"Search failed: {results['_error']}"}

    if not results:
        return {"result": "No results found."}

    lines = []
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", "(no title)")
        href = r.get("href") or r.get("url", "")
        body = r.get("body", "")
        lines.append(f"[{i}] {title}\n    {href}\n    {body}")
    return {"result": "\n\n".join(lines)}


def _md_to_paragraphs(body: str, styles):
    blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
    out = []
    for block in blocks:
        lines = block.split("\n")
        if all(l.strip().startswith(("-", "*", "•")) for l in lines if l.strip()):
            for line in lines:
                txt = line.strip().lstrip("-*• ").strip()
                if txt:
                    out.append(Paragraph(f"• &nbsp; {html.escape(txt)}", styles["body"]))
                    out.append(Spacer(1, 4))
        else:
            txt = " ".join(l.strip() for l in lines)
            out.append(Paragraph(html.escape(txt), styles["body"]))
            out.append(Spacer(1, 8))
    return out


async def generate_pdf(title: str, sections: list) -> dict:
    def _run():
        artifact_id = str(uuid.uuid4())
        fname = ARTIFACTS_DIR / f"{artifact_id}.pdf"

        ss = getSampleStyleSheet()
        styles = {
            "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=colors.HexColor("#15110d")),
            "meta": ParagraphStyle("m", parent=ss["Normal"], fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#7a7368")),
            "h2": ParagraphStyle("h", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#15110d")),
            "body": ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=11, leading=16, textColor=colors.HexColor("#2a2520"), alignment=TA_LEFT),
        }

        doc = SimpleDocTemplate(str(fname), pagesize=LETTER, topMargin=0.8*inch, bottomMargin=0.8*inch, leftMargin=0.9*inch, rightMargin=0.9*inch)
        story = []
        story.append(Paragraph(html.escape(title), styles["title"]))
        story.append(Paragraph(f"Generated by Cogent • {datetime.utcnow().strftime('%B %d, %Y')}", styles["meta"]))
        story.append(Spacer(1, 18))
        for sec in sections:
            heading = sec.get("heading", "")
            body = sec.get("body", "")
            if heading:
                story.append(Paragraph(html.escape(heading), styles["h2"]))
            story.extend(_md_to_paragraphs(body, styles))
            story.append(Spacer(1, 6))
        doc.build(story)

        size_kb = round(fname.stat().st_size / 1024, 1)
        return artifact_id, size_kb

    artifact_id, size_kb = await asyncio.to_thread(_run)
    return {
        "result": f"PDF generated successfully. {len(sections)} sections, {size_kb} KB. Tell the user it's ready and reference it by name.",
        "artifact": {
            "id": artifact_id,
            "type": "pdf",
            "title": title,
            "size_kb": size_kb,
            "url": f"/api/artifacts/{artifact_id}/download",
        },
    }


async def generate_webapp(title: str, html_doc: str) -> dict:
    artifact_id = str(uuid.uuid4())
    fname = ARTIFACTS_DIR / f"{artifact_id}.html"
    # ensure full doc
    if "<html" not in html_doc.lower():
        html_doc = f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head><body>\n{html_doc}\n</body></html>"
    fname.write_text(html_doc, encoding="utf-8")
    return {
        "result": f"Web app deployed at /api/artifacts/{artifact_id}/render. Tell the user to click to open.",
        "artifact": {
            "id": artifact_id,
            "type": "webapp",
            "title": title,
            "url": f"/api/artifacts/{artifact_id}/render",
        },
    }


# Memory + Schedule use db reference passed in
async def save_memory(db, workspace_id: str, key: str, value: str) -> dict:
    await db.memories.update_one(
        {"workspace_id": workspace_id, "key": key},
        {"$set": {"value": value, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"result": f"Saved to memory: {key} = {value}"}


async def recall_memory(db, workspace_id: str) -> dict:
    cursor = db.memories.find({"workspace_id": workspace_id}, {"_id": 0, "key": 1, "value": 1})
    items = await cursor.to_list(length=200)
    if not items:
        return {"result": "No memories saved yet."}
    lines = [f"- {m['key']}: {m['value']}" for m in items]
    return {"result": "Known facts:\n" + "\n".join(lines)}


async def schedule_task(db, workspace_id: str, name: str, cadence: str, time: str, prompt: str) -> dict:
    task_id = str(uuid.uuid4())
    doc = {
        "id": task_id,
        "workspace_id": workspace_id,
        "name": name,
        "cadence": cadence,
        "time": time,
        "prompt": prompt,
        "status": "active",
        "created_at": datetime.utcnow(),
        "last_run": None,
    }
    await db.scheduled_tasks.insert_one(doc)
    return {
        "result": f"Scheduled '{name}' to run {cadence} at {time}. I'll handle it automatically.",
        "artifact": {
            "id": task_id,
            "type": "schedule",
            "title": name,
            "cadence": cadence,
            "time": time,
        },
    }
