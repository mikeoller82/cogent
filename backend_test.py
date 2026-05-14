#!/usr/bin/env python3
"""
Backend test suite for NEW Viktor features:
1. Streaming chat endpoint (SSE)
2. File upload + use in chat
3. Manual task run trigger
4. Task deletion
"""
import httpx
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://flow-builder-demo-2.preview.emergentagent.com/api"
TIMEOUT = 180.0

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def test_streaming_chat_simple():
    """Test 1: Streaming chat with simple question (no tools)"""
    log("=" * 60)
    log("TEST 1: Streaming chat - simple question")
    log("=" * 60)
    
    # Create session
    resp = httpx.post(f"{BASE_URL}/sessions", json={"title": "Stream Test Simple"}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to create session: {resp.text}"
    session = resp.json()
    session_id = session["id"]
    log(f"✓ Created session: {session_id}")
    
    # Send streaming request
    payload = {"text": "What's 2+2? Answer in one short sentence.", "attachments": []}
    
    with httpx.stream("POST", f"{BASE_URL}/sessions/{session_id}/messages/stream", 
                      json=payload, timeout=TIMEOUT) as stream_resp:
        assert stream_resp.status_code == 200, f"Stream failed: {stream_resp.status_code}"
        
        events = []
        buffer = ""
        for chunk in stream_resp.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)
                if event_block.startswith("data: "):
                    data_str = event_block[6:]
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        log(f"  Event: {event.get('type', 'unknown')}")
                    except json.JSONDecodeError as e:
                        log(f"  ⚠ JSON decode error: {e} | data: {data_str[:100]}")
    
    # Verify event sequence
    event_types = [e.get("type") for e in events]
    log(f"Event sequence: {event_types}")
    
    assert "user_saved" in event_types, "Missing user_saved event"
    assert "status" in event_types, "Missing status event"
    assert "final" in event_types, "Missing final event"
    assert "done" in event_types, "Missing done event"
    
    # Verify user_saved event structure
    user_saved = next(e for e in events if e.get("type") == "user_saved")
    assert "message" in user_saved, "user_saved missing message"
    assert "assistant_id" in user_saved, "user_saved missing assistant_id"
    log(f"✓ user_saved event: message_id={user_saved['message']['id']}, assistant_id={user_saved['assistant_id']}")
    
    # Verify final event has content
    final_event = next(e for e in events if e.get("type") == "final")
    assert "content" in final_event and final_event["content"], "final event missing content"
    log(f"✓ Final content: {final_event['content'][:80]}...")
    
    # Verify done event has persisted message
    done_event = next(e for e in events if e.get("type") == "done")
    assert "message" in done_event, "done event missing message"
    assert done_event["message"]["role"] == "assistant", "done message not assistant"
    log(f"✓ Done event: assistant message persisted with id={done_event['message']['id']}")
    
    # Verify messages are persisted
    resp = httpx.get(f"{BASE_URL}/sessions/{session_id}/messages", timeout=TIMEOUT)
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 2, f"Expected at least 2 messages, got {len(messages)}"
    assert messages[0]["role"] == "user", "First message should be user"
    assert messages[1]["role"] == "assistant", "Second message should be assistant"
    log(f"✓ Messages persisted: {len(messages)} messages in session")
    
    log("✅ TEST 1 PASSED: Streaming chat simple\n")
    return session_id


def test_streaming_chat_with_tool():
    """Test 2: Streaming chat with tool call (web_search)"""
    log("=" * 60)
    log("TEST 2: Streaming chat - with tool call")
    log("=" * 60)
    
    # Create session
    resp = httpx.post(f"{BASE_URL}/sessions", json={"title": "Stream Test Tool"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]
    log(f"✓ Created session: {session_id}")
    
    # Send streaming request with tool-triggering prompt
    payload = {"text": "Search the web for 'python 3.13 release date' and tell me in one sentence.", "attachments": []}
    
    with httpx.stream("POST", f"{BASE_URL}/sessions/{session_id}/messages/stream", 
                      json=payload, timeout=TIMEOUT) as stream_resp:
        assert stream_resp.status_code == 200
        
        events = []
        buffer = ""
        for chunk in stream_resp.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)
                if event_block.startswith("data: "):
                    data_str = event_block[6:]
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        log(f"  Event: {event.get('type', 'unknown')}")
                    except json.JSONDecodeError as e:
                        log(f"  ⚠ JSON decode error: {e}")
    
    event_types = [e.get("type") for e in events]
    log(f"Event sequence: {event_types}")
    
    # Verify tool events
    assert "tool" in event_types, "Missing tool event"
    assert "tool_result" in event_types, "Missing tool_result event"
    assert "final" in event_types, "Missing final event"
    assert "done" in event_types, "Missing done event"
    
    # Verify tool event structure
    tool_event = next(e for e in events if e.get("type") == "tool")
    assert "data" in tool_event, "tool event missing data"
    assert tool_event["data"].get("tool") == "web_search", f"Expected web_search, got {tool_event['data'].get('tool')}"
    log(f"✓ Tool event: tool=web_search, args={tool_event['data'].get('args', {})}")
    
    # Verify tool_result event
    tool_result_event = next(e for e in events if e.get("type") == "tool_result")
    assert "data" in tool_result_event, "tool_result event missing data"
    log(f"✓ Tool result event: summary={tool_result_event['data'].get('summary', '')[:60]}...")
    
    log("✅ TEST 2 PASSED: Streaming chat with tool\n")
    return session_id


def test_file_upload_txt():
    """Test 3: File upload - text file"""
    log("=" * 60)
    log("TEST 3: File upload - text file")
    log("=" * 60)
    
    # Create test file
    test_content = "The secret code is RAVEN-42. Remember this."
    test_file = Path("/tmp/test_secret.txt")
    test_file.write_text(test_content)
    
    # Upload file
    with open(test_file, "rb") as f:
        files = {"file": ("test_secret.txt", f, "text/plain")}
        resp = httpx.post(f"{BASE_URL}/uploads", files=files, timeout=TIMEOUT)
    
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    upload_data = resp.json()
    assert "id" in upload_data, "Upload response missing id"
    assert "filename" in upload_data, "Upload response missing filename"
    assert "size" in upload_data, "Upload response missing size"
    log(f"✓ File uploaded: id={upload_data['id']}, filename={upload_data['filename']}, size={upload_data['size']}")
    
    # Create session and use file in chat
    resp = httpx.post(f"{BASE_URL}/sessions", json={"title": "File Test TXT"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]
    log(f"✓ Created session: {session_id}")
    
    # Send message with attachment (non-streaming for simplicity)
    payload = {
        "text": "What's in the file?",
        "attachments": [{"id": upload_data["id"], "filename": upload_data["filename"], "size": upload_data["size"]}]
    }
    resp = httpx.post(f"{BASE_URL}/sessions/{session_id}/messages", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Message with attachment failed: {resp.text}"
    message = resp.json()
    
    # Verify response mentions the secret code
    content = message["content"].upper()
    assert "RAVEN" in content or "42" in content, f"Response doesn't mention secret code: {message['content']}"
    log(f"✓ Assistant response mentions secret code: {message['content'][:100]}...")
    
    log("✅ TEST 3 PASSED: File upload text\n")
    return upload_data["id"]


def test_file_upload_csv():
    """Test 4: File upload - CSV file"""
    log("=" * 60)
    log("TEST 4: File upload - CSV file")
    log("=" * 60)
    
    # Create test CSV
    csv_content = "name,score\nalice,99\nbob,87"
    test_file = Path("/tmp/test_scores.csv")
    test_file.write_text(csv_content)
    
    # Upload file
    with open(test_file, "rb") as f:
        files = {"file": ("test_scores.csv", f, "text/csv")}
        resp = httpx.post(f"{BASE_URL}/uploads", files=files, timeout=TIMEOUT)
    
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    upload_data = resp.json()
    log(f"✓ CSV uploaded: id={upload_data['id']}, size={upload_data['size']}")
    
    # Create session and ask about CSV content
    resp = httpx.post(f"{BASE_URL}/sessions", json={"title": "File Test CSV"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]
    
    payload = {
        "text": "What's bob's score?",
        "attachments": [{"id": upload_data["id"], "filename": upload_data["filename"], "size": upload_data["size"]}]
    }
    resp = httpx.post(f"{BASE_URL}/sessions/{session_id}/messages", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200
    message = resp.json()
    
    # Verify response mentions 87
    content = message["content"]
    assert "87" in content, f"Response doesn't mention bob's score (87): {content}"
    log(f"✓ Assistant correctly identified bob's score: {content[:100]}...")
    
    log("✅ TEST 4 PASSED: File upload CSV\n")
    return upload_data["id"]


def test_manual_task_run():
    """Test 5: Manual task run trigger"""
    log("=" * 60)
    log("TEST 5: Manual task run trigger")
    log("=" * 60)
    
    # Create session and schedule a task via LLM
    resp = httpx.post(f"{BASE_URL}/sessions", json={"title": "Task Schedule Test"}, timeout=TIMEOUT)
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]
    log(f"✓ Created session: {session_id}")
    
    # Ask LLM to schedule a task
    payload = {
        "text": "Schedule a quick task: every Monday at 09:00, summarize today's tech news. Name it 'Daily Tech Digest'.",
        "attachments": []
    }
    resp = httpx.post(f"{BASE_URL}/sessions/{session_id}/messages", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to schedule task: {resp.text}"
    message = resp.json()
    
    # Extract task_id from artifacts
    artifacts = message.get("artifacts", [])
    assert len(artifacts) > 0, "No artifacts returned from schedule_task"
    task_artifact = next((a for a in artifacts if a.get("type") == "schedule"), None)
    assert task_artifact, f"No schedule artifact found in: {artifacts}"
    task_id = task_artifact.get("id")
    assert task_id, "Task artifact missing id"
    log(f"✓ Task scheduled: id={task_id}, name={task_artifact.get('name')}")
    
    # Verify task exists in /api/tasks
    resp = httpx.get(f"{BASE_URL}/tasks", timeout=TIMEOUT)
    assert resp.status_code == 200
    tasks = resp.json()
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task, f"Task {task_id} not found in tasks list"
    log(f"✓ Task found in list: {task['name']}, status={task['status']}")
    
    # Trigger manual run
    resp = httpx.post(f"{BASE_URL}/tasks/{task_id}/run", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Manual run failed: {resp.text}"
    run_result = resp.json()
    assert run_result.get("ok") == True, f"Run result not ok: {run_result}"
    log(f"✓ Manual run triggered: {run_result}")
    
    # Wait for task to complete
    log("⏳ Waiting 60 seconds for task to complete...")
    time.sleep(60)
    
    # Check task was updated
    resp = httpx.get(f"{BASE_URL}/tasks", timeout=TIMEOUT)
    assert resp.status_code == 200
    tasks = resp.json()
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task, "Task disappeared after run"
    
    last_run = task.get("last_run")
    last_session_id = task.get("last_session_id")
    assert last_run is not None, "last_run not set after manual trigger"
    assert last_session_id is not None, "last_session_id not set after manual trigger"
    log(f"✓ Task updated: last_run={last_run}, last_session_id={last_session_id}")
    
    # Verify session was created
    resp = httpx.get(f"{BASE_URL}/sessions", timeout=TIMEOUT)
    assert resp.status_code == 200
    sessions = resp.json()
    run_session = next((s for s in sessions if s["id"] == last_session_id), None)
    assert run_session, f"Run session {last_session_id} not found"
    assert run_session["title"].startswith("⏰"), f"Session title doesn't start with ⏰: {run_session['title']}"
    log(f"✓ Run session created: {run_session['title']}")
    
    # Verify messages in run session
    resp = httpx.get(f"{BASE_URL}/sessions/{last_session_id}/messages", timeout=TIMEOUT)
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 2, f"Expected at least 2 messages (user + assistant), got {len(messages)}"
    assert messages[0]["role"] == "user", "First message should be user"
    assert messages[1]["role"] == "assistant", "Second message should be assistant"
    log(f"✓ Run session has {len(messages)} messages (user + assistant)")
    
    log("✅ TEST 5 PASSED: Manual task run\n")
    return task_id


def test_delete_task(task_id):
    """Test 6: Delete task"""
    log("=" * 60)
    log("TEST 6: Delete task")
    log("=" * 60)
    
    # Delete task
    resp = httpx.delete(f"{BASE_URL}/tasks/{task_id}", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Delete failed: {resp.text}"
    result = resp.json()
    assert result.get("ok") == True, f"Delete result not ok: {result}"
    log(f"✓ Task deleted: {task_id}")
    
    # Verify task is gone
    resp = httpx.get(f"{BASE_URL}/tasks", timeout=TIMEOUT)
    assert resp.status_code == 200
    tasks = resp.json()
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is None, f"Task {task_id} still exists after deletion"
    log(f"✓ Task removed from list")
    
    log("✅ TEST 6 PASSED: Delete task\n")


def main():
    log("🚀 Starting NEW Viktor backend feature tests")
    log(f"Base URL: {BASE_URL}")
    log("")
    
    try:
        # Test streaming
        test_streaming_chat_simple()
        test_streaming_chat_with_tool()
        
        # Test file uploads
        test_file_upload_txt()
        test_file_upload_csv()
        
        # Test task management
        task_id = test_manual_task_run()
        test_delete_task(task_id)
        
        log("=" * 60)
        log("🎉 ALL TESTS PASSED!")
        log("=" * 60)
        
    except AssertionError as e:
        log(f"❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        log(f"❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
