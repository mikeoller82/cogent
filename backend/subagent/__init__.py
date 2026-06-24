"""Dynamic subagent orchestration for Cogent.

Orchestrator → planning pass → agent factory → concurrent execution → aggregation.
"""

from .types import (
    SubagentRole, SubagentStatus, SubtaskSpec, SubagentSpec,
    SubagentResult, DecompositionPlan,
)
from .task_graph import TaskGraph
from .agent_factory import AgentFactory
from .subagent import Subagent
from .orchestrator import Orchestrator

__all__ = [
    "SubagentRole", "SubagentStatus", "SubtaskSpec", "SubagentSpec",
    "SubagentResult", "DecompositionPlan",
    "TaskGraph", "AgentFactory", "Subagent", "Orchestrator",
]
