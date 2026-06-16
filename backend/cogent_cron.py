"""Cron output storage and job management extensions for Cogent.

Analogous to Hermes' ``cron/jobs.py`` and ``cron/output/`` — stores
scheduled task job definitions and execution output in
``memory/cron/``.

This extends the existing ``scheduler.py`` with:
  - Persistent job storage (``memory/cron/jobs.json``)
  - Execution output storage (``memory/cron/output/{job_id}/{timestamp}.md``)
  - Job CRUD operations
  - Output retrieval
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogent_constants import MEMORY_DIR

logger = logging.getLogger("cogent.cron")


# ── Directories ──────────────────────────────────────────────────────────

def _cron_dir() -> Path:
    p = MEMORY_DIR / "cron"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _output_dir() -> Path:
    p = _cron_dir() / "output"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _jobs_path() -> Path:
    return _cron_dir() / "jobs.json"


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class CronJob:
    id: str
    name: str = ""
    cadence: str = "daily"       # daily | weekly | monthly | weekdays
    time: str = "09:00"          # HH:MM 24-hour
    prompt: str = ""
    workspace_id: str = "default"
    enabled: bool = True
    created_at: float = 0.0
    last_run_at: Optional[float] = None
    last_output: str = ""        # summary of last run
    run_count: int = 0


@dataclass
class CronOutput:
    job_id: str
    timestamp: str = ""
    content: str = ""
    duration: float = 0.0


# ── Job storage ──────────────────────────────────────────────────────────

_lock = threading.Lock()


def _load_jobs() -> Dict[str, CronJob]:
    path = _jobs_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {jid: CronJob(**j) for jid, j in data.items()}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt cron jobs file, starting fresh")
        return {}


def _save_jobs(jobs: Dict[str, CronJob]) -> None:
    data = {jid: asdict(j) for jid, j in jobs.items()}
    path = _jobs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── Job CRUD ─────────────────────────────────────────────────────────────

def register_job(name: str, cadence: str, time_str: str,
                 prompt: str, workspace_id: str = "default") -> CronJob:
    """Register a new cron job and persist it."""
    import uuid
    job = CronJob(
        id=str(uuid.uuid4()),
        name=name, cadence=cadence, time=time_str,
        prompt=prompt, workspace_id=workspace_id,
        created_at=time.time(),
    )
    with _lock:
        jobs = _load_jobs()
        jobs[job.id] = job
        _save_jobs(jobs)
    logger.info("Cron job registered: %s (%s @ %s)", job.name, cadence, time_str)
    return job


def get_job(job_id: str) -> Optional[CronJob]:
    with _lock:
        return _load_jobs().get(job_id)


def list_jobs(workspace_id: Optional[str] = None) -> List[Dict]:
    with _lock:
        jobs = _load_jobs().values()

    result = []
    for j in jobs:
        if workspace_id and j.workspace_id != workspace_id:
            continue
        result.append({
            "id": j.id,
            "name": j.name,
            "cadence": j.cadence,
            "time": j.time,
            "enabled": j.enabled,
            "last_run": j.last_run_at,
            "run_count": j.run_count,
            "last_output": (j.last_output or "")[:100],
        })
    result.sort(key=lambda j: j.get("last_run") or 0, reverse=True)
    return result


def update_job(job_id: str, **changes) -> bool:
    with _lock:
        jobs = _load_jobs()
        job = jobs.get(job_id)
        if not job:
            return False
        for key, val in changes.items():
            if hasattr(job, key):
                setattr(job, key, val)
        jobs[job_id] = job
        _save_jobs(jobs)
    return True


def delete_job(job_id: str) -> bool:
    with _lock:
        jobs = _load_jobs()
        if job_id not in jobs:
            return False
        del jobs[job_id]
        _save_jobs(jobs)
    logger.info("Cron job deleted: %s", job_id[:12])
    return True


# ── Output storage ───────────────────────────────────────────────────────

def save_output(job_id: str, content: str, duration: float = 0.0) -> str:
    """Save execution output for a job. Returns the output id."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    output_id = f"{timestamp}"

    job_dir = _output_dir() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    out_path = job_dir / f"{output_id}.md"
    header = (
        f"# Output: {job_id}\n"
        f"**Timestamp:** {timestamp}\n"
        f"**Duration:** {duration:.1f}s\n\n"
    )
    out_path.write_text(header + content, encoding="utf-8")

    # Update job's last run info
    update_job(job_id, last_run_at=time.time(),
               last_output=content[:200],
               run_count=(get_job(job_id).run_count + 1
                          if get_job(job_id) else 1))

    logger.info("Cron output saved: %s / %s", job_id[:12], output_id)
    return output_id


def list_outputs(job_id: str, limit: int = 10) -> List[Dict]:
    """List recent outputs for a job."""
    job_dir = _output_dir() / job_id
    if not job_dir.is_dir():
        return []

    results = []
    for f in sorted(job_dir.iterdir(), reverse=True):
        if f.suffix == ".md":
            results.append({
                "id": f.stem,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return results[:limit]


def get_output(job_id: str, output_id: str) -> Optional[str]:
    """Read a specific output by job and output id."""
    path = _output_dir() / job_id / f"{output_id}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
