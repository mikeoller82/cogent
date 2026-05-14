"""Scheduler worker for recurring Viktor tasks.
Uses AsyncIOScheduler. On startup, loads all active scheduled_tasks from MongoDB
and registers cron jobs. Each job runs the task prompt through llm_service and
stores the run output as a system-authored message in a special 'scheduled run'
session scoped to the task.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("viktor.scheduler")

_scheduler: Optional[AsyncIOScheduler] = None
_db_ref = None


def _trigger_for(cadence: str, time_str: str) -> Optional[CronTrigger]:
    try:
        hh, mm = time_str.split(":")
        hour = int(hh)
        minute = int(mm)
    except Exception:
        hour, minute = 9, 0
    cadence = (cadence or "weekly").lower()
    if cadence == "daily":
        return CronTrigger(hour=hour, minute=minute)
    if cadence == "weekly":
        return CronTrigger(day_of_week="mon", hour=hour, minute=minute)
    if cadence == "monthly":
        return CronTrigger(day=1, hour=hour, minute=minute)
    if cadence == "every_minute":  # test-only
        return CronTrigger(minute="*")
    return None


async def _run_task(task_id: str):
    """Execute a single scheduled task: run prompt through Viktor, save result."""
    from llm_service import run_turn
    db = _db_ref
    task = await db.scheduled_tasks.find_one({"id": task_id, "status": "active"})
    if not task:
        logger.info(f"Task {task_id} no longer active, skipping")
        return

    logger.info(f"Running scheduled task: {task['name']}")

    # Create a dedicated session for this run
    run_session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    session_doc = {
        "id": run_session_id,
        "title": f"⏰ {task['name']} — {now.strftime('%b %d %H:%M')}",
        "workspace_id": task["workspace_id"],
        "created_at": now,
        "updated_at": now,
        "scheduled_task_id": task_id,
    }
    await db.sessions.insert_one(session_doc)

    # Insert the prompt as a user message
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
        result = await run_turn(db, run_session_id, task["workspace_id"], task["prompt"], [])
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
    logger.info(f"Task {task['name']} complete")


def _job_id(task_id: str) -> str:
    return f"viktor-task-{task_id}"


async def add_task_job(task: dict):
    if not _scheduler:
        return
    trigger = _trigger_for(task.get("cadence", "weekly"), task.get("time", "09:00"))
    if not trigger:
        return
    job_id = _job_id(task["id"])
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass
    _scheduler.add_job(_run_task, trigger=trigger, args=[task["id"]], id=job_id, replace_existing=True)
    logger.info(f"Scheduled job {job_id} ({task.get('cadence')}@{task.get('time')})")


async def remove_task_job(task_id: str):
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(_job_id(task_id))
    except Exception:
        pass


async def start_scheduler(db):
    global _scheduler, _db_ref
    _db_ref = db
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
        logger.info("Scheduler started")

    # Load existing active tasks
    cursor = db.scheduled_tasks.find({"status": "active"})
    tasks = await cursor.to_list(length=500)
    for t in tasks:
        await add_task_job(t)
    logger.info(f"Loaded {len(tasks)} scheduled tasks")


async def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


async def run_task_now(task_id: str):
    """Manual trigger for a task (called by API endpoint)."""
    await _run_task(task_id)
