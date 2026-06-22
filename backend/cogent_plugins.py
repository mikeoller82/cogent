"""Plugin registry, discovery, and lifecycle for Cogent.

Implements the Knowledge Work Plugins schema:
  plugins/<name>/
    .claude-plugin/plugin.json   # Manifest
    .mcp.json                     # MCP server definitions
    skills/                       # Merged into skill catalog
    commands/                     # Registered in command registry

Plugins sit alongside the existing skills system — they do not replace it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.plugins")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# ── Data models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    description: str
    author: str = ""


@dataclass(frozen=True)
class PluginCommand:
    name: str
    plugin: str
    description: str
    body: str


@dataclass
class Plugin:
    name: str
    manifest: PluginManifest
    directory: Path
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    skills: List[Path] = field(default_factory=list)
    commands: List[PluginCommand] = field(default_factory=list)


# ── Manifest parsing ───────────────────────────────────────────────────────


def read_manifest(plugin_dir: Path) -> Optional[PluginManifest]:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return PluginManifest(
            name=str(data.get("name", plugin_dir.name)),
            version=str(data.get("version", "0.0.0")),
            description=str(data.get("description", "")),
            author=str(data.get("author", {}).get("name", "")),
        )
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read manifest %s: %s", manifest_path, e)
        return None


def read_mcp_json(plugin_dir: Path) -> Dict[str, Any]:
    mcp_path = plugin_dir / ".mcp.json"
    if not mcp_path.is_file():
        return {}
    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        return data.get("mcpServers", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read .mcp.json %s: %s", mcp_path, e)
        return {}


# ── Skills / commands discovery ────────────────────────────────────────────


def discover_plugin_skills(plugin_dir: Path) -> List[Path]:
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def discover_plugin_commands(plugin_dir: Path, plugin_name: str) -> List[PluginCommand]:
    commands_dir = plugin_dir / "commands"
    if not commands_dir.is_dir():
        return []
    result: List[PluginCommand] = []
    for cmd_dir in sorted(commands_dir.iterdir()):
        if not cmd_dir.is_dir():
            continue
        cmd_file = cmd_dir / "SKILL.md"
        if not cmd_file.is_file():
            continue
        body = cmd_file.read_text(encoding="utf-8", errors="replace")
        # Extract name and description from frontmatter
        name = cmd_dir.name
        description = ""
        if body.startswith("---"):
            end = body.find("---", 3)
            if end != -1:
                front = body[3:end].strip()
                for line in front.splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip("\"'")
                body = body[end + 3:].strip()
        result.append(PluginCommand(
            name=f"{plugin_name}:{name}",
            plugin=plugin_name,
            description=description,
            body=body,
        ))
    return result


# ── Plugin loading ─────────────────────────────────────────────────────────


def load_plugin(plugin_dir: Path) -> Optional[Plugin]:
    if not plugin_dir.is_dir():
        return None
    manifest = read_manifest(plugin_dir)
    if not manifest:
        return None
    return Plugin(
        name=manifest.name,
        manifest=manifest,
        directory=plugin_dir,
        mcp_servers=read_mcp_json(plugin_dir),
        skills=discover_plugin_skills(plugin_dir),
        commands=discover_plugin_commands(plugin_dir, manifest.name),
    )


def discover_plugins(plugins_dir: Optional[Path | str] = None) -> Dict[str, Plugin]:
    if isinstance(plugins_dir, str):
        plugins_dir = Path(plugins_dir)
    plugins_dir = plugins_dir or PLUGINS_DIR
    if not plugins_dir.is_dir():
        return {}
    plugins: Dict[str, Plugin] = {}
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        plugin = load_plugin(entry)
        if plugin:
            plugins[plugin.name] = plugin
    return plugins


# ── Plugin installation ────────────────────────────────────────────────────


async def install_plugin_from_repo(repo_url: str, plugin_name: str) -> Dict[str, Any]:
    """Install a plugin from a GitHub repository.

    Supports:
      - ``anthropics/knowledge-work-plugins`` (multi-plugin repo)
      - ``owner/repo`` (single-plugin repo)
    """
    import subprocess as sp

    repo_url = repo_url.strip().rstrip("/")
    # Normalise to https://github.com/owner/repo
    if repo_url.startswith("http"):
        clone_url = repo_url
        if clone_url.endswith(".git"):
            clone_url = clone_url[:-4]
    elif "/" in repo_url and not repo_url.startswith("http"):
        clone_url = f"https://github.com/{repo_url}"
    else:
        return {"result": f"Invalid repo URL: {repo_url}"}

    tmp_dir = PROJECT_ROOT / ".plugin_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", clone_url, str(tmp_dir),
            stdout=sp.PIPE, stderr=sp.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")[:500]
            return {"result": f"Git clone failed: {err}"}

        # Find the plugin directory — either a named subdir or root itself
        candidates: List[Path] = []
        for child in tmp_dir.iterdir():
            if child.is_dir() and child.name == plugin_name:
                candidates.append(child)
        if not candidates:
            # Maybe the whole repo is the plugin
            if (tmp_dir / ".claude-plugin" / "plugin.json").is_file():
                candidates.append(tmp_dir)

        if not candidates:
            shutil.rmtree(tmp_dir)
            return {"result": f"Plugin '{plugin_name}' not found in {repo_url}"}

        src = candidates[0]
        dst = PLUGINS_DIR / plugin_name
        if dst.exists():
            shutil.rmtree(dst)

        shutil.copytree(src, dst)

        # Load the installed plugin
        plugin = load_plugin(dst)
        if not plugin:
            shutil.rmtree(dst)
            return {"result": f"Plugin '{plugin_name}' has no valid manifest"}

        lines = [
            f"Installed plugin: {plugin.name} v{plugin.manifest.version}",
            f"  Description: {plugin.manifest.description}",
            f"  Path: {dst}",
            f"  Skills: {len(plugin.skills)}",
            f"  Commands: {len(plugin.commands)}",
            f"  MCP servers: {len(plugin.mcp_servers)}",
        ]

        # Merge skills into .cogent/skills/ by symlinking
        skills_target = PROJECT_ROOT / ".cogent" / "skills"
        skills_target.mkdir(parents=True, exist_ok=True)
        merged = 0
        for skill_path in plugin.skills:
            skill_name = skill_path.parent.name
            link = skills_target / f"{plugin.name}.{skill_name}"
            if not link.exists():
                try:
                    rel = Path(os.path.relpath(skill_path.parent, skills_target))
                    link.symlink_to(rel, target_is_directory=True)
                    merged += 1
                except OSError as e:
                    lines.append(f"  Warning: could not link skill {skill_name}: {e}")

        lines.append(f"  Skills merged: {merged}")

        return {"result": "\n".join(lines)}

    except asyncio.TimeoutError:
        return {"result": f"Plugin install timed out cloning {repo_url}"}
    except Exception as e:
        logger.exception("Plugin install failed")
        return {"result": f"Plugin install error: {e}"}
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Plugin listing / info ──────────────────────────────────────────────────


def list_plugins(plugins_dir: Optional[Path] = None) -> str:
    plugins = discover_plugins(plugins_dir)
    if not plugins:
        return "No plugins installed."
    lines = [f"Installed plugins ({len(plugins)}):"]
    for p in sorted(plugins.values(), key=lambda x: x.name):
        lines.append(f"  {p.name} v{p.manifest.version} — {p.manifest.description[:80]}")
        lines.append(f"    Skills: {len(p.skills)}  Commands: {len(p.commands)}  "
                     f"MCP servers: {len(p.mcp_servers)}")
    return "\n".join(lines)


def describe_plugin(name: str) -> str:
    plugin = load_plugin(PLUGINS_DIR / name)
    if not plugin:
        return f"Plugin not found: {name}"
    lines = [
        f"Plugin: {plugin.name} v{plugin.manifest.version}",
        f"  Description: {plugin.manifest.description}",
        f"  Author: {plugin.manifest.author or '(unknown)'}",
        f"  Path: {plugin.directory}",
        "",
    ]
    if plugin.skills:
        lines.append("  Skills:")
        for s in plugin.skills:
            lines.append(f"    - {s.parent.name}")
    if plugin.commands:
        lines.append("  Commands:")
        for c in plugin.commands:
            lines.append(f"    - /{c.name}  — {c.description}")
    if plugin.mcp_servers:
        lines.append("  MCP servers:")
        for name, cfg in plugin.mcp_servers.items():
            url = cfg.get("url", "") or "(configure in .mcp.json)"
            lines.append(f"    - {name}: {url}")
    return "\n".join(lines)



