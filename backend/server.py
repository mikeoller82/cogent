from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
import uuid
import json
import logging
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from llm_service import run_turn, run_turn_stream
from tools import ARTIFACTS_DIR
from file_extract import extract_text_from_file
import scheduler as sched

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cogent")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

UPLOADS_DIR = Path("/app/backend/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_WORKSPACE = "default"

app = FastAPI(title="Cogent API")
api = APIRouter(prefix="/api")


# ---------------- Models ----------------
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


# ---------------- Helpers ----------------
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


async def _build_message_with_attachments(text: str, attachments: List[Attachment]) -> str:
    """Inline extracted text of attached files into the message body for the LLM."""
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


# ---------------- Routes ----------------
@api.get("/")
async def root():
    return {"service": "cogent", "status": "ok"}


# Sessions
@api.get("/sessions", response_model=List[SessionOut])
async def list_sessions():
    cursor = db.sessions.find({"workspace_id": DEFAULT_WORKSPACE}).sort("updated_at", -1)
    items = await cursor.to_list(length=200)
    return [_doc_to_session(i) for i in items]


@api.post("/sessions", response_model=SessionOut)
async def create_session(body: CreateSessionBody):
    sid = str(uuid.uuid4())
    now = datetime.utcnow()
    doc = {
        "id": sid,
        "title": body.title or "New chat",
        "workspace_id": DEFAULT_WORKSPACE,
        "created_at": now,
        "updated_at": now,
    }
    await db.sessions.insert_one(doc)
    return _doc_to_session(doc)


@api.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    await db.sessions.delete_one({"id": session_id})
    await db.messages.delete_many({"session_id": session_id})
    return {"ok": True}


@api.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
async def list_messages(session_id: str):
    cursor = db.messages.find({"session_id": session_id}).sort("created_at", 1)
    items = await cursor.to_list(length=1000)
    return [_doc_to_message(i) for i in items]


# Non-streaming message endpoint (kept for compat / tests)
@api.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(session_id: str, body: SendMessageBody):
    session = await db.sessions.find_one({"id": session_id})
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

    workspace_id = session.get("workspace_id", DEFAULT_WORKSPACE)
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
async def stream_message(session_id: str, body: SendMessageBody):
    session = await db.sessions.find_one({"id": session_id})
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
    workspace_id = session.get("workspace_id", DEFAULT_WORKSPACE)

    asst_id = str(uuid.uuid4())

    async def event_stream():
        tool_uses = []
        artifacts = []
        final_text = ""
        # Emit a starting event so the client can render the user message + assistant placeholder
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


# ---------------- Memory ----------------
@api.get("/memory")
async def list_memory():
    cursor = db.memories.find({"workspace_id": DEFAULT_WORKSPACE}, {"_id": 0}).sort("updated_at", -1)
    items = await cursor.to_list(length=200)
    return items


@api.post("/memory")
async def add_memory(item: MemoryItem):
    now = datetime.utcnow()
    await db.memories.update_one(
        {"workspace_id": DEFAULT_WORKSPACE, "key": item.key},
        {"$set": {"value": item.value, "updated_at": now}},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/memory/{key}")
async def delete_memory(key: str):
    await db.memories.delete_one({"workspace_id": DEFAULT_WORKSPACE, "key": key})
    return {"ok": True}


# ---------------- Scheduled tasks ----------------
@api.get("/tasks", response_model=List[ScheduledTaskOut])
async def list_tasks():
    cursor = db.scheduled_tasks.find({"workspace_id": DEFAULT_WORKSPACE}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(length=200)
    return items


@api.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    await db.scheduled_tasks.delete_one({"id": task_id})
    await sched.remove_task_job(task_id)
    return {"ok": True}


@api.post("/tasks/{task_id}/run")
async def trigger_task(task_id: str):
    """Manually run a scheduled task immediately. Returns when the run finishes."""
    asyncio.create_task(sched.run_task_now(task_id))
    return {"ok": True, "message": "Task queued"}


# ---------------- File uploads ----------------
@api.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    safe_name = (file.filename or "upload").replace("/", "_")
    stored = f"{file_id}__{safe_name}"
    dest = UPLOADS_DIR / stored
    contents = await file.read()
    dest.write_bytes(contents)
    doc = {
        "id": file_id,
        "filename": file.filename,
        "stored_name": stored,
        "content_type": file.content_type or "",
        "size": len(contents),
        "workspace_id": DEFAULT_WORKSPACE,
        "uploaded_at": datetime.utcnow(),
    }
    await db.uploads.insert_one(doc)
    return {"id": file_id, "filename": file.filename, "size": len(contents)}


# ---------------- Artifacts ----------------
@api.get("/artifact/{artifact_id}")
async def get_artifact(artifact_id: str, dl: int = 0):
    """Serve any artifact. PDFs render inline by default, ?dl=1 to download.
    HTML artifacts (web apps) always render inline."""
    pdf_path = ARTIFACTS_DIR / f"{artifact_id}.pdf"
    html_path = ARTIFACTS_DIR / f"{artifact_id}.html"
    if pdf_path.exists():
        disp = "attachment" if dl else "inline"
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disp}; filename="cogent-{artifact_id[:8]}.pdf"'},
        )
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    raise HTTPException(404, "Not found")


# Backward-compat aliases (older messages had these URLs stored in DB)
@api.get("/artifacts/{artifact_id}/download")
async def _legacy_download(artifact_id: str, dl: int = 0):
    return await get_artifact(artifact_id, dl)


@api.get("/artifacts/{artifact_id}/render", response_class=HTMLResponse)
async def _legacy_render(artifact_id: str):
    return await get_artifact(artifact_id, 0)


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await sched.start_scheduler(db)


@app.on_event("shutdown")
async def shutdown():
    await sched.stop_scheduler()
    client.close()


# Hook into scheduler when tasks are created by the LLM tool — patch tools.schedule_task
# to register the cron job after insert. We achieve this by wrapping the existing function.
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
