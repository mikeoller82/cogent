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

tools_stub = types.ModuleType("tools")
tools_stub.tool_specs_for_prompt = lambda: "[]"
sys.modules.setdefault("tools", tools_stub)

import llm_service


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


def run_async(coro):
    return asyncio.run(coro)


async def collect_stream_events():
    events = []
    async for event in llm_service.run_turn_stream(
        db=None,
        session_id="session-1",
        workspace_id="workspace-1",
        user_text="Hello",
        history=[{"role": "assistant", "content": "Previous answer"}],
    ):
        events.append(event)
    return events


@pytest.fixture(autouse=True)
def no_memory(monkeypatch):
    async def fake_load_memory_facts(db, workspace_id):
        return ""

    monkeypatch.setattr(llm_service, "_load_memory_facts", fake_load_memory_facts)


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

    monkeypatch.setattr(llm_service.requests, "post", fake_post)

    content = llm_service._post_kilocode_chat(messages)

    assert captured["url"] == llm_service.KILOCODE_CHAT_COMPLETIONS_URL
    assert captured["headers"]["Authorization"] == "Bearer kilo-test-key"
    assert captured["json"]["model"] == "nex-agi/nex-n2-pro:free"
    assert captured["json"]["max_tokens"] == 4000
    assert captured["json"]["messages"] == messages
    assert content == "Final answer"


def test_final_stream_event_uses_ordered_messages(monkeypatch):
    captured = {}

    async def fake_send(messages):
        captured["messages"] = messages
        return "Final answer"

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)

    events = run_async(collect_stream_events())

    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1] == {"role": "assistant", "content": "Previous answer"}
    assert captured["messages"][2] == {"role": "user", "content": "Hello"}
    assert events[-1] == {"type": "final", "content": "Final answer"}


def test_tool_loop_still_executes_local_tool_and_continues(monkeypatch):
    responses = [
        '<tool>{"name": "recall_memory", "args": {}}</tool>',
        "Done after tool",
    ]
    sent_payloads = []

    async def fake_send(messages):
        sent_payloads.append({"messages": messages})
        return responses.pop(0)

    async def fake_execute_tool(db, workspace_id, call):
        assert call == {"name": "recall_memory", "args": {}}
        return {"result": "remembered fact"}

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)
    monkeypatch.setattr(llm_service, "_execute_tool", fake_execute_tool)

    events = run_async(collect_stream_events())
    event_types = [event["type"] for event in events]

    assert "tool" in event_types
    assert "tool_result" in event_types
    assert events[-1] == {"type": "final", "content": "Done after tool"}
    assert sent_payloads[1]["messages"][-1] == {
        "role": "user",
        "content": "<tool_result>\nremembered fact\n</tool_result>\n\nContinue.",
    }


def test_missing_kilocode_api_key_yields_useful_error(monkeypatch):
    monkeypatch.delenv("KILOCODE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Missing KILOCODE_API_KEY"):
        llm_service._post_kilocode_chat([])


def test_stream_send_error_yields_useful_error(monkeypatch):
    async def fake_send(messages):
        raise RuntimeError("Missing KILOCODE_API_KEY")

    monkeypatch.setattr(llm_service, "_send_kilocode_chat", fake_send)

    events = run_async(collect_stream_events())

    assert events[0] == {"type": "status", "content": "thinking"}
    assert events[1]["type"] == "error"
    assert "Missing KILOCODE_API_KEY" in events[1]["content"]
    assert len(events) == 2


def test_bad_kilocode_response_shape_yields_error(monkeypatch):
    monkeypatch.setenv("KILOCODE_API_KEY", "kilo-test-key")

    def fake_post(url, headers, json, timeout):
        return FakeResponse(data={"choices": []})

    monkeypatch.setattr(llm_service.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match=r"missing choices\[0\].message.content"):
        llm_service._post_kilocode_chat([])
