from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Request, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import uuid
import json
import logging
import asyncio
import time
from contextlib import asynccontextmanager

from cogent_constants import (
    DEFAULT_WORKSPACE,
    ENV_MONGO_URL,
    ENV_DB_NAME,
    ensure_dirs,
)
import cogent_auth
from cogent_logging import setup_logging, set_session_context
from cogent_config import get_config
from cogent_state import create_session, touch_session, list_sessions
from cogent_hooks import discover_and_load, run_hooks

# Import new auth
from cogent_auth_v2 import (
    UserCreate, UserLogin, Token, RefreshTokenRequest,
    UserResponse,
    create_user, authenticate_user, get_current_user, get_current_user_optional,
    get_user_by_id, get_user_workspace, ensure_user_workspace,
    create_tokens, refresh_access_token,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from cogent_providers import get_provider
from llm_service import run_turn, run_turn_stream
from tools import ARTIFACTS_DIR
from file_extract import extract_text_from_file
import scheduler as sched
import skill_forge as skf
import loop_engine as le
import mcp_registry as mcp_reg
from cogent_db_init import create_indexes

cfg = get_config()
setup_logging(level=cfg.log_level, log_dir=cfg.log_dir or None)
logger = logging.getLogger("cogent.server")

mongo_url = os.environ.get("MONGO_URL", cfg.mongo_url or "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", cfg.db_name or "cogent")
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

UPLOADS_DIR = ROOT_DIR / "uploads"

app = FastAPI(title="Cogent API", version="0.1.0")
api = APIRouter(prefix="/api")

# ─── Request ID Middleware ───
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{time.time() - start_time:.3f}"
    return response

# ─── Rate Limiting ───
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}
    
    async def check(self, key: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        if key not in self.requests:
            self.requests[key] = []
        self.requests[key] = [t for t in self.requests[key] if t > minute_ago]
        if len(self.requests[key]) >= self.requests_per_minute:
            return False
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter(requests_per_minute=100)

async def rate_limit_check(request: Request):
    # Skip rate limiting for health checks
    if request.url.path in ["/api/health", "/api/health/ready", "/api/health/live"]:
        return
    # Use user ID if authenticated, otherwise IP
    if hasattr(request.state, "user") and request.state.user:
        key = f"user:{request.state.user['id']}"
    else:
        client = request.client
        key = f"ip:{client.host if client else 'unknown'}"
    
    if not await rate_limiter.check(key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down."
        )

# ─── Models ───
class CreateSessionBody(BaseModel):
    title: Optional[str] = None

class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    workspace_id: str

class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    tool_uses: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []
    created_at: datetime

class Attachment(BaseModel):
    id: str
    filename: str
    size: int

class SendMessageBody(BaseModel):
    text: str
    attachments: List[Attachment] = []

class MemoryItem(BaseModel):
    key: str
    value: str

class ScheduledTaskOut(BaseModel):
    id: str
    name: str
    cadence: str
    time: str
    prompt: str
    status: str
    created_at: datetime
    last_run: Optional[datetime] = None
    last_session_id: Optional[str] = None

class CredentialBody(BaseModel):
    api_key: str

class CredentialOut(BaseModel):
    service: str
    has_key: bool
    key_preview: str

# MCP Models
class MCPInstallBody(BaseModel):
    server_id: str
    registry_entry: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    skip_install: bool = False

class MCPRemoveBody(BaseModel):
    name: str

class MCPConfigBody(BaseModel):
    name: str
    config: Dict[str, Any]

class MCPCallBody(BaseModel):
    server: str
    tool: str
    args: Dict[str, Any] = {}

# ─── Helpers ───

def _doc_to_session(d: dict) -> dict:
    return {
        "id": d["id"],
        "title": d.get("title", "New chat"),
        "created_at": d["created_at"],
        "updated_at": d.get("updated_at", d["created_at"]),
        "workspace_id": d.get("workspace_id", DEFAULT_WORKSPACE),
    }

def _doc_to_message(d: dict) -> dict:
    return {
        "id": d["id"],
        "session_id": d["session_id"],
        "role": d["role"],
        "content": d["content"],
        "tool_uses": d.get("tool_uses", []),
        "artifacts": d.get("artifacts", []),
        "attachments": d.get("attachments", []),
        "created_at": d["created_at"],
    }

def _mask_key(key: str) -> str:
    if len(key) <= 7:
        return key[:3] + "..." if len(key) > 3 else "***"
    return f"{key[:3]}...{key[-4:]}"

async def _build_message_with_attachments(text: str, attachments: List[Attachment]) -> str:
    if not attachments:
        return text
    chunks = [text.strip()] if text.strip() else []
    for a in attachments:
        upload_doc = await db.uploads.find_one({"id": a.id})
        if not upload_doc:
            continue
        file_path = UPLOADS_DIR / upload_doc["stored_name"]
        if not file_path.exists():
            continue
        extracted = await extract_text_from_file(file_path, upload_doc.get("content_type", ""))
        if extracted:
            chunks.append(f"\n\n[Attached file: {a.filename}]\n{extracted}\n[End of {a.filename}]")
    return "\n".join(chunks)


# ─── Auth Endpoints ───
@api.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user."""
    try:
        user = create_user(user_data.email, user_data.password, user_data.name)
        return create_tokens(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password."""
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return create_tokens(user)


@api.post("/auth/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    new_access_token = refresh_access_token(request.refresh_token)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    # Get user to include in response
    # We need to decode the refresh token to get user_id
    from cogent_auth_v2 import decode_refresh_token
    token_data = decode_refresh_token(request.refresh_token)
    user = get_user_by_id(token_data.user_id) if token_data else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return Token(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            created_at=datetime.fromisoformat(user["created_at"]),
            workspace_id=user["workspace_id"],
        ),
    )


@api.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("name"),
        created_at=datetime.fromisoformat(user["created_at"]),
        workspace_id=user["workspace_id"],
    )


# ─── Session Endpoints (Protected) ───

@api.get("/sessions", response_model=List[SessionOut])
async def list_sessions(user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    cursor = db.sessions.find({"workspace_id": workspace_id}).sort("updated_at", -1)
    items = await cursor.to_list(length=200)
    return [_doc_to_session(i) for i in items]


@api.post("/sessions", response_model=SessionOut)
async def create_session(body: CreateSessionBody, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    sid = str(uuid.uuid4())
    now = datetime.utcnow()
    doc = {
        "id": sid,
        "title": body.title or "New chat",
        "workspace_id": workspace_id,
        "created_at": now,
        "updated_at": now,
    }
    await db.sessions.insert_one(doc)
    return _doc_to_session(doc)


@api.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    # Verify session belongs to user's workspace
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")
    await db.sessions.delete_one({"id": session_id})
    await db.messages.delete_many({"session_id": session_id})
    return {"ok": True}


@api.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
async def list_messages(session_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")
    cursor = db.messages.find({"session_id": session_id}).sort("created_at", 1)
    items = await cursor.to_list(length=1000)
    return [_doc_to_message(i) for i in items]


# Non-streaming message endpoint (kept for compat / tests)
@api.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(session_id: str, body: SendMessageBody, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")

    full_text = await _build_message_with_attachments(body.text, body.attachments)
    now = datetime.utcnow()
    user_msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "user",
        "content": body.text,
        "tool_uses": [],
        "artifacts": [],
        "attachments": [a.dict() for a in body.attachments],
        "created_at": now,
    }
    await db.messages.insert_one(user_msg)

    cursor = db.messages.find({"session_id": session_id, "id": {"$ne": user_msg["id"]}}).sort("created_at", 1)
    history_docs = await cursor.to_list(length=200)
    history = [{"role": d["role"], "content": d["content"]} for d in history_docs]

    try:
        result = await run_turn(db, session_id, workspace_id, full_text, history)
    except Exception as e:
        logger.exception("run_turn failed")
        result = {"text": f"(error: {e})", "tool_uses": [], "artifacts": []}

    asst_msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "assistant",
        "content": result["text"],
        "tool_uses": result.get("tool_uses", []),
        "artifacts": result.get("artifacts", []),
        "attachments": [],
        "created_at": datetime.utcnow(),
    }
    await db.messages.insert_one(asst_msg)

    update = {"updated_at": datetime.utcnow()}
    if session.get("title") in (None, "", "New chat"):
        update["title"] = body.text[:60]
    await db.sessions.update_one({"id": session_id}, {"$set": update})

    return _doc_to_message(asst_msg)


# Streaming message endpoint (SSE)
@api.post("/sessions/{session_id}/messages/stream")
async def stream_message(
    session_id: str, 
    body: SendMessageBody, 
    user: dict = Depends(get_current_user)
):
    workspace_id = get_user_workspace(user)
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")

    full_text = await _build_message_with_attachments(body.text, body.attachments)
    now = datetime.utcnow()
    user_msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "user",
        "content": body.text,
        "tool_uses": [],
        "artifacts": [],
        "attachments": [a.dict() for a in body.attachments],
        "created_at": now,
    }
    await db.messages.insert_one(user_msg)

    cursor = db.messages.find({"session_id": session_id, "id": {"$ne": user_msg["id"]}}).sort("created_at", 1)
    history_docs = await cursor.to_list(length=200)
    history = [{"role": d["role"], "content": d["content"]} for d in history_docs]

    asst_id = str(uuid.uuid4())

    async def event_stream():
        tool_uses = []
        artifacts = []
        final_text = ""
        
        # Emit starting event
        yield f"data: {json.dumps({'type': 'user_saved', 'message': _doc_to_message(user_msg) | {'created_at': user_msg['created_at'].isoformat()}, 'assistant_id': asst_id})}\n\n"

        try:
            async for ev in run_turn_stream(db, session_id, workspace_id, full_text, history):
                if ev["type"] == "tool":
                    tool_uses.append(ev["data"])
                elif ev["type"] == "artifact":
                    artifacts.append(ev["data"])
                elif ev["type"] == "final":
                    final_text = ev["content"]
                yield f"data: {json.dumps(ev)}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            logger.exception("stream failed")
            err = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(err)}\n\n"

        # Persist the final assistant message
        asst_msg = {
            "id": asst_id,
            "session_id": session_id,
            "role": "assistant",
            "content": final_text or "(no response)",
            "tool_uses": tool_uses,
            "artifacts": artifacts,
            "attachments": [],
            "created_at": datetime.utcnow(),
        }
        await db.messages.insert_one(asst_msg)
        update = {"updated_at": datetime.utcnow()}
        if session.get("title") in (None, "", "New chat"):
            update["title"] = body.text[:60]
        await db.sessions.update_one({"id": session_id}, {"$set": update})

        done = {"type": "done", "message": _doc_to_message(asst_msg) | {"created_at": asst_msg["created_at"].isoformat()}}
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─── Memory Endpoints (Protected) ───
@api.get("/memory")
async def list_memory(user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    cursor = db.memories.find({"workspace_id": workspace_id}, {"_id": 0}).sort("updated_at", -1)
    items = await cursor.to_list(length=200)
    return items


@api.post("/memory")
async def add_memory(item: MemoryItem, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    now = datetime.utcnow()
    await db.memories.update_one(
        {"workspace_id": workspace_id, "key": item.key},
        {"$set": {"value": item.value, "updated_at": now}},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/memory/{key}")
async def delete_memory(key: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    await db.memories.delete_one({"workspace_id": workspace_id, "key": key})
    return {"ok": True}


# ─── Settings / Credentials (Protected) ───
@api.get("/settings/credentials", response_model=List[CredentialOut])
async def list_credentials(user: dict = Depends(get_current_user)):
    creds = cogent_auth.list_credentials()
    result = []
    for service in creds:
        cred = cogent_auth.get_credential(service)
        api_key = ""
        if isinstance(cred, dict):
            api_key = cred.get("api_key", "")
        result.append(CredentialOut(
            service=service,
            has_key=bool(api_key),
            key_preview=_mask_key(api_key) if api_key else "",
        ))
    return result


@api.put("/settings/credentials/{service}")
async def set_credential(service: str, body: CredentialBody, user: dict = Depends(get_current_user)):
    cogent_auth.set_credential(service, {"api_key": body.api_key})
    return {"ok": True, "service": service, "key_preview": _mask_key(body.api_key)}


@api.delete("/settings/credentials/{service}")
async def delete_credential(service: str, user: dict = Depends(get_current_user)):
    deleted = cogent_auth.delete_credential(service)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No credential found for '{service}'")
    return {"ok": True, "service": service}


# ─── Scheduled Tasks (Protected) ───
@api.get("/tasks", response_model=List[ScheduledTaskOut])
async def list_tasks(user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    cursor = db.scheduled_tasks.find({"workspace_id": workspace_id}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(length=200)
    return items


@api.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    result = await db.scheduled_tasks.delete_one({"id": task_id, "workspace_id": workspace_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Task not found")
    sched.remove_task_job(task_id)
    return {"ok": True}


@api.post("/tasks/{task_id}/run")
async def run_task_now(task_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    task = await db.scheduled_tasks.find_one({"id": task_id, "workspace_id": workspace_id})
    if not task:
        raise HTTPException(404, "Task not found")
    # Create a dedicated session for this run
    run_session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    session_doc = {
        "id": run_session_id,
        "title": f"⏰ {task['name']} — {now.strftime('%b %d %H:%M')}",
        "workspace_id": workspace_id,
        "created_at": now,
        "updated_at": now,
        "scheduled_task_id": task_id,
    }
    await db.sessions.insert_one(session_doc)

    user_msg = {
        "id": str(uuid.uuid4()),
        "session_id": run_session_id,
        "role": "user",
        "content": f"[scheduled run]\n{task['prompt']}",
        "tool_uses": [],
        "artifacts": [],
        "created_at": now,
    }
    await db.messages.insert_one(user_msg)

    try:
        result = await run_turn(db, run_session_id, workspace_id, task["prompt"], [])
    except Exception as e:
        logger.exception("scheduled run failed")
        result = {"text": f"(scheduled run error: {e})", "tool_uses": [], "artifacts": []}

    asst_msg = {
        "id": str(uuid.uuid4()),
        "session_id": run_session_id,
        "role": "assistant",
        "content": result["text"],
        "tool_uses": result.get("tool_uses", []),
        "artifacts": result.get("artifacts", []),
        "created_at": datetime.utcnow(),
    }
    await db.messages.insert_one(asst_msg)

    await db.scheduled_tasks.update_one(
        {"id": task_id},
        {"$set": {"last_run": datetime.utcnow(), "last_session_id": run_session_id}},
    )
    return {"ok": True, "session_id": run_session_id}


# ─── File Upload (Protected) ───
@api.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    workspace_id = get_user_workspace(user)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix if file.filename else ""
    stored_name = f"{file_id}{ext}"
    file_path = UPLOADS_DIR / stored_name
    
    content = await file.read()
    file_path.write_bytes(content)
    
    doc = {
        "id": file_id,
        "filename": file.filename,
        "stored_name": stored_name,
        "content_type": file.content_type,
        "size": len(content),
        "workspace_id": workspace_id,
        "created_at": datetime.utcnow(),
    }
    await db.uploads.insert_one(doc)
    return {"id": file_id, "filename": file.filename, "size": len(content)}


# ─── Health Checks ───
@api.get("/health")
async def health():
    return {"status": "ok", "service": "cogent"}


@api.get("/health/ready")
async def health_ready():
    # Check database connectivity
    try:
        await db.command("ping")
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": str(e)}
        )


@api.get("/health/live")
async def health_live():
    return {"status": "alive"}


# ─── Skills (Protected) ───
@api.post("/skills/import")
async def import_skills(body: skf.ImportSkillBody, user: dict = Depends(get_current_user)):
    try:
        result = await skf.import_from_url(body.repo_url, force=body.force)
        if result["errors"]:
            logger.warning("Skill import had errors: %s", result["errors"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Git operation failed: {e}")
    except Exception as e:
        logger.exception("Skill import failed")
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/skills/forge")
async def forge_skill(body: skf.ForgeSkillBody, user: dict = Depends(get_current_user)):
    try:
        async def _llm_complete(prompt: str) -> str:
            provider = get_provider()
            return await provider.chat([
                {"role": "system", "content": "You are an expert at analyzing code repositories and creating agent skills."},
                {"role": "user", "content": prompt},
            ])

        result = await skf.forge_skill(body.repo_url, _llm_complete, force=body.force)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Git or LLM operation failed: {e}")
    except Exception as e:
        logger.exception("Skill forge failed")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/skills")
async def list_skills(user: dict = Depends(get_current_user)):
    return skf.list_installed_skills()


@api.get("/skills/{name}")
async def skill_detail(name: str, user: dict = Depends(get_current_user)):
    detail = skf.get_skill_detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return detail


@api.delete("/skills/{name}")
async def delete_skill(name: str, user: dict = Depends(get_current_user)):
    if not skf.delete_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"ok": True, "name": name}


# ─── Loop Engineering (Protected) ───
@api.get("/sessions/{session_id}/loop")
async def get_loop_state(session_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")
    state = le.load_state(session_id)
    return {
        "session_id": state.session_id,
        "phase": state.phase,
        "iteration": state.iteration,
        "task_description": state.task_description[:200] if state.task_description else "",
        "verification_result": state.verification_result,
        "verification_notes": state.verification_notes[:200] if state.verification_notes else "",
        "attempts": len(state.attempts),
        "tokens_estimated": state.tokens_estimated,
        "budget_max": state.budget_max,
        "errors": state.errors,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "updated_at": state.updated_at,
    }


@api.delete("/sessions/{session_id}/loop")
async def reset_loop_state(session_id: str, user: dict = Depends(get_current_user)):
    workspace_id = get_user_workspace(user)
    session = await db.sessions.find_one({"id": session_id, "workspace_id": workspace_id})
    if not session:
        raise HTTPException(404, "Session not found")
    le.delete_state(session_id)
    return {"ok": True}


@api.get("/loops")
async def list_loop_states(user: dict = Depends(get_current_user)):
    return le.get_all_loop_states()


# ─── MCP Registry (Protected) ───
@api.get("/mcp/registry")
async def list_mcp_registry(user: dict = Depends(get_current_user)):
    params = dict(user) if hasattr(user, 'items') else {}
    return mcp_reg.list_registry(params)


@api.post("/mcp/registry/sync")
async def sync_mcp_registry(user: dict = Depends(get_current_user)):
    return await mcp_reg.sync_registry()


@api.get("/mcp/installed")
async def list_installed_mcp(user: dict = Depends(get_current_user)):
    return mcp_reg.get_installed_servers()


@api.post("/mcp/install")
async def install_mcp(body: MCPInstallBody, user: dict = Depends(get_current_user)):
    try:
        registry_entry = body.registry_entry
        config = body.config or {}
        result = await mcp_reg.install_server(
            body.server_id,
            registry_entry=registry_entry,
            config=config,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("MCP install failed")
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/mcp/remove")
async def remove_mcp(body: MCPRemoveBody, user: dict = Depends(get_current_user)):
    ok = await mcp_reg.remove_server(body.name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"MCP server '{body.name}' not found")
    return {"ok": True, "name": body.name}


@api.post("/mcp/config")
async def config_mcp(body: MCPConfigBody, user: dict = Depends(get_current_user)):
    result = mcp_reg.update_server_config(body.name, body.config)
    if result is None:
        raise HTTPException(status_code=404, detail=f"MCP server '{body.name}' not found")
    return {"ok": True, "manifest": result}


@api.get("/mcp/languages")
async def list_mcp_languages(user: dict = Depends(get_current_user)):
    return mcp_reg.get_languages()


@api.get("/mcp/topics")
async def list_mcp_topics(user: dict = Depends(get_current_user)):
    return mcp_reg.list_available_topics()


@api.get("/mcp/server/{server_id:path}")
async def mcp_server_detail(server_id: str, user: dict = Depends(get_current_user)):
    try:
        detail = await mcp_reg.fetch_server_detail(server_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Server '{server_id}' not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("MCP server detail failed")
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/mcp/servers/available")
async def mcp_available(user: dict = Depends(get_current_user)):
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=5,
        )
        docker_ok = result.returncode == 0
    except Exception:
        docker_ok = False
    return {
        "docker_available": docker_ok,
        "registry_synced": mcp_reg.get_cached_registry() is not None,
        "installed_count": len(mcp_reg.get_installed_servers()),
    }


# ─── Include router and middleware ───
app.include_router(api)

# CORS - Configure for production
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# ─── Startup / Shutdown ───
@app.on_event("startup")
async def startup():
    # Loud, harmless warning when operators forget to set a real secret.
    # We deliberately do NOT refuse to start — self-hosted single-user
    # setups may rely on the dev fallback. Set ``COGENT_AUTH_SECRET`` or
    # ``auth.secret_key`` in config.yaml before going public.
    _secret = os.environ.get("COGENT_AUTH_SECRET") or (
        getattr(cfg, "auth_secret_key", None) or ""
    )
    if not _secret:
        logger.warning(
            "JWT secret is unset — falling back to the development default. "
            "Set COGENT_AUTH_SECRET (or config.yaml auth.secret_key) before "
            "exposing this server to the public internet."
        )
    ensure_dirs()
    discover_and_load()
    await sched.start_scheduler(db)
    await run_hooks("on_startup")
    # Auto-sync MCP registry on startup (non-blocking)
    try:
        if not mcp_reg.get_cached_registry():
            asyncio.create_task(mcp_reg.sync_registry())
    except Exception:
        pass

    # Create database indexes
    await create_indexes(db)


@app.on_event("shutdown")
async def shutdown():
    await run_hooks("on_shutdown")
    await sched.stop_scheduler()
    client.close()


# Hook into scheduler when tasks are created by the LLM tool
import tools as _tools_mod
_original_schedule_task = _tools_mod.schedule_task


async def _schedule_task_with_register(db_, workspace_id, name, cadence, time, prompt):
    result = await _original_schedule_task(db_, workspace_id, name, cadence, time, prompt)
    art = result.get("artifact") or {}
    if art.get("id"):
        task = await db_.scheduled_tasks.find_one({"id": art["id"]})
        if task:
            await sched.add_task_job(task)
    return result


_tools_mod.schedule_task = _schedule_task_with_register


# ─── Root ───
@app.get("/")
async def root():
    return {"service": "cogent", "status": "ok", "version": "0.1.0"}


# ─── Health Checks ───
@app.get("/api/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "cogent"}


@app.get("/api/health/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/api/health/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks DB connectivity."""
    try:
        # Check MongoDB
        await db.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")