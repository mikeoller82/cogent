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


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
