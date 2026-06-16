"""Tool implementations for the AI coworker.
Each tool returns a dict with 'result' (string for LLM) and optional 'artifact' (dict for client).
"""
import os
import uuid
import json
import html
import asyncio
from pathlib import Path
from datetime import datetime

import agent_skills
import skill_forge
import loop_engine
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Theme ----------------
INK = colors.HexColor("#15110d")
INK_SOFT = colors.HexColor("#3a342d")
MUTED = colors.HexColor("#7a7368")
RULE = colors.HexColor("#e6e0d2")
PAPER = colors.HexColor("#fafaf5")
SURFACE = colors.HexColor("#ffffff")
ACCENT = colors.HexColor("#7c5cf5")
ACCENT_SOFT = colors.HexColor("#ede9fb")
SUCCESS = colors.HexColor("#16a34a")
WARN = colors.HexColor("#d97706")
DANGER = colors.HexColor("#dc2626")


# ---------------- Tool definitions ----------------
TOOL_SPECS = [
    {
        "name": "web_search",
        "description": "Search the live internet via DuckDuckGo. Use for current news, facts, competitor research, anything time-sensitive.",
        "args": {"query": "string", "max_results": "integer, optional (default 5)"},
    },
    {
        "name": "generate_pdf",
        "description": (
            "Generate a designed PDF report (NOT a plain text dump). "
            "Pick the right mix of section types so it looks like a real designed document. "
            "Use 'kpis' for numeric highlights at the top, 'callout' for emphasis or quotes, "
            "'table' for data, 'bullets' for lists, 'paragraph' for narrative."
        ),
        "args": {
            "title": "string - document title",
            "subtitle": "string, optional - tagline shown under title",
            "accent": "string, optional - one of: purple (default), green, amber, red, blue",
            "sections": (
                "array. Each item is ONE of:\n"
                "  {type: 'heading', text: 'H2 heading'}\n"
                "  {type: 'paragraph', text: '...'}\n"
                "  {type: 'bullets', items: ['point 1', 'point 2', ...]}\n"
                "  {type: 'kpis', items: [{label, value, delta?}, ...]} -- 2-4 stat cards in a row\n"
                "  {type: 'callout', text: '...', variant?: 'accent'|'success'|'warn'|'danger'}\n"
                "  {type: 'table', columns: ['Col A', 'Col B'], rows: [['a1','b1'], ...]}\n"
                "  {type: 'divider'}\n"
                "  {heading: '...', body: '...'} -- legacy shorthand for heading + paragraph"
            ),
        },
    },
    {
        "name": "generate_webapp",
        "description": (
            "Generate a single-file HTML web app and deploy it. Returns a live URL. "
            "Use for dashboards, internal tools, demos, landing pages. "
            "MUST be visually designed (see system prompt) — never plain unstyled HTML."
        ),
        "args": {
            "title": "string",
            "html": "string - complete <!DOCTYPE html> document with inline <style> and <script>. Include Google Fonts, real typography, layout, hover states, and a clear design system.",
        },
    },
    {
        "name": "save_memory",
        "description": "Persist a fact about the user/team/business across all future conversations.",
        "args": {"key": "string", "value": "string"},
    },
    {
        "name": "recall_memory",
        "description": "List everything you remember about the user.",
        "args": {},
    },
    {
        "name": "schedule_task",
        "description": "Schedule a recurring task that runs automatically.",
        "args": {
            "name": "string",
            "cadence": "string - one of: daily, weekly, monthly",
            "time": "string - HH:MM 24-hour",
            "prompt": "string - the instruction to execute each run",
        },
    },
    {
        "name": "import_skill",
        "description": (
            "Import agent skills from a GitHub repository URL into Cogent's skill directory. "
            "Scans the repo for SKILL.md files, parses their frontmatter, and installs them. "
            "Use when the user provides a GitHub URL containing agent skills they want to use."
        ),
        "args": {
            "repo_url": "string - full GitHub URL (https://github.com/owner/repo or owner/repo shorthand)",
            "force": "boolean, optional - overwrite existing skills if true (default false)",
        },
    },
    {
        "name": "get_loop_state",
        "description": (
            "Get the current loop engineering state for this session. "
            "Use to check your current phase, iteration count, past attempts, "
            "and verification results. Helps avoid repeating failed approaches."
        ),
        "args": {},
    },
]


def tool_specs_for_prompt() -> str:
    specs = list(TOOL_SPECS)
    if agent_skills.has_skills():
        specs.extend([
            {
                "name": "activate_skill",
                "description": (
                    "Load the full instructions for an available Agent Skill. "
                    "Use before performing a task that matches a listed skill description."
                ),
                "args": {"name": "string - one of the available skill names"},
            },
            {
                "name": "read_skill_resource",
                "description": (
                    "Read a bundled resource file from an activated Agent Skill, such as "
                    "references/REFERENCE.md, scripts/helper.py, or assets/template.md."
                ),
                "args": {
                    "skill_name": "string - activated skill name",
                    "path": "string - relative path inside the skill directory",
                },
            },
        ])
    return json.dumps(specs, indent=2)


async def activate_skill(name: str) -> dict:
    return await asyncio.to_thread(agent_skills.activate_skill, name)


async def read_skill_resource(skill_name: str, path: str) -> dict:
    return await asyncio.to_thread(agent_skills.read_skill_resource, skill_name, path)


async def import_skill(repo_url: str, force: bool = False) -> dict:
    """Import skills from a GitHub URL. Returns a summary for the LLM."""
    try:
        result = await skill_forge.import_from_url(repo_url, force=force)
        lines = [f"Repo: {result['repo']}"]
        for s in result.get("skills", []):
            act = s.get("action", "?")
            name = s.get("name", "?")
            lines.append(f"  {act}: {name}")
        if result.get("errors"):
            for e in result["errors"]:
                lines.append(f"  error: {e}")
        return {"result": "\n".join(lines) if lines else "No skills found or imported."}
    except Exception as e:
        return {"result": f"Import failed: {e}"}


# ---------------- Web search ----------------
async def web_search(query: str, max_results: int = 5) -> dict:
    def _run():
        from ddgs import DDGS
        try:
            with DDGS() as ddg:
                return list(ddg.text(query, max_results=max_results))
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


# ---------------- Loop state tool ----------------
async def get_loop_state(session_id: str = "") -> dict:
    """Return the current loop engineering state as a formatted string."""
    if session_id:
        state = loop_engine.load_state(session_id)
    else:
        states = loop_engine.get_all_loop_states()
        if not states:
            return {"result": "No active loop states."}
        lines = ["Active loop states:"]
        for s in states:
            lines.append(f"  {s['session_id'][:12]} — phase={s['phase']} iter={s['iteration']} task={s['task_description'][:60]}")
        return {"result": "\n".join(lines)}

    lines = [
        f"Phase: {state.phase}",
        f"Iteration: {state.iteration}/{loop_engine.MAX_ITERATIONS}",
        f"Task: {state.task_description[:120]}",
        f"Verification: {state.verification_result or 'not run'}",
        f"Token budget: ~{state.tokens_estimated}/{state.budget_max}",
        f"Attempts: {len(state.attempts)}",
        f"Errors: {len(state.errors)}",
    ]
    if state.errors:
        for e in state.errors:
            lines.append(f"  - {e}")
    if state.decisions:
        lines.append("Recent decisions:")
        for d in state.decisions[-3:]:
            lines.append(f"  - {d}")
    return {"result": "\n".join(lines)}


# ---------------- PDF Generation ----------------
ACCENT_MAP = {
    "purple": colors.HexColor("#7c5cf5"),
    "green": colors.HexColor("#16a34a"),
    "amber": colors.HexColor("#d97706"),
    "red": colors.HexColor("#dc2626"),
    "blue": colors.HexColor("#2563eb"),
}
ACCENT_SOFT_MAP = {
    "purple": colors.HexColor("#ede9fb"),
    "green": colors.HexColor("#e7f7ed"),
    "amber": colors.HexColor("#fbf2e3"),
    "red": colors.HexColor("#fbe9e9"),
    "blue": colors.HexColor("#e6efff"),
}


def _build_styles(accent_color):
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=ss["Title"],
            fontName="Helvetica-Bold", fontSize=32, leading=36,
            textColor=INK, alignment=TA_LEFT, spaceBefore=0, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"],
            fontName="Helvetica", fontSize=13, leading=18,
            textColor=MUTED, alignment=TA_LEFT, spaceAfter=4),
        "meta": ParagraphStyle("meta", parent=ss["Normal"],
            fontName="Courier", fontSize=9, leading=12,
            textColor=MUTED, alignment=TA_LEFT, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"],
            fontName="Helvetica-Bold", fontSize=16, leading=22,
            textColor=INK, spaceBefore=22, spaceAfter=10),
        "section_badge": ParagraphStyle("section_badge", parent=ss["Normal"],
            fontName="Courier-Bold", fontSize=7.5, leading=9,
            textColor=accent_color, alignment=TA_LEFT, spaceAfter=5),
        "body": ParagraphStyle("body", parent=ss["Normal"],
            fontName="Helvetica", fontSize=11, leading=17,
            textColor=INK_SOFT, alignment=TA_LEFT, spaceAfter=10),
        "bullet": ParagraphStyle("bullet", parent=ss["Normal"],
            fontName="Helvetica", fontSize=11, leading=17,
            textColor=INK_SOFT, leftIndent=14, bulletIndent=0, spaceAfter=4),
        "kpi_label": ParagraphStyle("kpil", parent=ss["Normal"],
            fontName="Courier", fontSize=8, leading=10,
            textColor=MUTED, alignment=TA_LEFT, spaceAfter=4),
        "kpi_value": ParagraphStyle("kpiv", parent=ss["Normal"],
            fontName="Helvetica-Bold", fontSize=22, leading=24,
            textColor=INK, alignment=TA_LEFT, spaceAfter=2),
        "kpi_delta": ParagraphStyle("kpid", parent=ss["Normal"],
            fontName="Helvetica", fontSize=10, leading=12,
            textColor=accent_color, alignment=TA_LEFT),
        "callout": ParagraphStyle("callout", parent=ss["Normal"],
            fontName="Helvetica", fontSize=11.5, leading=18,
            textColor=INK, alignment=TA_LEFT),
        "tbl_head": ParagraphStyle("th", parent=ss["Normal"],
            fontName="Helvetica-Bold", fontSize=9.5, leading=12,
            textColor=INK, alignment=TA_LEFT),
        "tbl_cell": ParagraphStyle("td", parent=ss["Normal"],
            fontName="Helvetica", fontSize=10, leading=14,
            textColor=INK_SOFT, alignment=TA_LEFT),
        "footer": ParagraphStyle("footer", parent=ss["Normal"],
            fontName="Courier", fontSize=8, leading=10,
            textColor=MUTED, alignment=TA_RIGHT),
    }


def _escape(s):
    if s is None:
        return ""
    return html.escape(str(s)).replace("\n", "<br/>")


def _bullets_flow(items, styles, accent_color):
    flow = []
    for item in items:
        p = Paragraph(
            f'<font color="{accent_color.hexval()[2:]}">●</font>&nbsp;&nbsp;{_escape(item)}',
            styles["bullet"],
        )
        flow.append(p)
    flow.append(Spacer(1, 6))
    return flow


def _paragraph_flow(text, styles):
    blocks = [b.strip() for b in (text or "").split("\n\n") if b.strip()]
    flow = []
    for b in blocks:
        b_safe = _escape(b)
        flow.append(Paragraph(b_safe, styles["body"]))
    return flow


def _kpi_flow(items, styles, accent_color, accent_soft):
    # build a single-row table of KPI cards
    if not items:
        return []
    cells = []
    for it in items[:4]:
        label = it.get("label", "")
        value = it.get("value", "")
        delta = it.get("delta", "")
        inner = [
            Paragraph(_escape(label).upper(), styles["kpi_label"]),
            Paragraph(_escape(value), styles["kpi_value"]),
        ]
        if delta:
            inner.append(Paragraph(_escape(delta), styles["kpi_delta"]))
        cells.append(inner)
    n = len(cells)
    page_w = LETTER[0] - 1.8 * inch
    col_w = page_w / n
    t = Table([cells], colWidths=[col_w] * n)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LINEABOVE", (0, 0), (-1, 0), 2.0, accent_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [t, Spacer(1, 14)]


def _callout_flow(text, styles, accent_color, variant="accent"):
    variant_color = {
        "accent": accent_color,
        "success": SUCCESS,
        "warn": WARN,
        "danger": DANGER,
    }.get(variant, accent_color)
    variant_bg = {
        "accent": ACCENT_SOFT,
        "success": colors.HexColor("#e7f7ed"),
        "warn": colors.HexColor("#fbf2e3"),
        "danger": colors.HexColor("#fbe9e9"),
    }.get(variant, ACCENT_SOFT)
    para = Paragraph(_escape(text), styles["callout"])
    t = Table([[para]], colWidths=[LETTER[0] - 1.8 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), variant_bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, variant_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return [t, Spacer(1, 12)]


def _table_flow(columns, rows, styles, accent_soft):
    cols = [Paragraph(_escape(c), styles["tbl_head"]) for c in columns]
    body_rows = []
    for r in rows:
        body_rows.append([Paragraph(_escape(c), styles["tbl_cell"]) for c in r])
    data = [cols] + body_rows
    n = max(1, len(columns))
    page_w = LETTER[0] - 1.8 * inch
    t = Table(data, colWidths=[page_w / n] * n, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), accent_soft),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # alternating rows
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), PAPER))
    style.append(("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE))
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 14)]


def _divider_flow():
    t = Table([[" "]], colWidths=[LETTER[0] - 1.8 * inch], rowHeights=[1])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE)]))
    return [Spacer(1, 8), t, Spacer(1, 12)]


def _render_section(sec, styles, accent_color, accent_soft):
    # legacy shape: {heading, body}
    if "type" not in sec and ("heading" in sec or "body" in sec):
        flow = []
        if sec.get("heading"):
            flow.append(Paragraph(_escape(sec["heading"]), styles["h2"]))
        if sec.get("body"):
            flow.extend(_paragraph_flow(sec["body"], styles))
        return flow

    t = sec.get("type", "paragraph")
    if t == "heading":
        return [
            Spacer(1, 2),
            Paragraph("SECTION", styles["section_badge"]),
            Paragraph(_escape(sec.get("text", "")), styles["h2"]),
        ]
    if t == "paragraph":
        return _paragraph_flow(sec.get("text", ""), styles)
    if t == "bullets":
        return _bullets_flow(sec.get("items", []), styles, accent_color)
    if t == "kpis":
        return _kpi_flow(sec.get("items", []), styles, accent_color, accent_soft)
    if t == "callout":
        return _callout_flow(sec.get("text", ""), styles, accent_color, sec.get("variant", "accent"))
    if t == "table":
        return _table_flow(sec.get("columns", []), sec.get("rows", []), styles, accent_soft)
    if t == "divider":
        return _divider_flow()
    if t == "spacer":
        return [Spacer(1, sec.get("h", 10))]
    return _paragraph_flow(sec.get("text", ""), styles)


def _make_page_decoration(accent_color):
    def _on_page(canvas, doc):
        canvas.saveState()
        # warm paper background
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, LETTER[0], LETTER[1], fill=1, stroke=0)
        # content surface
        canvas.setFillColor(SURFACE)
        canvas.roundRect(0.65 * inch, 0.78 * inch, LETTER[0] - 1.3 * inch, LETTER[1] - 1.7 * inch, 12, fill=1, stroke=0)
        # top accent band
        canvas.setFillColor(accent_color)
        canvas.rect(0, LETTER[1] - 14, LETTER[0], 14, fill=1, stroke=0)
        # footer
        canvas.setFillColor(MUTED)
        canvas.setFont("Courier", 8)
        page_num = canvas.getPageNumber()
        canvas.drawString(0.9 * inch, 0.5 * inch, "Generated by Cogent")
        canvas.drawRightString(LETTER[0] - 0.9 * inch, 0.5 * inch, f"Page {page_num}")
        # thin rule above footer
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(0.9 * inch, 0.7 * inch, LETTER[0] - 0.9 * inch, 0.7 * inch)
        canvas.restoreState()
    return _on_page


async def generate_pdf(title: str, sections: list, subtitle: str = "", accent: str = "purple") -> dict:
    accent_color = ACCENT_MAP.get((accent or "purple").lower(), ACCENT)
    accent_soft = ACCENT_SOFT_MAP.get((accent or "purple").lower(), ACCENT_SOFT)

    def _run():
        artifact_id = str(uuid.uuid4())
        fname = ARTIFACTS_DIR / f"{artifact_id}.pdf"

        styles = _build_styles(accent_color)

        doc = BaseDocTemplate(
            str(fname),
            pagesize=LETTER,
            topMargin=1.05 * inch,
            bottomMargin=0.95 * inch,
            leftMargin=0.9 * inch,
            rightMargin=0.9 * inch,
        )
        frame = Frame(
            doc.leftMargin, doc.bottomMargin,
            doc.width, doc.height, id="main"
        )
        deco = _make_page_decoration(accent_color)
        doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=deco)])

        story = []
        story.append(Paragraph(_escape(title), styles["title"]))
        if subtitle:
            story.append(Spacer(1, 4))
            story.append(Paragraph(_escape(subtitle), styles["subtitle"]))
        story.append(Spacer(1, 4))
        meta = f"Prepared by Cogent  ·  {datetime.utcnow().strftime('%B %d, %Y')}"
        story.append(Paragraph(meta, styles["meta"]))
        story.append(Spacer(1, 6))
        story.extend(_divider_flow())

        for sec in (sections or []):
            try:
                story.extend(_render_section(sec, styles, accent_color, accent_soft))
            except Exception as e:
                story.append(Paragraph(f"[render error: {_escape(str(e))}]", styles["body"]))

        doc.build(story)
        size_kb = round(fname.stat().st_size / 1024, 1)
        return artifact_id, size_kb

    artifact_id, size_kb = await asyncio.to_thread(_run)
    return {
        "result": f"PDF generated. {len(sections or [])} sections, {size_kb} KB.",
        "artifact": {
            "id": artifact_id,
            "type": "pdf",
            "title": title,
            "size_kb": size_kb,
            "url": f"/api/artifact/{artifact_id}",
        },
    }


# ---------------- Web app generation ----------------
async def generate_webapp(title: str, html_doc: str) -> dict:
    artifact_id = str(uuid.uuid4())
    fname = ARTIFACTS_DIR / f"{artifact_id}.html"
    if "<html" not in (html_doc or "").lower():
        html_doc = f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head><body>\n{html_doc}\n</body></html>"
    fname.write_text(html_doc, encoding="utf-8")
    return {
        "result": f"Web app deployed at /api/artifact/{artifact_id}. Tell the user to click to open.",
        "artifact": {
            "id": artifact_id,
            "type": "webapp",
            "title": title,
            "url": f"/api/artifact/{artifact_id}",
        },
    }


# ---------------- Memory + Schedule ----------------
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
