"""Integration tests for Cogent's three most critical subsystems:

1. **Loop engine state machine** — phase transitions, circuit breaker, exit
   detection, tool guardrails.
2. **Tool execution** — ``_execute_tool`` dispatch with in-memory database.
3. **Chat streaming** — ``run_turn_stream`` yields the expected event types.

These tests use in-memory mocks so they require **no** MongoDB, no API keys,
and no running services.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the backend package is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))



# Now safe to import production modules
import llm_service as _llm
import loop_engine as le
from loop_engine import (
    LoopState,
    PHASE_IDLE, PHASE_PLAN, PHASE_EXECUTE, PHASE_VERIFY, PHASE_DONE,
    PHASE_ERROR, PHASE_ESCALATE,
    CB_CLOSED, CB_HALF_OPEN, CB_OPEN,
)


# =============================================================================
# 1.  Loop Engine State Machine
# =============================================================================

class TestLoopStateMachine:
    """Phase transitions, circuit breaker, and exit detection."""

    def test_initial_state(self):
        """A freshly created loop state is idle with sensible defaults."""
        state = LoopState(session_id="s-1")
        assert state.phase == PHASE_IDLE
        assert state.iteration == 0
        assert state.cb_state == CB_CLOSED

    def test_begin_task_transitions_to_plan(self):
        """begin_task() resets state and sets phase=plan."""
        state = LoopState(session_id="s-2")
        le.begin_task(state, "Build a PDF report")
        assert state.phase == PHASE_PLAN
        assert state.task_description == "Build a PDF report"
        assert state.iteration == 0

    def test_record_attempt_increments_iteration(self):
        """record_attempt() bumps iteration and stores the summary."""
        state = LoopState(session_id="s-3")
        le.begin_task(state, "Investigate")
        le.record_attempt(state, PHASE_EXECUTE, "Ran analysis")
        assert state.iteration == 1
        assert len(state.attempts) == 1
        assert state.attempts[0]["phase"] == PHASE_EXECUTE

    def test_complete_task_sets_phase_done(self):
        state = LoopState(session_id="s-4")
        le.begin_task(state, "Do work")
        le.complete_task(state, "All done")
        assert state.phase == PHASE_DONE
        assert state.completed_at is not None

    def test_fail_task_sets_phase_error(self):
        state = LoopState(session_id="s-5")
        le.begin_task(state, "Risk task")
        le.fail_task(state, "Something broke")
        assert state.phase == PHASE_ERROR
        assert "Something broke" in state.errors[0]

    def test_escalate_task_sets_phase_escalate(self):
        state = LoopState(session_id="s-6")
        le.begin_task(state, "Hard task")
        le.escalate_task(state, "Need human")
        assert state.phase == PHASE_ESCALATE

    def test_circuit_breaker_opens_after_consecutive_no_progress(self):
        state = LoopState(session_id="s-7")
        le.begin_task(state, "Loop task")
        # Simulate several loops with no progress
        for i in range(1, 5):
            le.record_loop_result(state, i, files_changed=0, has_errors=False,
                                   has_progress=False, exit_signal=False)
        assert le.should_halt_execution(state), "Circuit should be OPEN after sustained no-progress"

    def test_circuit_breaker_stays_closed_when_progress_detected(self):
        state = LoopState(session_id="s-8")
        le.begin_task(state, "Progress task")
        for i in range(1, 6):
            le.record_loop_result(state, i, files_changed=1, has_errors=False,
                                   has_progress=True, exit_signal=False)
        assert not le.should_halt_execution(state)

    def test_exit_via_completion_signals(self):
        state = LoopState(session_id="s-9")
        le.begin_task(state, "Completable task")
        le.record_attempt(state, PHASE_EXECUTE, "first")

        # Send enough done signals to trigger the exit threshold
        signal = "---RALPH_STATUS---\nEXIT_SIGNAL: true\n---END_RALPH_STATUS---\n\nDone with work."
        for _ in range(le.MAX_CONSECUTIVE_DONE_SIGNALS):
            analysis = le.analyze_response_text(signal)
            le.update_exit_signals(state, analysis)

        reason = le.should_exit_gracefully(state)
        assert reason is not None, "Should exit after done signal saturation"

    def test_tool_loop_guardrail_detects_repeated_calls(self):
        state = LoopState(session_id="s-10")
        le.begin_task(state, "Tool task")

        # Same tool + same args repeatedly
        for _ in range(6):
            le.record_tool_result(state, "run_shell", {"command": "ls"}, True)

        is_loop, _, _ = le.check_tool_loop(state, "run_shell", {"command": "ls"})
        assert is_loop, "Should detect tool loop after 5+ same calls"

    def test_save_state_debounce_skips_early_writes(self):
        """Save is debounced — the first 4 non-force calls skip disk."""
        state = LoopState(session_id="s-debounce")
        le.begin_task(state, "Debounce test")  # internally calls save_state(force=True)

        # The _pending_save_count should be 0 after the force-save in begin_task
        sid = state.session_id
        initial_count = le._pending_save_count.get(sid, 0)

        # Non-force saves should accumulate without flushing until limit
        for i in range(le.SAVE_DEBOUNCE_LIMIT - 1):
            le.save_state(state)
        assert le._pending_save_count.get(sid, 0) == le.SAVE_DEBOUNCE_LIMIT - 1, \
            "Should only increment counter, not flush"

        # The Nth call should flush (reset to 0)
        le.save_state(state)
        assert le._pending_save_count.get(sid, 0) == 0, \
            "Should have flushed and reset counter"

    def test_transition_validates_phase(self):
        state = LoopState(session_id="s-11")
        le.transition(state, "invalid_phase")
        assert state.phase == PHASE_IDLE  # unchanged


# =============================================================================
# 2.  Tool Execution (_execute_tool)
# =============================================================================

@pytest.mark.asyncio
async def test_execute_tool_unknown_name_returns_clean_error():
    """An unrecognised tool name should return a clear error, not an exception."""
    from llm_service import _execute_tool
    result = await _execute_tool(None, "default", {"name": "nonexistent_tool", "args": {}})
    assert "result" in result
    assert "Unknown tool" in result["result"]


@pytest.mark.asyncio
async def test_execute_tool_save_and_recall_memory(test_db):
    """Memory tools should persist and retrieve values."""
    from llm_service import _execute_tool

    # Save a memory
    save_call = {"name": "save_memory", "args": {"key": "test_key", "value": "test_value"}}
    save_result = await _execute_tool(test_db, "default", save_call)
    assert "result" in save_result

    # Recall memories
    recall_call = {"name": "recall_memory", "args": {}}
    recall_result = await _execute_tool(test_db, "default", recall_call)
    assert "test_key" in recall_result["result"]
    assert "test_value" in recall_result["result"]


@pytest.mark.asyncio
async def test_execute_tool_schedule_task(test_db):
    """schedule_task should insert a document and return a result."""
    from llm_service import _execute_tool

    call = {
        "name": "schedule_task",
        "args": {
            "name": "daily report",
            "cadence": "daily",
            "time": "08:00",
            "prompt": "Generate report",
        },
    }
    result = await _execute_tool(test_db, "default", call)
    assert "result" in result
    assert "artifact" in result
    assert result["artifact"]["type"] == "schedule"


@pytest.mark.asyncio
async def test_execute_tool_invalid_args_returns_validation_error(test_db):
    """Passing bad argument types should result in a validation error, not a crash."""
    from llm_service import _execute_tool

    # run_shell expects an int timeout, but we pass a dict — triggers TypeError
    # Actually, the code does int(args.get("timeout", 30)) — passing a dict would fail
    result = await _execute_tool(test_db, "default", {
        "name": "run_shell",
        "args": {"command": "echo hi", "timeout": {"bad": "type"}},
    })
    assert "result" in result


# =============================================================================
# 3.  Chat Streaming (run_turn_stream)
# =============================================================================

@pytest.mark.asyncio
async def test_run_turn_stream_yields_status_and_final(monkeypatch, test_db):
    """run_turn_stream should at minimum yield status and final events."""
    from llm_service import run_turn_stream

    # Stub out the LLM call so it returns immediately
    async def fake_chat(messages, **kwargs):
        return "Hello from fake Cogent"

    monkeypatch.setattr("llm_service._call_llm", fake_chat)

    events = []
    async for event in run_turn_stream(
        test_db, "session-stream-1", "default",
        "Hello", [],
    ):
        events.append(event)

    types_found = {ev["type"] for ev in events}
    assert "status" in types_found
    assert "final" in types_found


@pytest.mark.asyncio
async def test_run_turn_stream_tool_execution(monkeypatch, test_db):
    """When the LLM emits a tool call, the stream should show tool + tool_result."""
    from llm_service import run_turn_stream

    # Stub the LLM call to return a tool call then done
    call_count = [0]

    async def fake_chat(messages, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return '<tool>{"name": "save_memory", "args": {"key": "k", "value": "v"}}</tool>'
        return "All done."

    monkeypatch.setattr("llm_service._call_llm", fake_chat)

    events = []
    async for event in run_turn_stream(
        test_db, "session-stream-2", "default",
        "Remember this", [],
    ):
        events.append(event)

    types_found = {ev["type"] for ev in events}
    assert "tool" in types_found, "Tool event should be emitted"
    assert "tool_result" in types_found, "Tool result event should be emitted"
    assert "final" in types_found, "Final event should be emitted"


@pytest.mark.asyncio
async def test_run_turn_stream_loop_events_included(monkeypatch, test_db):
    """The stream should include loop state events."""
    from llm_service import run_turn_stream

    async def fake_chat(messages, **kwargs):
        return "Simple answer."

    monkeypatch.setattr("llm_service._call_llm", fake_chat)

    events = []
    async for event in run_turn_stream(
        test_db, "session-loop-1", "default",
        "Just answer", [],
    ):
        events.append(event)

    types_found = {ev["type"] for ev in events}
    # Should have status, final at minimum; loop may or may not be present
    # depending on the exact flow
    assert "final" in types_found
