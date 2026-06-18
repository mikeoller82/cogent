"""Cogent CLI dispatcher.

Provides management commands for the Cogent AI coworker.
Run ``python -m backend.cli --help`` for usage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure backend/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import display as D


def _add_server_subparser(subparsers) -> None:
    p = subparsers.add_parser("server", help="Manage the Cogent API server")
    p.add_argument("action", choices=["start", "stop", "status"],
                   help="Server action")
    p.add_argument("--host", default="0.0.0.0", help="Bind host")
    p.add_argument("--port", type=int, default=8000, help="Bind port")
    p.add_argument("--reload", action="store_true", help="Auto-reload on changes")


def _add_tools_subparser(subparsers) -> None:
    p = subparsers.add_parser("tools", help="List available tools")
    p.add_argument("action", choices=["list"], default="list", nargs="?")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_auth_subparser(subparsers) -> None:
    p = subparsers.add_parser("auth", help="Manage credentials")
    p.add_argument("action", choices=["list", "set", "get", "delete"])
    p.add_argument("--service", "-s", help="Service name")
    p.add_argument("--key", "-k", help="Credential key (for set)")
    p.add_argument("--value", "-v", help="Credential value (for set)")


def _add_cron_subparser(subparsers) -> None:
    p = subparsers.add_parser("cron", help="Manage scheduled tasks")
    p.add_argument("action", choices=["list", "run"], default="list", nargs="?")
    p.add_argument("--id", help="Task id (for run)")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_kanban_subparser(subparsers) -> None:
    p = subparsers.add_parser("kanban", help="Manage task board")
    p.add_argument("action", choices=["list", "count", "summary"],
                   default="list", nargs="?")
    p.add_argument("--column", "-c", help="Filter by column")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_cache_subparser(subparsers) -> None:
    p = subparsers.add_parser("cache", help="Manage cache")
    p.add_argument("action", choices=["list", "clear"], default="list", nargs="?")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_processes_subparser(subparsers) -> None:
    p = subparsers.add_parser("processes", aliases=["ps"],
                              help="List background processes")
    p.add_argument("action", choices=["list", "reap"], default="list", nargs="?")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_status_subparser(subparsers) -> None:
    p = subparsers.add_parser("status", help="Show system status")
    p.add_argument("--json", action="store_true", help="Output as JSON")

def _add_config_subparser(subparsers) -> None:
    p = subparsers.add_parser("config", help="View or set configuration")
    p.add_argument("action", choices=["show", "get", "set"], default="show", nargs="?")
    p.add_argument("key", nargs="?", help="Config key (dot-separated for nested)")
    p.add_argument("--value", "-v", help="Value to set")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_logs_subparser(subparsers) -> None:
    p = subparsers.add_parser("logs", help="View and manage logs")
    p.add_argument("action", choices=["show", "tail", "clear"], default="show", nargs="?")
    p.add_argument("--lines", "-n", type=int, default=20, help="Number of lines (tail)")
    p.add_argument("--level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR"])


def _add_memory_subparser(subparsers) -> None:
    p = subparsers.add_parser("memory", help="Manage file-based memory")
    p.add_argument("action", choices=["show", "set", "delete", "list"], default="show", nargs="?")
    p.add_argument("key", nargs="?", help="Memory key")
    p.add_argument("--value", "-v", help="Value to set")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_checkpoints_subparser(subparsers) -> None:
    p = subparsers.add_parser("checkpoints", aliases=["snapshots"],
                              help="Manage state snapshots")
    p.add_argument("action", choices=["list", "create", "clean"], default="list", nargs="?")
    p.add_argument("--name", "-n", help="Snapshot name (create)")
    p.add_argument("--keep", type=int, default=10, help="Number of snapshots to keep (clean)")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_blueprints_subparser(subparsers) -> None:
    p = subparsers.add_parser("blueprints", help="List available task blueprints")
    p.add_argument("action", choices=["list", "show"], default="list", nargs="?")
    p.add_argument("--name", "-n", help="Blueprint name (show)")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def _add_skills_subparser(subparsers) -> None:
    p = subparsers.add_parser("skills", help="Manage agent skills")
    p.add_argument("action", choices=["list", "install", "remove", "catalog"], default="list", nargs="?")
    p.add_argument("--name", "-n", help="Skill name")
    p.add_argument("--repo", "-r", help="GitHub repo URL (install)")
    p.add_argument("--json", action="store_true", help="Output as JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cogent",
        description="Cogent AI coworker — management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    _add_server_subparser(subparsers)
    _add_tools_subparser(subparsers)
    _add_auth_subparser(subparsers)
    _add_cron_subparser(subparsers)
    _add_kanban_subparser(subparsers)
    _add_cache_subparser(subparsers)
    _add_processes_subparser(subparsers)
    _add_status_subparser(subparsers)
    _add_config_subparser(subparsers)
    _add_logs_subparser(subparsers)
    _add_memory_subparser(subparsers)
    _add_checkpoints_subparser(subparsers)
    _add_blueprints_subparser(subparsers)
    _add_skills_subparser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    command = args.command

    if command == "server":
        _cmd_server(args)
    elif command == "tools":
        _cmd_tools(args)
    elif command == "auth":
        _cmd_auth(args)
    elif command == "cron":
        _cmd_cron(args)
    elif command == "kanban":
        _cmd_kanban(args)
    elif command == "cache":
        _cmd_cache(args)
    elif command in ("processes", "ps"):
        _cmd_processes(args)
    elif command == "config":
        _cmd_config(args)
    elif command == "logs":
        _cmd_logs(args)
    elif command == "memory":
        _cmd_memory(args)
    elif command in ("checkpoints", "snapshots"):
        _cmd_checkpoints(args)
    elif command in ("blueprints",):
        _cmd_blueprints(args)
    elif command == "skills":
        _cmd_skills(args)
    elif command == "status":
        _cmd_status(args)


# ── Command implementations ──────────────────────────────────────────────

def _cmd_server(args: argparse.Namespace) -> None:
    action = args.action
    if action == "status":
        import requests
        port = args.port
        D.subheader("Server Status")
        try:
            r = requests.get(f"http://localhost:{port}/api/sessions", timeout=3)
            D.badge("running", D.GREEN), D.ok(f"HTTP {r.status_code} on port {port}")
        except requests.ConnectionError:
            D.warning("Not running")
            D.fail(f"No server on port {port}")
    elif action == "start":
        import subprocess
        cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.server:app",
            "--host", args.host,
            "--port", str(args.port),
        ]
        if args.reload:
            cmd.append("--reload")
        D.subheader("Starting Server")
        D.keyval("Host", f"{args.host}:{args.port}")
        D.keyval("Reload", "yes" if args.reload else "no")
        subprocess.Popen(cmd)
        D.ok("Server launched")
    elif action == "stop":
        import signal
        pid_file = "/tmp/cogent-server.pid"
        if os.path.isfile(pid_file):
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.unlink(pid_file)
            D.ok(f"PID {pid} stopped")
        else:
            D.fail("No PID file found")


def _cmd_tools(args: argparse.Namespace) -> None:
    from tools import TOOL_SPECS
    if args.json:
        print(json.dumps(TOOL_SPECS, indent=2))
        return
    D.subheader(f"Available tools ({len(TOOL_SPECS)})")
    for spec in TOOL_SPECS:
        D.item(f"{spec['name']} — {spec['description'][:80]}")


def _cmd_auth(args: argparse.Namespace) -> None:
    from cogent_auth import (get_credential, list_credentials,
                             set_credential, delete_credential)
    if args.action == "list":
        creds = list_credentials()
        if args.json:
            print(json.dumps(creds))
            return
        D.subheader(f"Credentials ({len(creds)})")
        for c in creds:
            D.item(f"{c}")
    elif args.action == "set":
        if not args.service or not args.key:
            D.error("--service and --key are required for set")
            sys.exit(1)
        value = {args.key: args.value or ""}
        set_credential(args.service, value)
        D.success(f"Credential set: {args.service}")
    elif args.action == "get":
        if not args.service:
            D.error("--service is required for get")
            sys.exit(1)
        cred = get_credential(args.service)
        if args.json:
            print(json.dumps(cred or {}))
            return
        if cred:
            for k, v in cred.items():
                D.keyval(k, str(v))
        else:
            D.warning(f"No credential found: {args.service}")
    elif args.action == "delete":
        if not args.service:
            D.error("--service is required for delete")
            sys.exit(1)
        if delete_credential(args.service):
            D.success(f"Deleted: {args.service}")
        else:
            D.error(f"Not found: {args.service}")


def _cmd_cron(args: argparse.Namespace) -> None:
    # Lazy import to avoid MongoDB dependency when just listing
    if args.action == "list":
        from blueprint_catalog import list_blueprints
        bps = list_blueprints()
        if args.json:
            data = [{"name": bp.name, "category": bp.category,
                     "description": bp.description} for bp in bps]
            print(json.dumps(data, indent=2))
            return
        D.subheader(f"Available task blueprints ({len(bps)})")
        for bp in bps:
            D.item(f"{bp.name} ({bp.category}) — {bp.description}")
    elif args.action == "run":
        if not args.id:
            D.error("--id is required for run")
            sys.exit(1)
        from scheduler import run_task_now
        import asyncio
        result = asyncio.run(run_task_now(args.id))
        D.success(f"Task {args.id} triggered: {result}")


def _cmd_kanban(args: argparse.Namespace) -> None:
    from cogent_kanban import list_tasks, task_count, COLUMNS
    if args.action == "list":
        tasks = list_tasks(column=args.column)
        if args.json:
            data = [{"id": t.id, "title": t.title, "column": t.column,
                     "priority": t.priority} for t in tasks]
            print(json.dumps(data, indent=2))
            return
        if not tasks:
            D.hint("No tasks")
            return
        D.table(
            [[t.id, D.status_badge(t.column), t.title[:60], t.priority] for t in tasks],
            headers=["ID", "Column", "Title", "Priority"]
        )
    elif args.action == "count":
        counts = {}
        for col in COLUMNS:
            n = task_count(col)
            if n:
                counts[col] = n
        if args.json:
            print(json.dumps(counts))
            return
        for col, n in counts.items():
            print(f"  {D.status_badge(col)} {D.WARM}{n}{D.RESET} task(s)")
    elif args.action == "summary":
        from cogent_kanban import kanban_summary
        D.panel("Kanban Summary", kanban_summary())


def _cmd_cache(args: argparse.Namespace) -> None:
    from cogent_cache import cache_list, cache_clear
    if args.action == "list":
        entries = cache_list()
        if args.json:
            print(json.dumps(entries, indent=2))
            return
        if not entries:
            D.info("Cache is empty")
            return
        D.subheader(f"Cache entries ({len(entries)})")
        for e in entries:
            expired = f" {D.AMBER}(expired){D.RESET}" if e["expired"] else ""
            print(f"  {D.DIM}•{D.RESET} {D.WARM}{e['key']}{D.RESET} — {D.DIM}{e['age']}s / {e['ttl']}s TTL{D.RESET}{expired}")
    elif args.action == "clear":
        count = cache_clear()
        if count:
            D.success(f"Cleared {count} expired cache entries")
        else:
            D.info("No expired cache entries to clear")


def _cmd_processes(args: argparse.Namespace) -> None:
    from cogent_processes import list_processes, reap_stale
    if args.action == "list":
        procs = list_processes()
        if args.json:
            data = [{"pid": p.pid, "label": p.label, "status": p.status,
                     "command": p.command[:60]} for p in procs]
            print(json.dumps(data, indent=2))
            return
        if not procs:
            D.hint("No processes")
            return
        D.table(
            [[str(p.pid), D.status_badge(p.status), p.label or p.command[:40]] for p in procs],
            headers=["PID", "Status", "Command"]
        )
    elif args.action == "reap":
        count = reap_stale()
        if count:
            D.ok(f"Reaped {count} stale processes")
        else:
            D.hint("No stale processes to reap")


def _cmd_status(args: argparse.Namespace) -> None:
    """Show aggregated system status."""
    from cogent_config import get_config
    from cogent_constants import PROJECT_ROOT, MEMORY_DIR

    cfg = get_config()

    if args.json:
        info = {
            "cogent_root": str(PROJECT_ROOT),
            "model": cfg.model_name,
            "db_name": cfg.db_name,
            "log_level": cfg.log_level,
            "max_turns": cfg.max_turns,
        }
        print(json.dumps(info, indent=2))
        return

    D.banner("Cogent Status", "system overview")

    D.section("Runtime", [
        ("Root", str(PROJECT_ROOT)),
        ("Model", cfg.model_name),
        ("DB", cfg.db_name),
        ("Log", str(cfg.log_level)),
        ("Max turns", str(cfg.max_turns)),
        ("Memory dir", str(MEMORY_DIR)),
    ])

    # Directory sizes
    sizes = []
    for d in [PROJECT_ROOT / "memory" / "cache",
              PROJECT_ROOT / "memory" / "sessions",
              PROJECT_ROOT / "memory" / "loops"]:
        if d.is_dir():
            size = sum(f.stat().st_size for f in d.glob("**/*") if f.is_file())
            sizes.append((d.name, f"{size / 1024:.0f} KB"))
    D.section("Storage", sizes)


if __name__ == "__main__":
    main()


def _cmd_config(args: argparse.Namespace) -> None:
    """View or set configuration."""
    from cogent_config import get_config, set_override
    cfg = get_config()

    if args.action == "show":
        if args.key:
            val = getattr(cfg, args.key, None)
            if args.json:
                print(json.dumps({args.key: val}, indent=2, default=str))
                return
            D.keyval(args.key, str(val))
        else:
            info = {"model_name": cfg.model_name, "model_base_url": cfg.model_base_url,
                    "db_name": cfg.db_name, "mongo_url": cfg.mongo_url,
                    "log_level": cfg.log_level, "max_turns": cfg.max_turns}
            if args.json:
                print(json.dumps(info, indent=2, default=str))
                return
            D.subheader("Configuration")
            for k, v in info.items():
                D.keyval(k, str(v))
    elif args.action == "set" and args.key and args.value:
        set_override(args.key, args.value)
        D.success(f"Set {args.key} = {args.value}")
    elif args.action == "get" and args.key:
        val = getattr(cfg, args.key, None)
        if args.json:
            print(json.dumps({args.key: val}, indent=2, default=str))
            return
        print(val)


def _cmd_logs(args: argparse.Namespace) -> None:
    """View and manage logs."""
    from cogent_constants import PROJECT_ROOT
    log_dir = PROJECT_ROOT / "backend" / "logs"
    if not log_dir.is_dir():
        D.warning("No logs directory found")
        return

    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        D.info("No log files found")
        return

    if args.action == "clear":
        import shutil
        for f in log_files:
            f.unlink()
        D.success(f"Cleared {len(log_files)} log files")
        return

    latest = log_files[0]
    if args.action == "show":
        lines = latest.read_text(encoding="utf-8").splitlines()
        D.header(f"Log: {latest.name}")
        for line in lines[-args.lines:]:
            print(f"  {line}")
    elif args.action == "tail":
        import subprocess
        D.info(f"Tailing {latest.name} (Ctrl+C to stop)...")
        subprocess.run(["tail", "-n", str(args.lines), "-f", str(latest)])


def _cmd_memory(args: argparse.Namespace) -> None:
    """Manage file-based memory."""
    from cogent_memory import remember, recall, memory_summary
    if args.action == "show":
        text = memory_summary()
        if args.json:
            print(json.dumps({"memory": text}, indent=2))
            return
        D.header("Memory")
        print(f"  {text or 'No memory stored'}")
    elif args.action == "set" and args.key and args.value:
        remember(args.key, args.value)
        D.success(f"Stored memory: {args.key}")
    elif args.action == "delete" and args.key:
        remember(args.key, "")  # Overwrite with empty
        D.success(f"Deleted memory: {args.key}")
    elif args.action == "list":
        text = memory_summary()
        if args.json:
            print(json.dumps({"memory": text}, indent=2))
            return
        D.subheader("Memory entries")
        print(f"  {text or 'No memory stored'}")


def _cmd_checkpoints(args: argparse.Namespace) -> None:
    """Manage state snapshots."""
    from cogent_checkpoints import create_snapshot, list_snapshots, clean_snapshots
    if args.action == "list":
        snaps = list_snapshots()
        if args.json:
            print(json.dumps(snaps, indent=2, default=str))
            return
        if not snaps:
            D.info("No snapshots")
            return
        D.subheader(f"Snapshots ({len(snaps)})")
        for s in snaps[-20:]:
            label = s.get("label", "") or s.get("name", "")
            D.item(label)
    elif args.action == "create":
        name = args.name or f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = create_snapshot(name)
        D.success(f"Created snapshot: {result}")
    elif args.action == "clean":
        count = clean_snapshots(keep=args.keep)
        if count:
            D.success(f"Cleaned, keeping {args.keep} snapshots")
        else:
            D.info("Nothing to clean")


def _cmd_blueprints(args: argparse.Namespace) -> None:
    """List available task blueprints."""
    from blueprint_catalog import BLUEPRINTS
    if args.action == "list":
        if args.json:
            print(json.dumps([{"name": b["name"], "description": b["description"]}
                             for b in BLUEPRINTS], indent=2))
            return
        D.subheader(f"Blueprints ({len(BLUEPRINTS)})")
        for b in BLUEPRINTS:
            D.item(f"{b['name']} — {b['description'][:80]}")
    elif args.action == "show" and args.name:
        for b in BLUEPRINTS:
            if b["name"] == args.name:
                if args.json:
                    print(json.dumps(b, indent=2, default=str))
                    return
                D.plain(json.dumps(b, indent=2, default=str))
                return
        D.error(f"Blueprint '{args.name}' not found")


def _cmd_skills(args: argparse.Namespace) -> None:
    """Manage agent skills."""
    if args.action == "list":
        try:
            import agent_skills as ask
            skills = ask.list_installed_skills()
            if args.json:
                print(json.dumps(skills, indent=2))
                return
            if not skills:
                D.info("No skills installed")
                return
            D.subheader(f"Installed skills ({len(skills)})")
            for s in skills:
                name = s.get("name", s.get("title", "?"))
                D.item(name)
        except Exception as e:
            D.error(f"Error reading skills: {e}")
    elif args.action == "install" and args.repo:
        try:
            import skill_forge as sf
            result = sf.import_skill(args.repo, force=("--force" in (args.extra or "")))
            D.success(f"Installed skill from {args.repo}: {result}")
        except Exception as e:
            D.error(f"Error installing skill: {e}")
    elif args.action == "remove" and args.name:
        try:
            import skill_forge as sf
            sf.delete_skill(args.name)
            D.success(f"Removed skill: {args.name}")
        except Exception as e:
            D.error(f"Error removing skill: {e}")
    elif args.action == "catalog":
        try:
            from skills_catalog import catalog_summary
            print(catalog_summary())
        except ImportError:
            D.error("Skills catalog not available")
