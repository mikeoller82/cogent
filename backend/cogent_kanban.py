"""Kanban-style task management for Cogent.

Analogous to Hermes' `kanban_db.py` — JSON-file-backed task board
with columns, priorities, tags, comments, and lifecycle tracking.

Stored in ``memory/kanban.json``.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import MEMORY_DIR

logger = logging.getLogger("cogent.kanban")

# ── Column definitions ───────────────────────────────────────────────────

COLUMNS = ["backlog", "ready", "in_progress", "review", "done", "archived"]
PRIORITIES = ["critical", "high", "medium", "low", "none"]


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class TaskComment:
    id: str
    author: str = "agent"
    body: str = ""
    created_at: float = 0.0


@dataclass
class TaskEvent:
    type: str = ""            # created, moved, commented, updated, completed
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    timestamp: float = 0.0


@dataclass
class Task:
    id: str
    title: str = ""
    description: str = ""
    column: str = "backlog"
    priority: str = "medium"
    tags: List[str] = field(default_factory=list)
    assignee: str = ""
    parent_id: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: Optional[float] = None
    comments: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)


# ── Kanban board ─────────────────────────────────────────────────────────

_lock = threading.Lock()


def _board_path() -> Path:
    return MEMORY_DIR / "kanban.json"


def _load_board() -> Dict[str, Any]:
    path = _board_path()
    if not path.is_file():
        return {"tasks": {}, "columns": COLUMNS, "updated_at": time.time()}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt kanban.json, starting fresh")
        return {"tasks": {}, "columns": COLUMNS, "updated_at": time.time()}


def _save_board(board: Dict[str, Any]) -> None:
    board["updated_at"] = time.time()
    path = _board_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(board, indent=2, default=str), encoding="utf-8")


# ── Task CRUD ────────────────────────────────────────────────────────────

def create_task(title: str, **kwargs: Any) -> Task:
    """Create a new task and add it to the board."""
    import uuid
    now = time.time()
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        column=kwargs.get("column", "backlog"),
        priority=kwargs.get("priority", "medium"),
        description=kwargs.get("description", ""),
        tags=kwargs.get("tags", []),
        assignee=kwargs.get("assignee", ""),
        parent_id=kwargs.get("parent_id"),
        created_at=now,
        updated_at=now,
    )
    # Initial event
    task.events.append(asdict(TaskEvent(
        type="created", new_value=title, timestamp=now
    )))

    with _lock:
        board = _load_board()
        board.setdefault("tasks", {})[task.id] = asdict(task)
        _save_board(board)

    logger.info("Task created: %s — %s", task.id[:12], title)
    return task


def get_task(task_id: str) -> Optional[Task]:
    with _lock:
        board = _load_board()
        data = board.get("tasks", {}).get(task_id)
    if not data:
        return None
    return Task(**data)


def update_task(task_id: str, **changes: Any) -> bool:
    """Update task fields. Returns True if the task existed."""
    now = time.time()
    with _lock:
        board = _load_board()
        tasks = board.setdefault("tasks", {})
        data = tasks.get(task_id)
        if not data:
            return False

        for key, val in changes.items():
            if key in ("id", "created_at"):
                continue  # immutable
            old = data.get(key)
            data[key] = val
            if old != val:
                data.setdefault("events", []).append(asdict(TaskEvent(
                    type="updated", field=key,
                    old_value=str(old or ""), new_value=str(val or ""),
                    timestamp=now,
                )))
        data["updated_at"] = now
        _save_board(board)
    return True


def move_task(task_id: str, to_column: str) -> bool:
    """Move a task to *to_column*. Returns True if the task existed."""
    if to_column not in COLUMNS:
        logger.warning("Invalid column: %s", to_column)
        return False
    now = time.time()
    with _lock:
        board = _load_board()
        data = board.get("tasks", {}).get(task_id)
        if not data:
            return False
        old_col = data.get("column", "backlog")
        data["column"] = to_column
        data["updated_at"] = now
        if to_column == "done":
            data["completed_at"] = now
        data.setdefault("events", []).append(asdict(TaskEvent(
            type="moved", field="column",
            old_value=old_col, new_value=to_column, timestamp=now,
        )))
        _save_board(board)
    logger.info("Task %s moved: %s → %s", task_id[:12], old_col, to_column)
    return True


def add_comment(task_id: str, body: str, author: str = "agent") -> bool:
    import uuid
    now = time.time()
    with _lock:
        board = _load_board()
        data = board.get("tasks", {}).get(task_id)
        if not data:
            return False
        comment = asdict(TaskComment(
            id=str(uuid.uuid4())[:12], author=author,
            body=body, created_at=now,
        ))
        data.setdefault("comments", []).append(comment)
        data.setdefault("events", []).append(asdict(TaskEvent(
            type="commented", new_value=f"{author}: {body[:60]}", timestamp=now,
        )))
        data["updated_at"] = now
        _save_board(board)
    return True


def delete_task(task_id: str) -> bool:
    with _lock:
        board = _load_board()
        tasks = board.get("tasks", {})
        if task_id not in tasks:
            return False
        del tasks[task_id]
        _save_board(board)
    logger.info("Task deleted: %s", task_id[:12])
    return True


# ── Query ────────────────────────────────────────────────────────────────

def list_tasks(column: Optional[str] = None,
               tag: Optional[str] = None,
               priority: Optional[str] = None,
               limit: int = 100) -> List[Task]:
    """List tasks with optional filters."""
    with _lock:
        board = _load_board()
        tasks_data = board.get("tasks", {}).values()

    tasks = [Task(**d) for d in tasks_data]

    if column:
        tasks = [t for t in tasks if t.column == column]
    if tag:
        tasks = [t for t in tasks if tag in t.tags]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    tasks.sort(key=lambda t: t.updated_at, reverse=True)
    return tasks[:limit]


def task_count(column: Optional[str] = None) -> int:
    with _lock:
        board = _load_board()
        tasks = board.get("tasks", {}).values()
    if column:
        return sum(1 for d in tasks if d.get("column") == column)
    return len(tasks)


def decompose_task(task_id: str, subtasks: List[Dict[str, str]]) -> List[Task]:
    """Split a task into subtasks. Returns the created subtasks."""
    created = []
    for st in subtasks:
        t = create_task(
            title=st.get("title", "Subtask"),
            description=st.get("description", ""),
            column="backlog",
            priority=st.get("priority", "medium"),
            parent_id=task_id,
        )
        created.append(t)
    return created


# ── Prompt integration ───────────────────────────────────────────────────

def kanban_summary() -> str:
    """Return a summary of the kanban board for the system prompt."""
    with _lock:
        board = _load_board()
        tasks = board.get("tasks", {})

    by_col: Dict[str, int] = {}
    for data in tasks.values():
        col = data.get("column", "backlog")
        by_col[col] = by_col.get(col, 0) + 1

    lines = [f"## Task Board ({sum(by_col.values())} total)"]
    for col in COLUMNS:
        count = by_col.get(col, 0)
        if count:
            lines.append(f"- {col}: {count}")
    return "\n".join(lines)
