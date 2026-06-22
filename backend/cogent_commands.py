"""Command registry and execution for plugin slash commands.

Each plugin can provide commands (markdown instructions in ``commands/<name>/SKILL.md``)
that the LLM can invoke explicitly via ``/plugin:command``.  Commands are like
skills but triggered by explicit naming rather than automatic relevance detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cogent_plugins

logger = logging.getLogger("cogent.commands")


@dataclass
class Command:
    name: str
    plugin: str
    description: str
    body: str


# ── In-memory cache ────────────────────────────────────────────────────────

_commands: Dict[str, Command] = {}
_cache_valid = False


def _refresh_cache() -> None:
    global _commands, _cache_valid
    plugins = cogent_plugins.discover_plugins()
    commands: Dict[str, Command] = {}
    for plugin in plugins.values():
        for pc in plugin.commands:
            cmd = Command(
                name=pc.name,
                plugin=pc.plugin,
                description=pc.description,
                body=pc.body,
            )
            commands[pc.name] = cmd
    _commands = commands
    _cache_valid = True


def discover_commands() -> Dict[str, Command]:
    if not _cache_valid:
        _refresh_cache()
    return dict(_commands)


def get_command(name: str) -> Optional[Command]:
    return discover_commands().get(name)


def command_catalog_for_prompt() -> str:
    """Build a prompt block listing available commands."""
    commands = discover_commands()
    if not commands:
        return ""

    lines = [
        "## Available Commands",
        "Invoke a command by calling run_command with its name.",
        "Commands provide structured workflows for specific tasks.",
        "",
    ]
    for cmd in sorted(commands.values(), key=lambda c: c.name):
        lines.append(f"- /{cmd.name}  —  {cmd.description[:120]}")

    return "\n".join(lines)


def invalidate_cache() -> None:
    global _cache_valid
    _cache_valid = False
