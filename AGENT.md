# AGENT.md — Cogent Project Instructions

This file governs how AI coding agents operate within the Cogent repository. All agents must follow these rules when editing, testing, or reviewing code in this project.

## Project overview

Cogent is an AI coworker — a production-grade system that ships real work via a chat interface with autonomous tool-use. It is not a chatbot; it is a platform that researches, writes documents, builds web apps, remembers facts, schedules recurring tasks, reads files, and refines output through a Plan→Execute→Verify loop.

**Stack:** FastAPI (Python 3.12) + MongoDB (Motor) + React (shadcn/ui + Tailwind + CRACO). LLM backend: KiloCode-hosted models via OpenAI-compatible API.

**Repository structure:**

```
cogent/
├── AGENT.md                    # Project instructions (this file)
├── AGENTS.md                   # Agent topology & delegation protocols
├── SOUL.md                     # Agent personality definition
├── config.yaml                 # Central configuration (model, agent, gateway, ACP, MCP, datagen)
│
├── backend/                    # FastAPI Python backend
│   ├── server.py               # Routes, CORS, middleware, startup/shutdown hooks
│   ├── llm_service.py          # LLM chat loop, streaming, tool parsing, memory loading
│   ├── tools.py                # All tool implementations (18 tools)
│   ├── loop_engine.py          # Plan→Execute→Verify state machine
│   ├── skill_forge.py          # Import skills from GitHub
│   ├── agent_skills.py         # Skill discovery & catalog
│   ├── scheduler.py            # APScheduler recurring tasks
│   ├── firecrawl_service.py    # Web scraping service
│   ├── agent_reach_tools.py    # YouTube, GitHub, RSS, V2EX, Bilibili
│   ├── file_extract.py         # Document text extraction
│   │
│   ├── cogent_config.py        # Config loader (YAML + env + overrides)
│   ├── cogent_constants.py     # Well-known paths & constants
│   ├── cogent_logging.py       # Structured logging with rotation
│   ├── cogent_state.py         # Session state (JSON file-backed)
│   ├── cogent_memory.py        # File-based long-term memory
│   ├── cogent_kanban.py        # Task board with columns & priorities
│   ├── cogent_auth.py          # Credential token store
│   ├── cogent_cache.py         # TTL-based file cache
│   ├── cogent_processes.py     # Background process registry
│   ├── cogent_checkpoints.py   # State snapshots & restore
│   ├── cogent_cron.py          # Cron job storage & output history
│   ├── cogent_providers.py     # LLM provider abstraction & registry
│   ├── cogent_budget.py        # Iteration & token budget tracker
│   ├── cogent_services.py      # Auxiliary service router
│   ├── cogent_hooks.py         # Lifecycle hook infrastructure
│   ├── cogent_gateway.py       # SSE delivery router for React UI
│   ├── cogent_acp.py           # Minimal Agent Communication Protocol adapter
│   ├── tools_registry.py       # Hermes-style tool registry
│   ├── skills_catalog.py       # Skill discovery from installed + optional dirs
│   ├── blueprint_catalog.py    # 8 task blueprint templates
│   │
│   ├── agent/                  # Agent core subsystem (Hermes agent/ analog)
│   │   ├── __init__.py         # Exports: TurnContext, ContextCompressor, etc.
│   │   ├── turn_context.py     # Per-turn context dataclass
│   │   ├── context_compressor.py  # Token-aware context compression
│   │   ├── conversation_compression.py  # Full-session summarization
│   │   └── agent_init.py       # Agent bootstrap (session, logging, memory)
│   │
│   ├── cli/                    # Cogent CLI (Hermes hermes_cli/ analog)
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── main.py             # Commands: server, tools, auth, cron, kanban, cache,
│   │                           #           processes, status, config, logs, memory,
│   │                           #           checkpoints, blueprints, skills
│   │
│   ├── hooks/                  # Hook scripts (auto-discovered *.py)
│   ├── artifacts/              # Generated PDFs / web apps
│   ├── uploads/                # Uploaded files
│   └── logs/                   # Rotating log files
│
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── chat/               # Chat UI components
│   │   ├── components/         # Shared UI components
│   │   ├── hooks/              # React hooks
│   │   └── lib/
│   │       └── gateway.ts      # SSE gateway client (Hermes apps/shared/ analog)
│   ├── public/
│   ├── package.json
│   └── craco.config.js
│
├── .cogent/
│   └── skills/                 # Installed agent skill definitions
│
├── memory/
│   ├── loops/                  # Loop state (per-session JSON)
│   ├── sessions/               # Session index & metadata
│   ├── memories/               # File-based memory (MEMORY.md, USER.md)
│   ├── kanban.json             # Task board data
│   ├── auth.json               # Stored credentials
│   ├── processes.json          # Process registry
│   ├── cron/                   # Job definitions + output history
│   │   ├── jobs.json
│   │   └── output/
│   ├── cache/                  # TTL-based file cache
│   └── snapshots/              # State snapshots
│
├── optional-skills/            # Curated skill catalog (17+ categories)
│   ├── DESCRIPTION.md
│   ├── security/
│   ├── devops/
│   └── research/
│
├── optional-mcps/              # MCP server catalog entries
│   ├── linear/manifest.yaml
│   └── n8n/manifest.yaml
│
├── datagen/                    # Batch generation configs (Hermes datagen-config-examples/ analog)
│   ├── browser_tasks.jsonl
│   ├── trajectory_compression.yaml
│   └── web_research.yaml
│
├── scripts/                    # Utility scripts (Hermes scripts/ analog)
│   ├── install.sh
│   ├── setup.sh
│   ├── run_tests.sh
│   └── build_skills_index.py
│
├── sandboxes/                  # Container sandbox staging
├── tests/                      # Python test suite
└── test_reports/               # Test output reports
```

Run:
```bash
cd backend && uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
```

Configure `frontend/.env.local`:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

Run:
```bash
cd frontend && npm start
```

### MongoDB

```bash
docker run -d -p 27017:27017 --name cogent-mongo mongo:7
```

## Testing

### Python tests (backend)

```bash
cd backend
source .venv/bin/activate
pytest ../tests/ -v
```

Key test files:
- `tests/test_llm_service.py` — LLM loop, streaming, tool parsing
- `tests/test_agent_skills.py` — Skill discovery and catalog

### Testing rules

- Add or update tests for any changed logic.
- Run full test suite before marking work complete.
- Prefer pytest fixtures over setUp methods.
- Test behavior, not implementation details. Focus on conditional branches, edge values, and error handling.

## Code conventions

### Backend (Python)

- Python 3.12+. Use modern typing (`list[str]` not `List[str]`, `|` for unions).
- FastAPI async endpoints. Use `async/await` for all route handlers and DB calls.
- Motor async driver for MongoDB. No synchronous PyMongo.
- SSE streaming via `StreamingResponse` + async generators.
- Tool implementations in `tools.py`. Keep parsing in `llm_service.py`.
- Pydantic models for request/response schemas.
- `black` formatting, `ruff` linting.
- No bare `except`. Handle specific exceptions.
- Type hints on all function signatures.

### Frontend (React)

- React 18 with hooks. No class components.
- shadcn/ui components from `components.json`.
- Tailwind CSS for styling. No inline styles.
- CRACO for CRA overrides. Use `npm start` (not `bun`/`yarn`).
- Fetch API for backend calls. SSE via `EventSource`.
- Functional patterns. Prefer `useReducer` for complex state.

### General

- No hardcoded paths. Use relative paths, env vars, or config.
- No emoji in code or comments.
- Markdown for docs. HTML only for `<details>`, `<aside>`.
- `.env` and `.env.*` files are gitignored. Never commit secrets.

## Architecture notes

### Data flow

1. User sends message → `POST /api/sessions/{id}/messages/stream` (SSE)
2. `llm_service.py` builds context, calls LLM, streams response events
3. LLM may request tool calls → parsed, executed, results streamed back
4. Loop engine tracks Plan→Execute→Verify state per session
5. Loop persists to `memory/loops/{session_id}.json`

### Key APIs

| Module | Responsibility |
|---|---|
| `server.py` | FastAPI app, route definitions, middleware |
| `llm_service.py` | LLM loop, SSE event stream, tool call dispatch |
| `tools.py` | All tool implementations (web search, PDF, webapp, memory, schedule, skills) |
| `loop_engine.py` | Loop state machine, maker/checker verification, iteration budget |
| `skill_forge.py` | GitHub repo parsing, SKILL.md scanning, LLM-assisted skill generation |
| `agent_skills.py` | Skill discovery from `.cogent/skills/`, frontmatter parsing, resource serving |

### SSE event types

- `status` — phase transitions, iteration counters
- `tool_start` / `tool_end` — tool call lifecycle
- `content` — streamed text chunks
- `artifact` — generated artifact (PDF, web app URL)
- `loop_phase` — loop state transitions (plan→execute→verify→refine)
- `error` — errors
- `done` — completion

## Security

- `backend/.env` contains `KILOCODE_API_KEY` and `MONGO_URL`. Never expose.
- Uploaded files stored in `backend/uploads/`. Artifacts in `backend/artifacts/`.
- No authentication layer currently. Internal/demo use assumed.
- Loop state files are local JSON. No encryption.
- `file_extract.py` handles untrusted uploads — limit rows/sheets to prevent resource exhaustion.

## LLM integration

- OpenAI-compatible API via KiloCode. Base URL configurable in `.env`.
- `tools.py` defines available functions sent to LLM as tool definitions.
- Tool call format: OpenAI tool-calling standard (`type: "function"`, `function.name`/`function.arguments`).
- Skills can add new tools dynamically via `activate_skill` endpoint.

## Working with this repo

- Always read the relevant source file before editing. Do not assume structure.
- When investigating bugs, reproduce first (check server logs, frontend console), then theorize.
- Run `pytest` after backend changes. Check the frontend compiles with `npm run build`.
- Never change `.env` or commit credentials.
- Keep the README in sync with any structural changes.
- The Plan→Execute→Verify loop is core to Cogent's identity — preserve and respect it in code changes.
