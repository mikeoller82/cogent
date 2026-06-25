"""Live task graph — DAG tracking spawned subagents, their status, and dependencies."""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional

from .types import SubagentRole, SubagentStatus, SubtaskSpec, SubagentResult

logger = logging.getLogger("cogent.subagent.task_graph")


class TaskGraphNode:
    """One node in the subagent task graph."""

    def __init__(self, spec: SubtaskSpec) -> None:
        self.id: str = spec.id
        self.role: SubagentRole = spec.role
        self.spec: SubtaskSpec = spec
        self.status: SubagentStatus = SubagentStatus.PENDING
        self.result: Optional[SubagentResult] = None
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.dependencies: List[str] = list(spec.dependencies)

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "elapsed": round(self.elapsed, 2),
        }


class TaskGraph:
    """Directed acyclic graph of subagent tasks.

    The orchestrator uses the graph to decide which agents are ready to
    spawn in each wave (all dependencies must be COMPLETED before a node
    becomes ready).
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, TaskGraphNode] = {}

    def add_node(self, spec: SubtaskSpec) -> TaskGraphNode:
        node = TaskGraphNode(spec)
        self._nodes[node.id] = node
        return node

    def get_node(self, node_id: str) -> Optional[TaskGraphNode]:
        return self._nodes.get(node_id)

    def update_status(self, node_id: str, status: SubagentStatus,
                      result: Optional[SubagentResult] = None,
                      error: Optional[str] = None) -> None:
        node = self._nodes.get(node_id)
        if node is None:
            logger.warning("TaskGraph: unknown node %s", node_id)
            return
        node.status = status
        if status == SubagentStatus.RUNNING:
            node.started_at = time.time()
        elif status in (SubagentStatus.COMPLETED, SubagentStatus.FAILED,
                        SubagentStatus.SKIPPED):
            node.completed_at = time.time()
        if result is not None:
            node.result = result
        if error is not None:
            node.error = error

    def get_ready_nodes(self) -> List[TaskGraphNode]:
        """Return nodes whose dependencies are all satisfied.

        A dependency is satisfied if it has reached a terminal state
        (COMPLETED, FAILED, or SKIPPED).  This prevents the graph from
        stalling when a dependency fails — downstream agents can still
        run and adapt to partial results.
        """
        terminal = {
            SubagentStatus.COMPLETED,
            SubagentStatus.FAILED,
            SubagentStatus.SKIPPED,
        }
        ready: List[TaskGraphNode] = []
        for node in self._nodes.values():
            if node.status != SubagentStatus.PENDING:
                continue
            deps_met = all(
                self._nodes.get(dep) is not None
                and self._nodes[dep].status in terminal
                for dep in node.dependencies
            )
            if deps_met:
                ready.append(node)
        return ready

    @property
    def all_done(self) -> bool:
        if not self._nodes:
            return False
        return all(
            n.status in (SubagentStatus.COMPLETED, SubagentStatus.FAILED,
                         SubagentStatus.SKIPPED)
            for n in self._nodes.values()
        )

    @property
    def failures(self) -> List[TaskGraphNode]:
        return [n for n in self._nodes.values() if n.status == SubagentStatus.FAILED]

    @property
    def succeeded(self) -> List[TaskGraphNode]:
        return [n for n in self._nodes.values() if n.status == SubagentStatus.COMPLETED]

    @property
    def running_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.status == SubagentStatus.RUNNING)

    def to_dict(self) -> dict:
        return {nid: node.to_dict() for nid, node in self._nodes.items()}
