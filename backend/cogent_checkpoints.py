"""State snapshots for Cogent.

Analogous to Hermes' ``state-snapshots/`` — creates timestamped
backups of key state files before making changes, enabling rollback.

Snapshots are stored in ``memory/snapshots/{timestamp}/``.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cogent_constants import MEMORY_DIR, ensure_dirs

logger = logging.getLogger("cogent.checkpoints")


def _snapshots_dir() -> Path:
    p = MEMORY_DIR / "snapshots"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Files to snapshot ────────────────────────────────────────────────────

SNAPSHOT_PATHS: List[Path] = [
    MEMORY_DIR / "kanban.json",
    MEMORY_DIR / "auth.json",
    MEMORY_DIR / "processes.json",
    MEMORY_DIR / "sessions" / "sessions.json",
    MEMORY_DIR / "memories" / "MEMORY.md",
    MEMORY_DIR / "memories" / "USER.md",
]


# ── Create snapshot ──────────────────────────────────────────────────────

def create_snapshot(label: str = "") -> str:
    """Create a timestamped snapshot of all tracked state files.

    Args:
        label: Optional description for the snapshot (e.g. "before-kanban-update").

    Returns:
        The snapshot directory name (timestamp).
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    if label:
        snapshot_name = f"{timestamp}-{label}"
    else:
        snapshot_name = timestamp

    snap_dir = _snapshots_dir() / snapshot_name
    snap_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for src in SNAPSHOT_PATHS:
        if src.is_file():
            # Preserve relative path inside snapshot
            rel = src.relative_to(MEMORY_DIR)
            dest = snap_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            count += 1

    # Write manifest
    manifest = {
        "timestamp": timestamp,
        "label": label,
        "created_at": time.time(),
        "files": count,
    }
    (snap_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    logger.info("Snapshot created: %s (%d files)", snapshot_name, count)
    return snapshot_name


# ── List / info ──────────────────────────────────────────────────────────

def list_snapshots(limit: int = 20) -> List[Dict]:
    """List recent snapshots, newest first."""
    results: List[Dict] = []
    snap_dir = _snapshots_dir()
    if not snap_dir.is_dir():
        return results

    for entry in sorted(snap_dir.iterdir(), reverse=True):
        if entry.is_dir():
            manifest_path = entry / "manifest.json"
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text())
                except (json.JSONDecodeError, TypeError):
                    manifest = {}
                results.append({
                    "name": entry.name,
                    "label": manifest.get("label", ""),
                    "created_at": manifest.get("created_at", 0),
                    "files": manifest.get("files", 0),
                })
            else:
                results.append({
                    "name": entry.name,
                    "label": "",
                    "created_at": entry.stat().st_ctime,
                    "files": len(list(entry.rglob("*"))),
                })
    return results[:limit]


# ── Restore ──────────────────────────────────────────────────────────────

def restore_snapshot(snapshot_name: str, dry_run: bool = False) -> int:
    """Restore state files from a snapshot.

    Args:
        snapshot_name: Name of the snapshot directory.
        dry_run: If True, only report what would be restored.

    Returns:
        Number of files restored.
    """
    snap_dir = _snapshots_dir() / snapshot_name
    if not snap_dir.is_dir():
        logger.error("Snapshot not found: %s", snapshot_name)
        return 0

    count = 0
    for f in snap_dir.rglob("*"):
        if f.is_file() and f.name != "manifest.json":
            rel = f.relative_to(snap_dir)
            dest = MEMORY_DIR / rel
            if dry_run:
                logger.info("Would restore: %s → %s", f, dest)
                count += 1
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                count += 1

    if not dry_run:
        logger.info("Restored %d files from snapshot: %s", count, snapshot_name)
    return count


# ── Cleanup ──────────────────────────────────────────────────────────────

def clean_snapshots(keep: int = 10) -> int:
    """Remove snapshots beyond the *keep* most recent. Returns count removed."""
    snaps = list_snapshots(limit=999)
    if len(snaps) <= keep:
        return 0

    removed = 0
    for snap in snaps[keep:]:
        snap_dir = _snapshots_dir() / snap["name"]
        if snap_dir.is_dir():
            shutil.rmtree(snap_dir)
            removed += 1

    if removed:
        logger.info("Cleaned %d old snapshots (keeping %d)", removed, keep)
    return removed
