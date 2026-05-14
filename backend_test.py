"""
Comprehensive backend tests for Viktor AI Coworker API
Tests all endpoints including LLM tool-using capabilities
"""
import requests
import time
import json
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://flow-builder-demo-2.preview.emergentagent.com/api"

# Test configuration
TIMEOUT = 180  # Generous timeout for LLM responses
session = requests.Session()

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append(f"✅ {test_name}" + (f": {details}" if details else ""))
        print(f"✅ PASS: {test_name}" + (f" - {details}" if details else ""))
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append(f"❌ {test_name}: {error}")
        print(f"❌ FAIL: {test_name}: {error}")
    
    def add_warning(self, test_name: str, warning: str):
        self.warnings.append(f"⚠️  {test_name}: {warning}")
        print(f"⚠️  WARNING: {test_name}: {warning}")
    
    def summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"\nPassed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.failed:
            print("\n❌ FAILED TESTS:")
            for f in self.failed:
                print(f"  {f}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for w in self.warnings:
                print(f"  {w}")
        
        if self.passed:
            print("\n✅ PASSED TESTS:")
            for p in self.passed:
                print(f"  {p}")
        
        return len(self.failed) == 0

results = TestResults()

def test_health():
    """Test 1: Health check endpoint"""
    try:
        resp = session.get(f"{BASE_URL}/", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("service") == "viktor" and data.get("status") == "ok":
                results.add_pass("Health Check", f"Response: {data}")
            else:
                results.add_fail("Health Check", f"Unexpected response: {data}")
        else:
            results.add_fail("Health Check", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Health Check", str(e))

def test_sessions_crud():
    """Test 2: Sessions CRUD operations"""
    session_id = None
    
    # Create session
    try:
        resp = session.post(f"{BASE_URL}/sessions", json={"title": None}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "id" in data and "title" in data and "created_at" in data:
                session_id = data["id"]
                results.add_pass("Create Session", f"Session ID: {session_id}")
            else:
                results.add_fail("Create Session", f"Missing fields in response: {data}")
                return None
        else:
            results.add_fail("Create Session", f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        results.add_fail("Create Session", str(e))
        return None
    
    # List sessions
    try:
        resp = session.get(f"{BASE_URL}/sessions", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and any(s["id"] == session_id for s in data):
                results.add_pass("List Sessions", f"Found {len(data)} sessions including new one")
            else:
                results.add_fail("List Sessions", "New session not found in list")
        else:
            results.add_fail("List Sessions", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("List Sessions", str(e))
    
    # Delete session (we'll create a new one for chat tests)
    try:
        resp = session.delete(f"{BASE_URL}/sessions/{session_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") == True:
                results.add_pass("Delete Session", f"Deleted session {session_id}")
            else:
                results.add_fail("Delete Session", f"Unexpected response: {data}")
        else:
            results.add_fail("Delete Session", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Delete Session", str(e))
    
    return session_id

def create_test_session() -> Optional[str]:
    """Helper to create a new session for testing"""
    try:
        resp = session.post(f"{BASE_URL}/sessions", json={"title": None}, timeout=10)
        if resp.status_code == 200:
            return resp.json()["id"]
    except:
        pass
    return None

def test_chat_simple():
    """Test 3a: Simple chat without tools"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Simple", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Hi, who are you?"},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            tool_uses = data.get("tool_uses", [])
            
            if content and len(content) > 10:
                results.add_pass("Chat Simple", f"Got response: {content[:100]}...")
            else:
                results.add_fail("Chat Simple", f"Empty or too short response: {content}")
        else:
            results.add_fail("Chat Simple", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Simple", str(e))

def test_chat_memory_save():
    """Test 3b: Memory save via chat"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Memory Save", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Remember this: my company is called Acme Tools and we sell to dentists in the US."},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            tool_uses = data.get("tool_uses", [])
            
            # Check if save_memory tool was used
            has_save_memory = any(t.get("tool") == "save_memory" for t in tool_uses)
            
            if has_save_memory:
                results.add_pass("Chat Memory Save", f"save_memory tool called: {tool_uses}")
                
                # Verify memory was actually saved
                time.sleep(1)
                mem_resp = session.get(f"{BASE_URL}/memory", timeout=10)
                if mem_resp.status_code == 200:
                    memories = mem_resp.json()
                    if len(memories) > 0:
                        results.add_pass("Memory Persistence", f"Found {len(memories)} memory items")
                    else:
                        results.add_fail("Memory Persistence", "No memories found after save")
                else:
                    results.add_fail("Memory Persistence", f"Could not fetch memories: {mem_resp.status_code}")
            else:
                results.add_fail("Chat Memory Save", f"save_memory tool not called. Tool uses: {tool_uses}")
        else:
            results.add_fail("Chat Memory Save", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Memory Save", str(e))

def test_chat_memory_recall():
    """Test 3c: Memory recall in new session"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Memory Recall", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "What do you remember about my company?"},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "").lower()
            tool_uses = data.get("tool_uses", [])
            
            # Check if recall_memory tool was used
            has_recall = any(t.get("tool") == "recall_memory" for t in tool_uses)
            
            # Check if response mentions saved info
            mentions_acme = "acme" in content
            mentions_dentists = "dentist" in content
            
            if has_recall and (mentions_acme or mentions_dentists):
                results.add_pass("Chat Memory Recall", f"Recalled memory correctly: {content[:150]}...")
            elif has_recall:
                results.add_warning("Chat Memory Recall", f"recall_memory called but response doesn't mention saved info: {content[:150]}...")
            else:
                results.add_fail("Chat Memory Recall", f"recall_memory tool not called. Tool uses: {tool_uses}")
        else:
            results.add_fail("Chat Memory Recall", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Memory Recall", str(e))

def test_chat_pdf_generation():
    """Test 3d: PDF generation via chat"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat PDF Generation", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Make me a very short PDF titled 'Test Brief' with one section 'Intro' that just says hello world."},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            tool_uses = data.get("tool_uses", [])
            artifacts = data.get("artifacts", [])
            
            # Check if generate_pdf tool was used
            has_pdf_tool = any(t.get("tool") == "generate_pdf" for t in tool_uses)
            
            # Check if PDF artifact was created
            pdf_artifact = next((a for a in artifacts if a.get("type") == "pdf"), None)
            
            if has_pdf_tool and pdf_artifact:
                pdf_url = pdf_artifact.get("url", "")
                results.add_pass("Chat PDF Generation", f"PDF created: {pdf_url}")
                
                # Try to download the PDF
                if pdf_url:
                    try:
                        download_resp = session.get(f"{BASE_URL.rsplit('/api', 1)[0]}{pdf_url}", timeout=10)
                        if download_resp.status_code == 200:
                            content_type = download_resp.headers.get("content-type", "")
                            if "pdf" in content_type.lower() and len(download_resp.content) > 0:
                                results.add_pass("PDF Download", f"Downloaded {len(download_resp.content)} bytes, type: {content_type}")
                            else:
                                results.add_fail("PDF Download", f"Invalid PDF: type={content_type}, size={len(download_resp.content)}")
                        else:
                            results.add_fail("PDF Download", f"Status {download_resp.status_code}")
                    except Exception as e:
                        results.add_fail("PDF Download", str(e))
            else:
                results.add_fail("Chat PDF Generation", f"PDF not generated. Tools: {tool_uses}, Artifacts: {artifacts}")
        else:
            results.add_fail("Chat PDF Generation", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat PDF Generation", str(e))

def test_chat_web_search():
    """Test 3e: Web search via chat"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Web Search", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Search the web for 'OpenAI latest announcement 2026' and summarize in 2 sentences."},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            tool_uses = data.get("tool_uses", [])
            
            # Check if web_search tool was used
            has_search = any(t.get("tool") == "web_search" for t in tool_uses)
            
            if has_search and content and len(content) > 20:
                results.add_pass("Chat Web Search", f"Search completed: {content[:150]}...")
            elif has_search:
                results.add_warning("Chat Web Search", f"Search tool called but response is short: {content}")
            else:
                results.add_fail("Chat Web Search", f"web_search tool not called. Tool uses: {tool_uses}")
        else:
            results.add_fail("Chat Web Search", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Web Search", str(e))

def test_chat_webapp_generation():
    """Test 3f: Webapp generation via chat"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Webapp Generation", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Build me a tiny single-file HTML webapp: a heading that says 'Hello Viktor' on a dark background. Keep it minimal."},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            tool_uses = data.get("tool_uses", [])
            artifacts = data.get("artifacts", [])
            
            # Check if generate_webapp tool was used
            has_webapp_tool = any(t.get("tool") == "generate_webapp" for t in tool_uses)
            
            # Check if webapp artifact was created
            webapp_artifact = next((a for a in artifacts if a.get("type") == "webapp"), None)
            
            if has_webapp_tool and webapp_artifact:
                webapp_url = webapp_artifact.get("url", "")
                results.add_pass("Chat Webapp Generation", f"Webapp created: {webapp_url}")
                
                # Try to render the webapp
                if webapp_url:
                    try:
                        render_resp = session.get(f"{BASE_URL.rsplit('/api', 1)[0]}{webapp_url}", timeout=10)
                        if render_resp.status_code == 200:
                            content_type = render_resp.headers.get("content-type", "")
                            html_content = render_resp.text
                            if "html" in content_type.lower() and len(html_content) > 0:
                                results.add_pass("Webapp Render", f"Rendered {len(html_content)} chars, type: {content_type}")
                            else:
                                results.add_fail("Webapp Render", f"Invalid HTML: type={content_type}, size={len(html_content)}")
                        else:
                            results.add_fail("Webapp Render", f"Status {render_resp.status_code}")
                    except Exception as e:
                        results.add_fail("Webapp Render", str(e))
            else:
                results.add_fail("Chat Webapp Generation", f"Webapp not generated. Tools: {tool_uses}, Artifacts: {artifacts}")
        else:
            results.add_fail("Chat Webapp Generation", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Webapp Generation", str(e))

def test_chat_schedule_task():
    """Test 3g: Schedule task via chat"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Chat Schedule Task", "Could not create session")
        return
    
    try:
        resp = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "Schedule a task: every Monday at 09:00, run 'audit my Meta Ads spend'."},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            tool_uses = data.get("tool_uses", [])
            artifacts = data.get("artifacts", [])
            
            # Check if schedule_task tool was used
            has_schedule = any(t.get("tool") == "schedule_task" for t in tool_uses)
            
            # Check if schedule artifact was created
            schedule_artifact = next((a for a in artifacts if a.get("type") == "schedule"), None)
            
            if has_schedule and schedule_artifact:
                results.add_pass("Chat Schedule Task", f"Task scheduled: {schedule_artifact}")
                
                # Verify task appears in tasks list
                time.sleep(1)
                tasks_resp = session.get(f"{BASE_URL}/tasks", timeout=10)
                if tasks_resp.status_code == 200:
                    tasks = tasks_resp.json()
                    if len(tasks) > 0:
                        results.add_pass("Task Persistence", f"Found {len(tasks)} scheduled tasks")
                    else:
                        results.add_fail("Task Persistence", "No tasks found after scheduling")
                else:
                    results.add_fail("Task Persistence", f"Could not fetch tasks: {tasks_resp.status_code}")
            else:
                results.add_fail("Chat Schedule Task", f"Task not scheduled. Tools: {tool_uses}, Artifacts: {artifacts}")
        else:
            results.add_fail("Chat Schedule Task", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Chat Schedule Task", str(e))

def test_multi_turn_conversation():
    """Test 4: Multi-turn conversation with history"""
    session_id = create_test_session()
    if not session_id:
        results.add_fail("Multi-turn Conversation", "Could not create session")
        return
    
    try:
        # Turn 1
        resp1 = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "My favorite number is 42."},
            timeout=TIMEOUT
        )
        if resp1.status_code != 200:
            results.add_fail("Multi-turn Conversation", f"Turn 1 failed: {resp1.status_code}")
            return
        
        time.sleep(2)
        
        # Turn 2
        resp2 = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "What's a fun fact about that number?"},
            timeout=TIMEOUT
        )
        if resp2.status_code != 200:
            results.add_fail("Multi-turn Conversation", f"Turn 2 failed: {resp2.status_code}")
            return
        
        time.sleep(2)
        
        # Turn 3 - should reference 42
        resp3 = session.post(
            f"{BASE_URL}/sessions/{session_id}/messages",
            json={"text": "What number did I just tell you?"},
            timeout=TIMEOUT
        )
        if resp3.status_code == 200:
            content = resp3.json().get("content", "").lower()
            if "42" in content or "forty-two" in content or "forty two" in content:
                results.add_pass("Multi-turn Conversation", f"Correctly remembered 42: {content[:150]}...")
            else:
                results.add_fail("Multi-turn Conversation", f"Did not remember 42: {content}")
        else:
            results.add_fail("Multi-turn Conversation", f"Turn 3 failed: {resp3.status_code}")
    except Exception as e:
        results.add_fail("Multi-turn Conversation", str(e))

def test_memory_crud():
    """Test 5: Memory CRUD operations"""
    # Create memory
    try:
        resp = session.post(
            f"{BASE_URL}/memory",
            json={"key": "tone_preference", "value": "casual"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") == True:
                results.add_pass("Memory Create", "Created tone_preference")
            else:
                results.add_fail("Memory Create", f"Unexpected response: {data}")
        else:
            results.add_fail("Memory Create", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Memory Create", str(e))
    
    # Read memory
    try:
        resp = session.get(f"{BASE_URL}/memory", timeout=10)
        if resp.status_code == 200:
            memories = resp.json()
            has_tone = any(m.get("key") == "tone_preference" for m in memories)
            if has_tone:
                results.add_pass("Memory Read", f"Found tone_preference in {len(memories)} memories")
            else:
                results.add_fail("Memory Read", "tone_preference not found in memories")
        else:
            results.add_fail("Memory Read", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Memory Read", str(e))
    
    # Delete memory
    try:
        resp = session.delete(f"{BASE_URL}/memory/tone_preference", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") == True:
                results.add_pass("Memory Delete", "Deleted tone_preference")
            else:
                results.add_fail("Memory Delete", f"Unexpected response: {data}")
        else:
            results.add_fail("Memory Delete", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        results.add_fail("Memory Delete", str(e))

def run_all_tests():
    """Run all tests in sequence"""
    print("="*80)
    print("VIKTOR AI COWORKER BACKEND TESTS")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("="*80 + "\n")
    
    print("Running tests...\n")
    
    # Basic tests
    test_health()
    test_sessions_crud()
    
    # Chat tests with tool use (these are the critical tests)
    print("\n--- CRITICAL LLM + TOOL TESTS ---\n")
    test_chat_simple()
    test_chat_memory_save()
    test_chat_memory_recall()
    test_chat_pdf_generation()
    test_chat_web_search()
    test_chat_webapp_generation()
    test_chat_schedule_task()
    
    # Multi-turn conversation
    print("\n--- CONVERSATION HISTORY TEST ---\n")
    test_multi_turn_conversation()
    
    # Memory CRUD
    print("\n--- MEMORY CRUD TESTS ---\n")
    test_memory_crud()
    
    # Summary
    results.summary()
    
    return results.failed == []

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
