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
        try:
            r = requests.get(f"http://localhost:{port}/api/sessions", timeout=3)
            print(f"Cogent server running on port {port} (HTTP {r.status_code})")
        except requests.ConnectionError:
            print(f"Cogent server not running on port {port}")
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
        print(f"Starting Cogent server on {args.host}:{args.port}...")
        subprocess.Popen(cmd)
    elif action == "stop":
        import signal
        pid_file = "/tmp/cogent-server.pid"
        if os.path.isfile(pid_file):
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.unlink(pid_file)
            print(f"Cogent server (PID {pid}) stopped")
        else:
            print("No PID file found. Use --pid or kill manually.")


def _cmd_tools(args: argparse.Namespace) -> None:
    from tools import TOOL_SPECS
    if args.json:
        print(json.dumps(TOOL_SPECS, indent=2))
        return
    print(f"Available tools ({len(TOOL_SPECS)}):")
    for spec in TOOL_SPECS:
        print(f"  {spec['name']} — {spec['description'][:80]}")


def _cmd_auth(args: argparse.Namespace) -> None:
    from cogent_auth import (get_credential, list_credentials,
                             set_credential, delete_credential)
    if args.action == "list":
        creds = list_credentials()
        if args.json:
            print(json.dumps(creds))
            return
        print(f"Credentials ({len(creds)}):")
        for c in creds:
            print(f"  - {c}")
    elif args.action == "set":
        if not args.service or not args.key:
            print("--service and --key are required for set")
            sys.exit(1)
        value = {args.key: args.value or ""}
        set_credential(args.service, value)
        print(f"Credential set: {args.service}")
    elif args.action == "get":
        if not args.service:
            print("--service is required for get")
            sys.exit(1)
        cred = get_credential(args.service)
        if args.json:
            print(json.dumps(cred or {}))
            return
        if cred:
            for k, v in cred.items():
                print(f"{k}={v}")
        else:
            print(f"No credential found: {args.service}")
    elif args.action == "delete":
        if not args.service:
            print("--service is required for delete")
            sys.exit(1)
        if delete_credential(args.service):
            print(f"Deleted: {args.service}")
        else:
            print(f"Not found: {args.service}")


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
        print(f"Available task blueprints ({len(bps)}):")
        for bp in bps:
            print(f"  {bp.name} ({bp.category}) — {bp.description}")
    elif args.action == "run":
        if not args.id:
            print("--id is required for run")
            sys.exit(1)
        from scheduler import run_task_now
        import asyncio
        result = asyncio.run(run_task_now(args.id))
        print(f"Task {args.id} triggered: {result}")


def _cmd_kanban(args: argparse.Namespace) -> None:
    from cogent_kanban import list_tasks, task_count, COLUMNS
    if args.action == "list":
        tasks = list_tasks(column=args.column)
        if args.json:
            data = [{"id": t.id, "title": t.title, "column": t.column,
                     "priority": t.priority} for t in tasks]
            print(json.dumps(data, indent=2))
            return
        print(f"Tasks ({len(tasks)}):")
        for t in tasks:
            print(f"  [{t.column}] {t.title[:60]} ({t.priority})")
    elif args.action == "count":
        counts = {}
        for col in COLUMNS:
            n = task_count(col)
            if n:
                counts[col] = n
        if args.json:
            print(json.dumps(counts))
            return
        print("Task counts:")
        for col, n in counts.items():
            print(f"  {col}: {n}")
    elif args.action == "summary":
        from cogent_kanban import kanban_summary
        print(kanban_summary())


def _cmd_cache(args: argparse.Namespace) -> None:
    from cogent_cache import cache_list, cache_clear
    if args.action == "list":
        entries = cache_list()
        if args.json:
            print(json.dumps(entries, indent=2))
            return
        if not entries:
            print("Cache is empty")
            return
        print(f"Cache entries ({len(entries)}):")
        for e in entries:
            expired = " (expired)" if e["expired"] else ""
            print(f"  {e['key']} — {e['age']}s / {e['ttl']}s TTL{expired}")
    elif args.action == "clear":
        count = cache_clear()
        print(f"Cleared {count} expired cache entries")


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
            print("No processes")
            return
        print(f"Processes ({len(procs)}):")
        for p in procs:
            print(f"  {p.pid:>6d}  {p.status:<10s}  {p.label or p.command[:40]}")
    elif args.action == "reap":
        count = reap_stale()
        print(f"Reaped {count} stale processes")


def _cmd_status(args: argparse.Namespace) -> None:
    """Show aggregated system status."""
    from cogent_config import get_config
    from cogent_constants import PROJECT_ROOT, MEMORY_DIR

    cfg = get_config()
    info = {
        "cogent_root": str(PROJECT_ROOT),
        "model": cfg.model_name,
        "db_name": cfg.db_name,
        "log_level": cfg.log_level,
        "max_turns": cfg.max_turns,
    }

    # Add directory sizes
    dirs = {}
    for d in [PROJECT_ROOT / "memory" / "cache",
              PROJECT_ROOT / "memory" / "sessions",
              PROJECT_ROOT / "memory" / "loops"]:
        if d.is_dir():
            size = sum(f.stat().st_size for f in d.glob("**/*") if f.is_file())
            dirs[d.name] = size
    info["directories"] = dirs

    if args.json:
        print(json.dumps(info, indent=2))
        return

    print("Cogent Status")
    print(f"  Root:     {info['cogent_root']}")
    print(f"  Model:    {info['model']}")
    print(f"  DB:       {info['db_name']}")
    print(f"  Log:      {info['log_level']}")
    print(f"  Max turn: {info['max_turns']}")
    for name, size in dirs.items():
        print(f"  {name}: {size / 1024:.0f} KB")


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
            print(f"{args.key}: {val}")
        else:
            info = {"model_name": cfg.model_name, "model_base_url": cfg.model_base_url,
                    "db_name": cfg.db_name, "mongo_url": cfg.mongo_url,
                    "log_level": cfg.log_level, "max_turns": cfg.max_turns}
            if args.json:
                print(json.dumps(info, indent=2, default=str))
                return
            for k, v in info.items():
                print(f"  {k}: {v}")
    elif args.action == "set" and args.key and args.value:
        set_override(args.key, args.value)
        print(f"Set {args.key} = {args.value}")
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
        print("No logs directory found")
        return

    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        print("No log files found")
        return

    if args.action == "clear":
        import shutil
        for f in log_files:
            f.unlink()
        print(f"Cleared {len(log_files)} log files")
        return

    latest = log_files[0]
    if args.action == "show":
        lines = latest.read_text(encoding="utf-8").splitlines()
        for line in lines[-args.lines:]:
            print(line)
    elif args.action == "tail":
        import subprocess
        subprocess.run(["tail", "-n", str(args.lines), "-f", str(latest)])


def _cmd_memory(args: argparse.Namespace) -> None:
    """Manage file-based memory."""
    from cogent_memory import remember, recall, memory_summary
    if args.action == "show":
        text = memory_summary()
        if args.json:
            print(json.dumps({"memory": text}, indent=2))
            return
        print(text or "No memory stored")
    elif args.action == "set" and args.key and args.value:
        remember(args.key, args.value)
        print(f"Stored memory: {args.key}")
    elif args.action == "delete" and args.key:
        remember(args.key, "")  # Overwrite with empty
        print(f"Deleted memory: {args.key}")
    elif args.action == "list":
        text = memory_summary()
        if args.json:
            print(json.dumps({"memory": text}, indent=2))
            return
        print(text or "No memory stored")


def _cmd_checkpoints(args: argparse.Namespace) -> None:
    """Manage state snapshots."""
    from cogent_checkpoints import create_snapshot, list_snapshots, clean_snapshots
    if args.action == "list":
        snaps = list_snapshots()
        if args.json:
            print(json.dumps(snaps, indent=2, default=str))
            return
        if not snaps:
            print("No snapshots")
            return
        print(f"Snapshots ({len(snaps)}):")
        for s in snaps[-20:]:
            label = s.get("label", "") or s.get("name", "")
            print(f"  {label}")
    elif args.action == "create":
        name = args.name or f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = create_snapshot(name)
        print(f"Created snapshot: {result}")
    elif args.action == "clean":
        count = clean_snapshots(keep=args.keep)
        print(f"Cleaned, keeping {args.keep} snapshots")


def _cmd_blueprints(args: argparse.Namespace) -> None:
    """List available task blueprints."""
    from blueprint_catalog import BLUEPRINTS
    if args.action == "list":
        if args.json:
            print(json.dumps([{"name": b["name"], "description": b["description"]}
                             for b in BLUEPRINTS], indent=2))
            return
        print(f"Blueprints ({len(BLUEPRINTS)}):")
        for b in BLUEPRINTS:
            print(f"  {b['name']} — {b['description'][:80]}")
    elif args.action == "show" and args.name:
        for b in BLUEPRINTS:
            if b["name"] == args.name:
                if args.json:
                    print(json.dumps(b, indent=2, default=str))
                    return
                print(json.dumps(b, indent=2, default=str))
                return
        print(f"Blueprint '{args.name}' not found")


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
                print("No skills installed")
                return
            print(f"Installed skills ({len(skills)}):")
            for s in skills:
                name = s.get("name", s.get("title", "?"))
                print(f"  {name}")
        except Exception as e:
            print(f"Error reading skills: {e}")
    elif args.action == "install" and args.repo:
        try:
            import skill_forge as sf
            result = sf.import_skill(args.repo, force=("--force" in (args.extra or "")))
            print(f"Installed skill from {args.repo}: {result}")
        except Exception as e:
            print(f"Error installing skill: {e}")
    elif args.action == "remove" and args.name:
        try:
            import skill_forge as sf
            sf.delete_skill(args.name)
            print(f"Removed skill: {args.name}")
        except Exception as e:
            print(f"Error removing skill: {e}")
    elif args.action == "catalog":
        try:
            from skills_catalog import catalog_summary
            print(catalog_summary())
        except ImportError:
            print("Skills catalog not available")
