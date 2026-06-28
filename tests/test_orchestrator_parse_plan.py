import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Stub out heavy dependencies so the module loads without a running server
import types

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_stub)

tools_stub = types.ModuleType("tools")
tools_stub.tool_specs_for_prompt = lambda: "[]"
sys.modules.setdefault("tools", tools_stub)

from subagent.orchestrator import Orchestrator
from subagent.types import DecompositionPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan_json(subtasks: list[dict], *, reasoning: str = "") -> str:
    """Build a raw JSON plan string (no <plan> wrapper)."""
    import json
    return json.dumps({"subtasks": subtasks, "reasoning": reasoning})


def _plan_xml(subtasks: list[dict], *, reasoning: str = "") -> str:
    """Build a <plan>…</plan> wrapped plan string."""
    import json
    inner = json.dumps({"subtasks": subtasks, "reasoning": reasoning})
    return f"<plan>{inner}</plan>"


# ---------------------------------------------------------------------------
# Tests — dependency ref types
# ---------------------------------------------------------------------------

class TestParsePlanDependencyRefs:
    """Ensure _parse_plan handles every numeric/string combo the LLM can emit."""

    def test_integer_deps(self):
        """The actual bug: LLM returns [0, 1] as JSON ints, not strings."""
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff", "dependencies": []},
            {"role": "coder",      "prompt": "build it",  "dependencies": [0]},
            {"role": "validator",  "prompt": "check it",  "dependencies": [0, 1]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert len(result.subtasks) == 3
        # dep on index 0 → should resolve to subtask[0].id
        assert result.subtasks[1].dependencies == [result.subtasks[0].id]
        # deps on 0 and 1 → should resolve to subtask[0].id and subtask[1].id
        assert result.subtasks[2].dependencies == [
            result.subtasks[0].id,
            result.subtasks[1].id,
        ]

    def test_string_deps(self):
        """Legacy format: LLM returns deps as strings ["0", "1"]."""
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff", "dependencies": []},
            {"role": "coder",      "prompt": "build it",  "dependencies": ["0"]},
            {"role": "validator",  "prompt": "check it",  "dependencies": ["0", "1"]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[1].dependencies == [result.subtasks[0].id]
        assert result.subtasks[2].dependencies == [
            result.subtasks[0].id,
            result.subtasks[1].id,
        ]

    def test_mixed_int_and_string_deps(self):
        """LLM is inconsistent — some ints, some strings."""
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff", "dependencies": []},
            {"role": "coder",      "prompt": "build it",  "dependencies": ["0"]},
            {"role": "validator",  "prompt": "check it",  "dependencies": [0, "1"]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[1].dependencies == [result.subtasks[0].id]
        assert result.subtasks[2].dependencies == [
            result.subtasks[0].id,
            result.subtasks[1].id,
        ]

    def test_uuid_deps_passthrough(self):
        """If deps are already UUIDs, they pass through unchanged."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff", "dependencies": []},
            {"role": "coder",      "prompt": "build it",  "dependencies": [fake_uuid]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[1].dependencies == [fake_uuid]

    def test_out_of_range_index_kept_as_is(self):
        """Index >= len(subtasks) is kept as-is (defensive)."""
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff", "dependencies": [99]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        # index 99 is out of range → kept as literal "99"
        assert result.subtasks[0].dependencies == ["99"]

    def test_empty_deps(self):
        """No dependencies at all — should produce empty lists."""
        plan_str = _plan_json([
            {"role": "researcher", "prompt": "find stuff"},
            {"role": "coder",      "prompt": "build it"},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[0].dependencies == []
        assert result.subtasks[1].dependencies == []

    def test_xml_wrapped_plan(self):
        """Plan inside <plan> tags (common LLM output format)."""
        plan_str = _plan_xml([
            {"role": "researcher", "prompt": "find stuff", "dependencies": []},
            {"role": "coder",      "prompt": "build it",  "dependencies": [0]},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[1].dependencies == [result.subtasks[0].id]

    def test_invalid_json_returns_none(self):
        assert Orchestrator._parse_plan("not json at all") is None

    def test_empty_subtasks_returns_none(self):
        import json
        plan_str = json.dumps({"subtasks": []})
        assert Orchestrator._parse_plan(plan_str) is None

    def test_unknown_role_defaults_to_researcher(self):
        """Invalid role string should fall back to RESEARCHER."""
        plan_str = _plan_json([
            {"role": "invalid_role", "prompt": "do something"},
        ])
        result = Orchestrator._parse_plan(plan_str)

        assert result is not None
        assert result.subtasks[0].role.value == "researcher"
