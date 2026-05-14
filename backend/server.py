from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
import uuid
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from llm_service import run_turn
from tools import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("viktor")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

DEFAULT_WORKSPACE = "default"

app = FastAPI(title="Viktor API")
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
    role: str  # user | assistant
    content: str
    tool_uses: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    created_at: datetime

class SendMessageBody(BaseModel):
    text: str

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
        "created_at": d["created_at"],
    }


# ---------------- Routes ----------------
@api.get("/")
async def root():
    return {"service": "viktor", "status": "ok"}


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


@api.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(session_id: str, body: SendMessageBody):
    session = await db.sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")

    now = datetime.utcnow()
    user_msg = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "user",
        "content": body.text,
        "tool_uses": [],
        "artifacts": [],
        "created_at": now,
    }
    await db.messages.insert_one(user_msg)

    # Load prior history (excluding system); we re-fetch so user_msg isn't included as "prior".
    cursor = db.messages.find({"session_id": session_id, "id": {"$ne": user_msg["id"]}}).sort("created_at", 1)
    history_docs = await cursor.to_list(length=200)
    history = [{"role": d["role"], "content": d["content"]} for d in history_docs]

    workspace_id = session.get("workspace_id", DEFAULT_WORKSPACE)
    try:
        result = await run_turn(db, session_id, workspace_id, body.text, history)
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
        "created_at": datetime.utcnow(),
    }
    await db.messages.insert_one(asst_msg)

    # update session
    update = {"updated_at": datetime.utcnow()}
    if session.get("title") in (None, "", "New chat"):
        update["title"] = body.text[:60]
    await db.sessions.update_one({"id": session_id}, {"$set": update})

    return _doc_to_message(asst_msg)


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
    return {"ok": True}


# ---------------- Artifacts ----------------
@api.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    pdf_path = ARTIFACTS_DIR / f"{artifact_id}.pdf"
    if pdf_path.exists():
        return FileResponse(str(pdf_path), media_type="application/pdf", filename=f"viktor-{artifact_id[:8]}.pdf")
    raise HTTPException(404, "Not found")


@api.get("/artifacts/{artifact_id}/render", response_class=HTMLResponse)
async def render_artifact(artifact_id: str):
    html_path = ARTIFACTS_DIR / f"{artifact_id}.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    raise HTTPException(404, "Not found")


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
