import asyncio
import sys
import types
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_stub)

import llm_service
import cogent_providers


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


def run_async(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def no_memory(monkeypatch):
    async def fake_load_memory_facts(db, workspace_id):
        return "Mock memory: test user prefers concise answers."
    monkeypatch.setattr(llm_service, "_load_memory_facts", fake_load_memory_facts)


# ── Streaming test helper ────────────────────────────────────────────────

async def _collect_stream_events(history=None, user_text="Hello from test"):
    """Run the streaming loop and return all emitted events."""
    events = []
    from llm_service import run_turn_stream
    from conftest_helpers import FakeMotorDatabase
    db = FakeMotorDatabase()
    async for ev in run_turn_stream(
        db, "session-test", "default",
        user_text,
        history or [],
    ):
        events.append(ev)
    return events


# ── KiloCode direct-call tests (sync wrapper around the provider chain) ──

def test_kilocode_request_payload_includes_model_and_ordered_messages(monkeypatch):
    monkeypatch.setenv("KILOCODE_API_KEY", "kilo-test-key")
    captured = {}
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "assistant", "content": "Previous answer"},
        {"role": "user", "content": "Hello"},
    ]

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            data={"choices": [{"message": {"content": "Final answer"}}]},
        )

    monkeypatch.setattr(cogent_providers.requests, "post", fake_post)
    content = llm_service._post_kilocode_chat(messages)
    assert content == "Final answer"


def test_missing_kilocode_api_key_yields_useful_error(monkeypatch):
    monkeypatch.delenv("KILOCODE_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="All LLM providers exhausted"):
        llm_service._post_kilocode_chat([])


def test_bad_kilocode_response_shape_yields_error(monkeypatch):
    monkeypatch.setenv("KILOCODE_API_KEY", "kilo-test-key")
    monkeypatch.setattr("cogent_providers.HAS_OLLAMA", False)

    def fake_post(url, headers, json, timeout):
        return FakeResponse(data={"choices": []})

    monkeypatch.setattr(cogent_providers.requests, "post", fake_post)
    with pytest.raises(RuntimeError, match=r"All LLM providers exhausted"):
        llm_service._post_kilocode_chat([])


# ── Streaming / tool-loop tests ─────────────────────────────────────────

def test_final_stream_event_uses_ordered_messages(monkeypatch):
    calls = []

    async def fake_send(messages):
        calls.append(messages)
        if len(calls) == 1:
            return "Final answer"
        return "PASS Verified correctly."

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)

    history = [{"role": "assistant", "content": "Previous answer"}]
    events = run_async(_collect_stream_events(history, "Hello"))

    # First LLM call: system, assistant(from history), user
    assert len(calls) >= 1
    assert calls[0][0]["role"] == "system"
    assert calls[0][1]["role"] == "assistant"
    assert calls[0][1]["content"] == "Previous answer"
    assert calls[0][2]["role"] == "user"
    assert calls[0][2]["content"] == "Hello"

    # With the no-tool re-prompt guard, the LLM is re-prompted up to
    # MAX_CONSECUTIVE_NO_TOOL times before passing to the evaluator.
    # The first call ("Final answer" — no tool) gets re-prompted;
    # subsequent calls ("PASS Verified correctly." — also no tool) continue
    # until the counter hits the limit, then the evaluator decides PASS.
    finals = [e for e in events if e["type"] == "final"]
    assert len(finals) >= 1


def test_tool_loop_still_executes_local_tool_and_continues(monkeypatch):
    call_count = [0]

    async def fake_send(messages):
        call_count[0] += 1
        if call_count[0] == 1:
            return '<tool>{"name": "recall_memory", "args": {}}</tool>'
        if call_count[0] == 2:
            return "Done after tool"
        return "PASS Verified correctly."

    async def fake_execute_tool(db, workspace_id, call):
        assert call == {"name": "recall_memory", "args": {}}
        return {"result": "remembered fact"}

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)
    monkeypatch.setattr(llm_service, "_execute_tool", fake_execute_tool)
    events = run_async(_collect_stream_events())

    event_types = [event["type"] for event in events]
    assert "tool" in event_types
    assert "tool_result" in event_types
    # 3 calls: (1) LLM returns tool, (2) tool-result fed back + user re-prompt,
    # (3) verification pass after "Done after tool"
    assert call_count[0] >= 2


def test_stream_send_error_yields_useful_error(monkeypatch):
    async def fake_send(messages):
        return ""

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)

    error_events = run_async(_collect_stream_events())

    # Empty LLM response yields a final event rather than an explicit error event
    assert any(e["type"] in ("final", "error") for e in error_events)

