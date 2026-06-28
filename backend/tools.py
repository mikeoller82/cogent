"""Tool implementations for the AI coworker.
Each tool returns a dict with 'result' (string for LLM) and optional 'artifact' (dict for client).
"""
import os
import re
import uuid
import json
import html
import glob as glob_module
import asyncio
from pathlib import Path
from datetime import datetime

import shlex
import cogent_plugins
import cogent_commands

import agent_skills
import skill_forge
import loop_engine
import firecrawl_service as fc
import agent_reach_tools as art
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
        "description": "Search the live internet via Firecrawl. Returns result titles, URLs, descriptions, and full page content. Use for current news, facts, research, anything time-sensitive.",
        "args": {"query": "string - what to search for", "max_results": "integer, optional (default 5)"},
    },
    {
        "name": "web_scrape",
        "description": "Extract clean readable content (markdown) from a URL via Firecrawl. Use to read articles, docs, blog posts, or any web page the user references.",
        "args": {"url": "string - the full URL to extract content from"},
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
    {
        "name": "agent_reach_doctor",
        "description": "Check which agent-reach channels (YouTube, GitHub, V2EX, RSS, Bilibili) are installed and healthy. Run this first to verify you have the tools you need.",
        "args": {},
    },
    {
        "name": "youtube_transcript",
        "description": "Extract subtitles/transcript from a YouTube video (via yt-dlp). Falls back to video metadata if no subtitles available.",
        "args": {"url": "string - full YouTube URL (e.g. https://www.youtube.com/watch?v=...)"},
    },
    {
        "name": "github_repo_info",
        "description": "Get detailed information about a GitHub repository: stars, forks, description, language, license, topics, recent activity, and README.",
        "args": {"repo": "string - repository in 'owner/repo' format (e.g. 'Panniantong/Agent-Reach')"},
    },
    {
        "name": "github_search",
        "description": "Search GitHub repositories by keyword, sorted by stars. Good for finding popular tools, libraries, and frameworks.",
        "args": {"query": "string - search keywords", "limit": "integer, optional (default 5, max 20)"},
    },
    {
        "name": "github_search_code",
        "description": "Search GitHub code by keyword. Returns matching files with repository and path. Requires 'gh' CLI to be installed.",
        "args": {"query": "string - code search query", "limit": "integer, optional (default 5, max 20)"},
    },
    {
        "name": "v2ex_hot_topics",
        "description": "Get current hot topics from V2EX (tech community). Shows titles, reply counts, and node categories.",
        "args": {"limit": "integer, optional (default 20, max 50)"},
    },
    {
        "name": "v2ex_topic_detail",
        "description": "Get full details of a V2EX topic including the post content and all replies.",
        "args": {"topic_id": "integer - V2EX topic ID from the URL"},
    },
    {
        "name": "rss_read",
        "description": "Parse and read an RSS/Atom feed. Returns recent entries with titles, dates, summaries, and links.",
        "args": {"url": "string - RSS/Atom feed URL", "limit": "integer, optional (default 10, max 50)"},
    },
    {
        "name": "run_shell",
        "description": "Run a shell command (non-interactive). Up to 600s timeout for rendering, compilation, and batch operations. Use for file ops, git, npm/npx/bun, hyperframes render, system tasks.",
        "args": {
            "command": "string - shell command to execute",
            "timeout": "integer, optional - timeout in seconds (default 30, max 600)",
        },
    },
    {
        "name": "process_media",
        "description": "Process audio/video/image via ffmpeg. Actions: info (get file metadata), convert (change format), compress (reduce size), extract_audio (pull audio track), trim (clip segment), screenshot (capture frame at timestamp), gif (make animated GIF from video).",
        "args": {
            "action": "string - one of: info, convert, compress, extract_audio, trim, screenshot, gif",
            "input": "string - path to input file (absolute or relative to cogent root)",
            "output": "string, optional - output path (default: auto-generated in artifacts/)",
            "start": "string, optional - start timestamp for trim/screenshot/gif (e.g. 00:01:30)",
            "duration": "string, optional - duration for trim/gif (e.g. 00:00:10)",
            "format": "string, optional - target format for convert (e.g. mp4, webm, mp3, wav, jpg, png)",
            "quality": "integer, optional - compression quality 1-100 (default 80)",
        },
    },
    {
        "name": "capture_screenshot",
        "description": "Capture a screenshot of the screen or a specific window. Uses scrot or import (ImageMagick). Returns the image path.",
        "args": {
            "output": "string, optional - output path (default: artifacts/screenshot_<timestamp>.png)",
            "delay": "integer, optional - delay in seconds before capture (default 1)",
        },
    },
    {
        "name": "file_write",
        "description": "Write text content to a file. Creates directories as needed. Use for saving code, configs, markdown, data files. Will overwrite existing files.",
        "args": {
            "path": "string - relative path from cogent root (e.g. 'output/report.md', 'data/config.json')",
            "content": "string - text content to write to the file",
            "mode": "string, optional - 'w' to overwrite (default) or 'a' to append",
        },
    },
    {
        "name": "plugin_install",
        "description": "Install a Knowledge Work Plugin from a GitHub repository. Clones the repo and installs the specified plugin. The plugin's skills are merged into the skill catalog, its MCP servers are registered, and its commands become available.",
        "args": {
            "repo_url": "string - GitHub repo URL or 'owner/repo' (e.g. 'anthropics/knowledge-work-plugins' or 'https://github.com/anthropics/knowledge-work-plugins')",
            "plugin_name": "string - name of the plugin directory inside the repo (e.g. 'sales', 'data')",
        },
    },
    {
        "name": "plugin_list",
        "description": "List all installed plugins with their versions, skill counts, command counts, and MCP server counts.",
        "args": {},
    },
    {
        "name": "plugin_describe",
        "description": "Show detailed information about an installed plugin: its manifest, skills, commands, and MCP server definitions.",
        "args": {"name": "string - plugin name (e.g. 'sales', 'data')"},
    },
    {
        "name": "run_command",
        "description": "Execute a registered plugin command. Commands are explicit slash-command workflows (e.g. /sales:account-research, /data:write-query). Call this when the user asks for a specific command workflow or mentions a /plugin:command they want to use.",
        "args": {"command": "string - the command name in 'plugin:command' format (e.g. 'sales:account-research')"},
    },
    {
        "name": "glob_files",
        "description": "Search for files matching a glob pattern by name/path. Returns matching file paths sorted by modification time (most recent first). Results never cross directory boundaries with *, use ** for recursive search. Prefer this over 'find' or 'ls' in shell for file discovery.",
        "args": {
            "pattern": "string - glob pattern (e.g. '**/*.py', 'src/**/*.ts', '*.json')",
            "path": "string, optional - directory to search from (default: project root)",
        },
    },
    {
        "name": "grep_files",
        "description": "Search file CONTENTS using ripgrep. Searches inside files, not file names. Use for finding definitions, usages, references, or any text across the codebase. Pair with glob_files to discover candidate files then grep their contents.",
        "args": {
            "pattern": "string - regex pattern to search for (e.g. 'def main', 'console\\.log')",
            "include": "string, optional - glob pattern to filter files (e.g. '*.py', '*.{ts,tsx}')",
            "path": "string, optional - directory to search in (default: project root)",
            "output_mode": "string, optional - 'files_with_matches' (default, just file paths), 'content' (matching lines with context), or 'count' (match tallies per file)",
            "-i": "boolean, optional - case-insensitive search (default false)",
        },
    },
]


def tool_specs_for_prompt() -> str:
    specs = list(TOOL_SPECS)
    if agent_skills.has_skills():
        specs.extend([
            {
                "name": "search_skills",
                "description": (
                    "Search available skills by keyword to find ones relevant to your task. "
                    "ALWAYS call this before starting any task — scan skills first, "
                    "then activate the relevant ones."
                ),
                "args": {
                    "query": "string - keywords from the task description",
                    "max_results": "integer, optional (default 10)",
                },
            },
            {
                "name": "activate_skill",
                "description": (
                    "Load the full instructions for an available Agent Skill. "
                    "Use after finding a relevant skill via search_skills."
                ),
                "args": {"name": "string - skill name from search_skills results"},
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


async def search_skills(query: str, max_results: int = 10) -> dict:
    return await asyncio.to_thread(agent_skills.search_skills, query, max_results)


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


# ---------------- Web search (Firecrawl) ----------------
async def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web via Firecrawl. Returns formatted results with content."""
    try:
        results = await fc.web_search(query, max_results)
    except Exception as e:
        return {"result": f"Search failed: {e}"}
    if not results:
        return {"result": "No results found."}
    lines = []
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", "") or "(no title)"
        url = r.get("url", "")
        desc = r.get("description", "") or ""
        content = r.get("content", "") or ""
        lines.append(f"[{i}] {title}")
        lines.append(f"    URL: {url}")
        if desc:
            lines.append(f"    About: {desc}")
        if content:
            lines.append(f"    Content: {content[:500]}"
                         f"{'…' if len(content) > 500 else ''}")
    return {"result": "\n".join(lines)}


# ---------------- Web scrape (content extraction via Firecrawl) ----------------
async def web_scrape(url: str) -> dict:
    """Extract clean content from a URL via Firecrawl."""
    try:
        doc = await fc.web_scrape(url)
    except Exception as e:
        return {"result": f"Scrape failed: {e}"}
    title = doc.get("title", "") or "(no title)"
    md = doc.get("markdown", "")
    if not md:
        return {"result": f"**{title}**\n\n(No extractable content at {url})"}
    max_chars = 15_000
    truncated = len(md) > max_chars
    body = md[:max_chars] + ("\n\n…(content truncated)" if truncated else "")
    return {"result": f"# {title}\n\n{body}"}

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


async def run_shell(command: str, timeout: int = 30) -> dict:
    """Run a shell command with timeout. Returns stdout, stderr, exit code.
    Default timeout is 30s; max is 600s (10 min) for rendering/processing.

    Note: the command is passed to ``/bin/sh -c`` directly.  If the command
    contains shell metacharacters (``{``, ``}``, ``[``, ``]``, ``$``, etc.)
    that should be treated as literal text, quote them or escape them as
    you would in any shell.  JSON-like patterns are the most common
    offender — use ``jq -c '.[]'`` (single-quoted) not ``jq -c .[]``.
    """
    import subprocess as sp
    timeout = min(timeout, 600)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            cwd=str(Path(__file__).parent.parent),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout = stdout.decode("utf-8", errors="replace")[:25000]
        stderr = stderr.decode("utf-8", errors="replace")[:10000]
        return {
            "result": (
                f"Exit code: {proc.returncode}\n"
                f"{'[stdout]\\n' + stdout if stdout else ''}"
                f"{'[stderr]\\n' + stderr if stderr else ''}"
            ).strip(),
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return {"result": f"Command timed out after {timeout}s and was killed:\n{command[:200]}"}
    except Exception as e:
        return {"result": f"Shell error: {e}"}

async def process_media(action: str, input: str, output: str = "",
                        start: str = "", duration: str = "",
                        format: str = "", quality: int = 80) -> dict:
    """Process media files via ffmpeg."""
    import subprocess as sp
    from pathlib import Path as PPath

    inp = PPath(input)
    if not inp.is_file():
        return {"result": f"Input not found: {input}"}

    # Default output in artifacts/
    arts_dir = PPath(__file__).parent / "artifacts"
    arts_dir.mkdir(exist_ok=True)
    if not output:
        stem = inp.stem
        # Derive extension from action
        ext_map = {
            "convert": f".{format or inp.suffix.strip('.') or 'mp4'}",
            "compress": inp.suffix or ".mp4",
            "extract_audio": ".mp3",
            "trim": inp.suffix or ".mp4",
            "screenshot": ".png",
            "gif": ".gif",
        }
        out_ext = ext_map.get(action, inp.suffix or ".mp4")
        output = str(arts_dir / f"{stem}_{action}{out_ext}")

    try:
        if action == "info":
            # Use ffprobe for metadata
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
                   "-show_format", "-show_streams", str(inp)]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=sp.PIPE, stderr=sp.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return {"result": f"ffprobe failed: {stderr.decode()[:500]}"}
            return {"result": f"Media info:\n{stdout.decode()[:5000]}"}

        elif action == "convert":
            out_fmt = format or inp.suffix.strip(".") or "mp4"
            cmd = ["ffmpeg", "-y", "-i", str(inp), "-c:v", "libx264" if out_fmt in ("mp4", "mov") else "copy",
                   "-c:a", "aac" if out_fmt in ("mp4", "mov", "m4a") else "copy",
                   str(output)]

        elif action == "compress":
            crf = max(0, min(51, int(51 - quality * 0.5)))
            cmd = ["ffmpeg", "-y", "-i", str(inp), "-c:v", "libx264",
                   "-crf", str(crf), "-preset", "medium",
                   "-c:a", "aac", "-b:a", "128k", str(output)]

        elif action == "extract_audio":
            out_fmt = format or "mp3"
            cmd = ["ffmpeg", "-y", "-i", str(inp), "-vn",
                   "-c:a", "libmp3lame" if out_fmt == "mp3" else "aac",
                   "-q:a", "2" if out_fmt == "mp3" else "", str(output)]
            cmd = [c for c in cmd if c]

        elif action == "trim":
            if not start:
                return {"result": "start timestamp required for trim"}
            cmd = ["ffmpeg", "-y", "-i", str(inp), "-ss", start]
            if duration:
                cmd += ["-t", duration]
            cmd += ["-c", "copy", str(output)]

        elif action == "screenshot":
            ts = start or "00:00:01"
            cmd = ["ffmpeg", "-y", "-i", str(inp), "-ss", ts,
                   "-vframes", "1", str(output)]

        elif action == "gif":
            if not start:
                start = "00:00:00"
            palette = arts_dir / f"{inp.stem}_palette.png"
            # Generate palette
            cmd1 = ["ffmpeg", "-y", "-i", str(inp), "-ss", start]
            if duration:
                cmd1 += ["-t", duration]
            cmd1 += ["-vf", "fps=10,scale=640:-1:flags=lanczos,palettegen",
                     str(palette)]
            proc1 = await asyncio.create_subprocess_exec(*cmd1)
            await proc1.wait()
            # Generate GIF with palette
            cmd2 = ["ffmpeg", "-y", "-i", str(inp), "-i", str(palette),
                    "-ss", start]
            if duration:
                cmd2 += ["-t", duration]
            cmd2 += ["-lavfi", "fps=10,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse",
                     str(output)]
            proc2 = await asyncio.create_subprocess_exec(*cmd2)
            await proc2.wait()

            # Cleanup palette
            PPath(palette).unlink(missing_ok=True)
            if PPath(output).is_file():
                return {"result": f"GIF created: {output}",
                        "artifact": {"id": f"media_{inp.stem}", "type": "media",
                                     "title": f"{inp.stem}.gif", "path": output}}
            return {"result": "GIF creation failed"}

        else:
            return {"result": f"Unknown action: {action}. Use: info, convert, compress, extract_audio, trim, screenshot, or gif."}

        # Execute single-command actions (not gif, which handles itself)
        if action != "gif":
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=sp.PIPE, stderr=sp.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode()[:1000]
                return {"result": f"ffmpeg failed (code {proc.returncode}): {err}"}

            out_path = str(output)
            if PPath(output).is_file():
                size_kb = PPath(output).stat().st_size / 1024
                return {
                    "result": f"Media saved: {out_path} ({size_kb:.0f} KB)",
                    "artifact": {"id": f"media_{inp.stem}", "type": "media",
                                 "title": PPath(output).name, "path": out_path},
                }
        return {"result": f"Media processed: {output}"}

    except FileNotFoundError:
        return {"result": "ffmpeg not found. Install ffmpeg to use media tools."}
    except Exception as e:
        return {"result": f"Media processing error: {e}"}


async def capture_screenshot(output: str = "", delay: int = 1) -> dict:
    """Capture a screenshot using scrot or ImageMagick import."""
    import subprocess as sp
    arts_dir = Path(__file__).parent / "artifacts"
    arts_dir.mkdir(exist_ok=True)
    if not output:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = str(arts_dir / f"screenshot_{ts}.png")

    # Prefer scrot, fallback to ImageMagick import, then xdg-desktop-portal
    cmds = [
        ["scrot", "-d", str(delay), output],
        ["import", "-window", "root", "-delay", str(delay * 100), output],
        ["xdg-desktop-portal", "--screenshot", output],
    ]

    for cmd in cmds:
        try:
            proc = await asyncio.create_subprocess_exec(
                *[c for c in cmd if c],
                stdout=sp.PIPE, stderr=sp.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0 and Path(output).is_file():
                size_kb = Path(output).stat().st_size / 1024
                return {
                    "result": f"Screenshot saved: {output} ({size_kb:.0f} KB)",
                    "artifact": {"id": "screenshot", "type": "image",
                                 "title": Path(output).name, "path": output},
                }
        except (FileNotFoundError, asyncio.TimeoutError):
            continue

    return {"result": "No screenshot tool found (scrot, import, or xdg-desktop-portal required)"}


async def file_write(path: str, content: str, mode: str = "w") -> dict:
    """Write text content to a file. Creates parent directories as needed."""
    root = Path(__file__).parent.parent   # cogent root
    target = root / path

    # Security: prevent path traversal outside project root
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        return {"result": f"Access denied: path must be inside {root}"}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, mode=mode, encoding="utf-8") as f:
            f.write(content)
        size = target.stat().st_size
        return {
            "result": f"Written {size} bytes to {path}",
            "artifact": {"id": f"file_{target.stem}", "type": "file",
                         "title": target.name, "path": str(target)},
        }
    except Exception as e:
        return {"result": f"Write error: {e}"}


# ---------------- Brace expansion helper ----------------
def _expand_braces(pattern: str) -> list[str]:
    """Expand {a,b,c} brace syntax in glob patterns."""
    if '{' not in pattern:
        return [pattern]
    results = ['']
    i = 0
    while i < len(pattern):
        if pattern[i] == '{':
            end = pattern.find('}', i)
            if end == -1:
                results = [r + pattern[i:] for r in results]
                break
            alternatives = pattern[i+1:end].split(',')
            new_results = []
            for r in results:
                for alt in alternatives:
                    new_results.append(r + alt)
            results = new_results
            i = end + 1
        elif pattern[i] == '\\' and i + 1 < len(pattern):
            results = [r + pattern[i:i+2] for r in results]
            i += 2
        else:
            results = [r + pattern[i] for r in results]
            i += 1
    return results


# ---------------- Glob file search ----------------
async def glob_files(pattern: str, path: str = "") -> dict:
    """Search for files matching a glob pattern, sorted by modification time."""
    root = Path(__file__).parent.parent
    search_dir = root
    if path:
        search_dir = (root / path).resolve()
        try:
            search_dir.relative_to(root.resolve())
        except ValueError:
            return {"result": f"Access denied: path must be inside {root}"}

    if not search_dir.is_dir():
        return {"result": f"Directory not found: {search_dir}"}

    try:
        expanded = _expand_braces(pattern)
        all_matches: set[Path] = set()
        for pat in expanded:
            full = str(search_dir / pat)
            all_matches.update(
                Path(m) for m in glob_module.glob(full, recursive=True)
                if Path(m).is_file()
            )

        if not all_matches:
            return {"result": "No files matched the pattern."}

        sorted_matches = sorted(all_matches, key=lambda p: p.stat().st_mtime, reverse=True)
        MAX_SHOWN = 100
        lines = []
        for p in sorted_matches[:MAX_SHOWN]:
            rel = p.relative_to(root)
            ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(f"{rel}  ({ts})")

        summary = f"Found {len(sorted_matches)} file(s)"
        if len(sorted_matches) > MAX_SHOWN:
            summary += f" (showing {MAX_SHOWN})"
        return {"result": summary + ":\n" + "\n".join(lines)}
    except Exception as e:
        return {"result": f"Glob error: {e}"}


# ---------------- Grep content search ----------------
async def grep_files(pattern: str, include: str = "", path: str = "",
                     output_mode: str = "files_with_matches",
                     case_insensitive: bool = False) -> dict:
    """Search file contents using ripgrep."""
    import subprocess as sp

    root = Path(__file__).parent.parent
    search_dir = root
    if path:
        search_dir = (root / path).resolve()
        try:
            search_dir.relative_to(root.resolve())
        except ValueError:
            return {"result": f"Access denied: path must be inside {root}"}

    if not search_dir.exists():
        return {"result": f"Path not found: {search_dir}"}

    try:
        cmd = ["rg", "--no-messages"]
        if case_insensitive:
            cmd.append("-i")
        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")
        elif output_mode == "content":
            cmd.append("-n")
            cmd.extend(["-C", "2"])
        if include:
            cmd.extend(["--glob", include])
        cmd.extend([pattern, str(search_dir)])

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=sp.PIPE, stderr=sp.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        stdout = stdout.decode("utf-8", errors="replace")
        stderr = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 2:
            return {"result": f"Grep error: {stderr[:1000]}".strip()}
        if not stdout.strip():
            return {"result": "No matches found."}

        max_output = 15000
        truncated = len(stdout) > max_output
        body = stdout[:max_output] + ("\n... (output truncated)" if truncated else "")

        if output_mode == "files_with_matches":
            files = [l for l in stdout.strip().split("\n") if l.strip()]
            return {"result": f"Found {len(files)} file(s):\n" + "\n".join(files)}
        elif output_mode == "count":
            return {"result": f"Match counts per file:\n{body}"
                    + ("\n(truncated)" if truncated else "")}
        else:
            lines = stdout.count("\n")
            return {"result": f"Found {lines} matching line(s):\n{body}"}
    except FileNotFoundError:
        return {"result": "ripgrep (rg) not found. Install with: apt install ripgrep  or  brew install ripgrep"}
    except asyncio.TimeoutError:
        return {"result": "Grep search timed out after 30s. Try narrowing with 'include' filter."}
    except Exception as e:
        return {"result": f"Grep error: {e}"}


# ---------------- Plugin management tools ----------------
async def plugin_install(repo_url: str, plugin_name: str) -> dict:
    """Install a plugin from a GitHub repository."""
    result = await cogent_plugins.install_plugin_from_repo(repo_url, plugin_name)
    cogent_commands.invalidate_cache()
    return result


async def plugin_list() -> dict:
    """List all installed plugins."""
    return {"result": cogent_plugins.list_plugins()}


async def plugin_describe(name: str) -> dict:
    """Describe an installed plugin."""
    return {"result": cogent_plugins.describe_plugin(name)}


async def run_command(command: str) -> dict:
    """Execute a registered plugin command."""
    cmd = cogent_commands.get_command(command)
    if not cmd:
        available = cogent_commands.command_catalog_for_prompt()
        return {
            "result": (
                f"Command '{command}' not found.\n"
                f"{available}" if available else "No commands are installed."
            )
        }
    return {
        "result": (
            f'<command name="{cmd.name}">\n'
            f"{cmd.body}\n"
            "</command>"
        )
    }
