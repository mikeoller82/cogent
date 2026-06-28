"""Tool Registry — Hermes-style registration and discovery for Cogent tools.

Mirrors Hermes' tools/registry.py pattern: centralized registry with
registration, discovery, availability checks, and toolset management.
"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("cogent.tools_registry")


@dataclass
class ToolEntry:
    """A registered tool with metadata and handler."""
    name: str
    description: str
    schema: Dict[str, Any]
    handler: Callable[..., Any]
    toolset: str = "default"
    check_fn: Optional[Callable[[], bool]] = None
    check_cache_ttl: float = 30.0
    _check_cache: float = 0.0
    _check_result: bool = True

    def is_available(self) -> bool:
        if self.check_fn is None:
            return True
        now = time.time()
        if now - self._check_cache > self.check_cache_ttl:
            try:
                self._check_result = self.check_fn()
            except Exception:
                self._check_result = False
            self._check_cache = now
        return self._check_result


class ToolRegistry:
    """Central registry for Cogent tools."""

    def __init__(self):
        self._entries: Dict[str, ToolEntry] = {}
        self._toolsets: Dict[str, Set[str]] = {}

    def register(self, name: str, description: str, schema: Dict[str, Any],
                 handler: Callable, toolset: str = "default",
                 check_fn: Optional[Callable[[], bool]] = None) -> None:
        """Register a tool."""
        self._entries[name] = ToolEntry(
            name=name, description=description, schema=schema,
            handler=handler, toolset=toolset, check_fn=check_fn,
        )
        if toolset not in self._toolsets:
            self._toolsets[toolset] = set()
        self._toolsets[toolset].add(name)
        logger.debug("Registered tool: %s (toolset: %s)", name, toolset)

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        return self._entries.get(name)

    def get_tool_definitions(self, toolsets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool definitions for filtered toolsets."""
        definitions = []
        for entry in self._entries.values():
            if toolsets is None or entry.toolset in toolsets:
                if not entry.is_available():
                    continue
                definitions.append({
                    "type": "function",
                    "function": {
                        "name": entry.name,
                        "description": entry.description,
                        "parameters": entry.schema,
                    },
                })
        return definitions

    def list_tools(self, toolset: Optional[str] = None) -> List[str]:
        if toolset:
            return sorted(self._toolsets.get(toolset, set()))
        return sorted(self._entries.keys())

    def list_toolsets(self) -> List[str]:
        return sorted(self._toolsets.keys())


# Singleton
_registry: Optional[ToolRegistry] = None
_registry_initialized: bool = False


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def init_default_registry() -> ToolRegistry:
    """Register all Cogent default tools into the singleton registry.

    Called once at startup (from ``tools.py``).  Subsequent calls are
    no-ops.  This is the single source of truth for which tools exist,
    their descriptions, and a reference to their handler so that both
    ``llm_service`` and ``subagent`` dispatch through the same table.
    """
    global _registry_initialized
    if _registry_initialized:
        return get_registry()

    registry = get_registry()
    import tools as tool_impls
    import agent_reach_tools as art

    # ── Tools from tools.py (no db dependency) ───────────────────────
    _reg(registry, "web_search",
         "Search the live internet via Firecrawl. Returns result titles, URLs, descriptions, and full page content.",
         {"query": "string - what to search for", "max_results": "integer, optional (default 5)"},
         tool_impls.web_search, "web")
    _reg(registry, "web_scrape",
         "Extract clean readable content (markdown) from a URL via Firecrawl.",
         {"url": "string - the full URL to extract content from"},
         tool_impls.web_scrape, "web")
    _reg(registry, "generate_pdf",
         "Generate a designed PDF report with sections like kpis, callouts, tables, bullets, paragraphs.",
         {"title": "string", "sections": "array", "subtitle": "string, optional", "accent": "string, optional"},
         tool_impls.generate_pdf, "output")
    _reg(registry, "generate_webapp",
         "Generate a single-file HTML web app and deploy it. Returns a live URL.",
         {"title": "string", "html": "string"},
         tool_impls.generate_webapp, "output")
    _reg(registry, "search_skills",
         "Search available skills by keyword to find ones relevant to your task.",
         {"query": "string", "max_results": "integer, optional (default 10)"},
         tool_impls.search_skills, "skills")
    _reg(registry, "activate_skill",
         "Load the full instructions for an available Agent Skill.",
         {"name": "string"},
         tool_impls.activate_skill, "skills")
    _reg(registry, "read_skill_resource",
         "Read a bundled resource file from an activated Agent Skill.",
         {"skill_name": "string", "path": "string"},
         tool_impls.read_skill_resource, "skills")
    _reg(registry, "import_skill",
         "Import agent skills from a GitHub repository URL into Cogent's skill directory.",
         {"repo_url": "string", "force": "boolean, optional"},
         tool_impls.import_skill, "skills")
    _reg(registry, "get_loop_state",
         "Get the current loop engineering state for this session.",
         {},
         tool_impls.get_loop_state, "system")
    _reg(registry, "run_shell",
         "Run a shell command (non-interactive). Up to 600s timeout.",
         {"command": "string", "timeout": "integer, optional (default 30)"},
         tool_impls.run_shell, "system")
    _reg(registry, "process_media",
         "Process audio/video/image via ffmpeg (info, convert, compress, extract_audio, trim, screenshot, gif).",
         {"action": "string", "input": "string", "output": "string, optional", "start": "string, optional", "duration": "string, optional", "format": "string, optional", "quality": "integer, optional"},
         tool_impls.process_media, "media")
    _reg(registry, "capture_screenshot",
         "Capture a screenshot of the screen or a specific window.",
         {"output": "string, optional", "delay": "integer, optional (default 1)"},
         tool_impls.capture_screenshot, "media")
    _reg(registry, "file_write",
         "Write text content to a file. Creates directories as needed.",
         {"path": "string", "content": "string", "mode": "string, optional (default 'w')"},
         tool_impls.file_write, "system")
    _reg(registry, "glob_files",
         "Search for files matching a glob pattern by name/path.",
         {"pattern": "string", "path": "string, optional"},
         tool_impls.glob_files, "system")
    _reg(registry, "grep_files",
         "Search file CONTENTS using ripgrep.",
         {"pattern": "string", "include": "string, optional", "path": "string, optional", "output_mode": "string, optional", "-i": "boolean, optional"},
         tool_impls.grep_files, "system")
    _reg(registry, "mcp_call",
         "Call a tool on an installed MCP (Model Context Protocol) server.",
         {"server": "string", "tool": "string", "args": "dict, optional"},
         tool_impls.mcp_call, "mcp")

    # ── Tools from agent_reach_tools.py ─────────────────────────────
    _reg(registry, "agent_reach_doctor",
         "Check which agent-reach channels are installed and healthy.",
         {},
         art.agent_reach_doctor, "reach")
    _reg(registry, "youtube_transcript",
         "Extract subtitles/transcript from a YouTube video.",
         {"url": "string"},
         art.youtube_transcript, "reach")
    _reg(registry, "github_repo_info",
         "Get detailed information about a GitHub repository.",
         {"repo": "string"},
         art.github_repo_info, "reach")
    _reg(registry, "github_search",
         "Search GitHub repositories by keyword, sorted by stars.",
         {"query": "string", "limit": "integer, optional (default 5)"},
         art.github_search, "reach")
    _reg(registry, "github_search_code",
         "Search GitHub code by keyword. Requires 'gh' CLI.",
         {"query": "string", "limit": "integer, optional (default 5)"},
         art.github_search_code, "reach")
    _reg(registry, "v2ex_hot_topics",
         "Get current hot topics from V2EX (tech community).",
         {"limit": "integer, optional (default 20)"},
         art.v2ex_hot_topics, "reach")
    _reg(registry, "v2ex_topic_detail",
         "Get full details of a V2EX topic including the post content and all replies.",
         {"topic_id": "integer"},
         art.v2ex_topic_detail, "reach")
    _reg(registry, "rss_read",
         "Parse and read an RSS/Atom feed. Returns recent entries.",
         {"url": "string", "limit": "integer, optional (default 10)"},
         art.rss_read, "reach")
    _reg(registry, "bilibili_search",
         "Search Bilibili videos by keyword.",
         {"query": "string", "limit": "integer, optional (default 5)"},
         art.bilibili_search, "reach")

    # ── Plugin tools ────────────────────────────────────────────────
    _reg(registry, "plugin_install",
         "Install a Knowledge Work Plugin from a GitHub repository.",
         {"repo_url": "string", "plugin_name": "string"},
         tool_impls.plugin_install, "plugins")
    _reg(registry, "plugin_list",
         "List all installed plugins with their versions, skill counts, and MCP server counts.",
         {},
         tool_impls.plugin_list, "plugins")
    _reg(registry, "plugin_describe",
         "Show detailed information about an installed plugin.",
         {"name": "string"},
         tool_impls.plugin_describe, "plugins")
    _reg(registry, "run_command",
         "Execute a registered plugin command.",
         {"command": "string"},
         tool_impls.run_command, "plugins")

    _registry_initialized = True
    logger.info("Tool registry initialized with %d tools in %d toolsets",
                len(registry._entries), len(registry._toolsets))
    return registry


def _reg(registry, name, description, args_spec, handler, toolset="default"):
    """Convenience helper — register a single tool with a free-form arg spec."""
    # Convert the free-form args spec to a simple schema for storage
    schema = {
        "type": "object",
        "properties": {k: {"type": "string", "description": v} if isinstance(v, str) else v
                       for k, v in args_spec.items()},
    }
    registry.register(name, description, schema, handler, toolset=toolset)
