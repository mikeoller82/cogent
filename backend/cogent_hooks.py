"""Hook execution infrastructure for Cogent.

Analogous to Hermes' hook system — allows lifecycle hooks
at session start/end, message start/end, and tool call boundaries.

Hooks are Python callables registered by name.  A file-based directory
(``backend/hooks/``) is scanned at startup for ``*.hook.py`` files that
are auto-imported to self-register.

Hook point reference:

- ``before_session_start(session_id, workspace_id)``
- ``after_session_end(session_id, summary)``
- ``before_message(session_id, user_text)``
- ``after_message(session_id, assistant_text)``
- ``before_tool(session_id, tool_name, arguments)``
- ``after_tool(session_id, tool_name, result)``
- ``on_error(session_id, error)``
- ``on_startup()``
- ``on_shutdown()``
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cogent_constants import HOOKS_DIR

logger = logging.getLogger("cogent.hooks")

# ── Registry ──────────────────────────────────────────────────────────────

HookFn = Callable[..., Any]

_hooks: Dict[str, List[HookFn]] = {
    "before_session_start": [],
    "after_session_end":    [],
    "before_message":       [],
    "after_message":        [],
    "before_tool":          [],
    "after_tool":           [],
    "on_error":             [],
    "on_startup":           [],
    "on_shutdown":          [],
}


# ── Registration ──────────────────────────────────────────────────────────

def register(hook_point: str, fn: HookFn) -> None:
    """Register *fn* to be called at *hook_point*.

    Args:
        hook_point: One of the well-known hook point names.
        fn: Async or sync callable.  Async hooks are awaited; sync hooks
            are run in a thread pool executor.
    """
    if hook_point not in _hooks:
        logger.warning("Unknown hook point: %s", hook_point)
        return
    _hooks[hook_point].append(fn)
    logger.debug("Hook registered: %s -> %s.%s", hook_point,
                 getattr(fn, "__module__", "?"), getattr(fn, "__qualname__", "?"))


def unregister(hook_point: str, fn: HookFn) -> None:
    """Remove a previously registered hook function."""
    if hook_point in _hooks:
        _hooks[hook_point] = [h for h in _hooks[hook_point] if h is not fn]


# ── Execution ─────────────────────────────────────────────────────────────

async def run_hooks(hook_point: str, **kwargs: Any) -> None:
    """Execute all hooks registered at *hook_point*.

    Hooks run in registration order.  Exceptions are logged but do not
    propagate — one failing hook never blocks the rest.
    """
    fns = _hooks.get(hook_point, [])
    if not fns:
        return

    for fn in fns:
        try:
            result = fn(**kwargs)
            if hasattr(result, "__await__"):
                await result
        except Exception:
            logger.exception("Hook %s failed in %s.%s",
                             hook_point,
                             getattr(fn, "__module__", "?"),
                             getattr(fn, "__qualname__", "?"))


# ── Auto-discovery ────────────────────────────────────────────────────────

def discover_and_load() -> int:
    """Scan ``backend/hooks/`` for ``*.hook.py`` files and import them.

    Each file should call :func:`register` at module level.
    Returns the number of hook files loaded.
    """
    hooks_dir = HOOKS_DIR
    if not hooks_dir.is_dir():
        return 0

    count = 0
    for entry in sorted(hooks_dir.iterdir()):
        if entry.suffix == ".py" and entry.stem.endswith("_hook"):
            _load_hook_file(entry)
            count += 1
        elif entry.suffix == ".py" and entry.name != "__init__.py":
            # Also load bare .py files in hooks/ as hook modules
            _load_hook_file(entry)
            count += 1

    if count:
        logger.info("Loaded %d hook file(s) from %s", count, hooks_dir)
    return count


def _load_hook_file(path: Path) -> None:
    """Import a single hook file by path."""
    try:
        spec = importlib.util.spec_from_file_location(
            f"cogent_hooks.{path.stem}", path
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            logger.debug("Loaded hook module: %s", path.name)
    except Exception:
        logger.exception("Failed to load hook module: %s", path.name)
