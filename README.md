# Cogent — the AI coworker

An AI-powered coworker that ships real work. Not a chatbot — a colleague who researches, writes documents, builds web apps, remembers facts, schedules recurring tasks, reads your files, and refines its output through a Plan→Execute→Verify loop.

Built on **FastAPI** + **MongoDB** + **React** (shadcn/ui). Driven by KiloCode-hosted LLMs via OpenAI-compatible API.

---

## Features

### Core AI interactions
- **Chat with tool-use** — Cogent uses tools autonomously (web search, PDF generation, web app deployment, memory, scheduling) via a multi-turn tool-calling loop
- **Streaming responses (SSE)** — real-time streaming with granular events: status updates, tool calls, tool results, artifacts, and loop phase transitions
- **File attachments** — upload PDF, CSV, Excel, images, or code files; extracted text is inlined into the LLM context
- **Conversation history** — persisted per-session, reloaded across page visits

### Tools (LLM-operated)
| Tool | What it does |
|---|---|
| `web_search` | Live internet search via DuckDuckGo |
| `generate_pdf` | Designed PDF reports with KPIs, tables, callouts, charts |
| `generate_webapp` | Build and deploy single-file HTML web apps |
| `save_memory` | Persist facts about the user across sessions |
| `recall_memory` | Retrieve stored facts in future conversations |
| `schedule_task` | Set up recurring tasks (cron-based) that Cogent runs autonomously |
| `activate_skill` | Load and activate an installed agent skill |
| `read_skill_resource` | Read reference files bundled with a skill |
| `get_loop_state` | Return the current loop-engineering state for the session |

### Loop engineering (Plan→Execute→Verify)
Every task runs through an iterative refinement loop:
1. **Plan** — the task is accepted and criteria established
2. **Execute** — Cogent works (tool calls, thinking, generating)
3. **Verify** — a maker/checker split self-verifies the output against criteria
4. **Refine** — on partial/fail, Cogent incorporates verification feedback and retries (up to 5 iterations)

The loop state is tracked per session and visible in the UI as phase badges with iteration counters and verdict indicators.

### Memory
- Persist key-value facts (`save_memory` / `recall_memory`)
- CRUD API for managing stored memories
- Cross-session recall — facts saved in one session are available in future ones

### Scheduled tasks
- Create recurring tasks with a prompt, cadence (`daily`, `weekly`, `monthly`), and time
- APScheduler-backed execution: Cogent runs the task autonomously on schedule
- Manual "Run now" trigger via the UI

### Agent skills system
- Discover and catalog skills from `.cogent/skills/` directories
- Install skills by importing from GitHub repos (auto-detect `SKILL.md`)
- Forge new skills by analyzing any code repository via LLM
- Import/forge endpoints for programmatic skill management

### File extraction
Extracts text from:
- **PDF** (via `pypdf`)
- **CSV / TSV** (capped at 200 rows)
- **Excel** `.xlsx` / `.xls` (via `openpyxl`, up to 5 sheets, 150 rows each)
- **Plain text**: `.txt`, `.md`, `.json`, `.html`, `.log`, `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.css`, `.yaml`, `.yml`

### Frontend
- Dark-themed chat UI with shadcn/ui components
- Session management (create, list, delete conversations)
- Real-time streaming with status indicators, tool badges, artifact cards, and loop phase visualization
- Sidebar panels for memory, scheduled tasks, and installed skills
- Drag-and-drop file attachments

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│    React + shadcn/ui + Tailwind + CRACO          │
│    Port 3000 (dev)                               │
│    REACT_APP_BACKEND_URL → backend               │
└────────────────┬────────────────────────────────┘
                 │ HTTP / SSE
                 ▼
┌─────────────────────────────────────────────────┐
│                 Backend (FastAPI)                 │
│    Port 8000                                     │
│                                                   │
│    server.py       — routes, CORS, middleware     │
│    llm_service.py  — LLM loop, tool parsing, SSE  │
│    tools.py        — tool implementations         │
│    loop_engine.py  — Plan→Execute→Verify state    │
│    skill_forge.py  — import/forge skills          │
│    agent_skills.py — skill discovery & catalog    │
│    scheduler.py    — APScheduler recurring tasks  │
│    file_extract.py — document text extraction     │
└────────────────┬────────────────────────────────┘
                 │
          ┌──────┴──────┐
          ▼              ▼
     ┌──────────┐  ┌──────────┐
     │ MongoDB  │  │ KiloCode │
     │ (Motor)  │  │  (LLM)   │
     └──────────┘  └──────────┘
```

### Backend modules

| Module | Responsibility |
|---|---|
| `server.py` | FastAPI app, route definitions, upload handling, artifact serving |
| `llm_service.py` | LLM chat loop, tool-call parsing, SSE event streaming, loop integration |
| `tools.py` | All tool implementations (web search, PDF, webapp, memory, schedule, skills) |
| `loop_engine.py` | Loop state machine, maker/checker verification, budget management |
| `skill_forge.py` | GitHub repo parsing, SKILL.md scanning, LLM-assisted skill generation |
| `agent_skills.py` | Skill discovery from `.cogent/skills/`, frontmatter parsing, resource serving |
| `scheduler.py` | APScheduler integration for recurring task execution |
| `file_extract.py` | Document text extraction for attachment processing |

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+ / npm 9+
- **MongoDB** — local or remote (Atlas)
- **KiloCode API key** — from [kilo.app](https://kilo.app) (or any OpenAI-compatible endpoint)

---

## Quick start

### 1. Clone and set up the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env     # create if it doesn't exist
```

Edit `.env`:

```env
KILOCODE_API_KEY=sk-...          # required — KiloCode or OpenAI-compatible key
MONGO_URL=mongodb://localhost:27017
DB_NAME=cogent
```

### 3. Start MongoDB

```bash
# local install
mongod --dbpath /var/lib/mongodb

# or via Docker
docker run -d -p 27017:27017 --name cogent-mongo mongo:7
```

### 4. Start the backend

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API available at `http://localhost:8000/api`

### 5. Set up and start the frontend

```bash
cd frontend
npm install --legacy-peer-deps
```

Create `frontend/.env.local`:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

```bash
npm start
```

Opens at `http://localhost:3000`. Navigate to `/app` for the chat interface.

### 6. Verify it works

```bash
curl http://localhost:8000/api/
# → {"service":"cogent","status":"ok"}
```

---

## Project structure

```
cogent/
├── backend/
│   ├── server.py              # FastAPI app + routes
│   ├── llm_service.py         # LLM loop + SSE streaming
│   ├── tools.py               # tool implementations
│   ├── loop_engine.py         # Plan→Execute→Verify state machine
│   ├── skill_forge.py         # import/forge skills from GitHub
│   ├── agent_skills.py        # skill discovery and catalog
│   ├── scheduler.py           # recurring task scheduler
│   ├── file_extract.py        # document extraction
│   ├── requirements.txt
│   ├── .env                   # backend config
│   ├── artifacts/             # generated PDFs and web apps
│   └── uploads/               # uploaded files
├── frontend/
│   ├── src/
│   │   ├── chat/              # chat UI (ChatThread, Sidebar, SkillsPanel…)
│   │   ├── components/        # shared UI (Navbar, Hero, Feature sections…)
│   │   ├── hooks/             # React hooks
│   │   ├── lib/               # utilities
│   │   ├── App.js             # router (landing + /app/*)
│   │   └── index.js           # entry point
│   ├── public/
│   ├── package.json
│   ├── craco.config.js
│   └── tailwind.config.js
├── .cogent/
│   └── skills/                # installed agent skill definitions
├── memory/
│   └── loops/                 # loop state persistence (per-session JSON)
├── tests/
│   ├── test_agent_skills.py
│   └── test_llm_service.py
└── test_result.md             # testing protocol + results log
```

---

## API reference

### Sessions

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create session |
| `DELETE` | `/api/sessions/{id}` | Delete session and messages |

### Messages

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions/{id}/messages` | List messages in session |
| `POST` | `/api/sessions/{id}/messages` | Send message (non-streaming) |
| `POST` | `/api/sessions/{id}/messages/stream` | Send message (SSE streaming) |

### Memory

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/memory` | List all stored memories |
| `POST` | `/api/memory` | Create/update memory `{key, value}` |
| `DELETE` | `/api/memory/{key}` | Delete memory |

### Scheduled tasks

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tasks` | List all scheduled tasks |
| `DELETE` | `/api/tasks/{id}` | Remove task |
| `POST` | `/api/tasks/{id}/run` | Trigger immediate execution |

### Skills

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/skills` | List installed skills |
| `GET` | `/api/skills/{name}` | Get skill detail |
| `DELETE` | `/api/skills/{name}` | Remove skill |
| `POST` | `/api/skills/import` | Import skills from a GitHub repo |
| `POST` | `/api/skills/forge` | Generate skill from repo analysis |

### Loop engineering

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions/{id}/loop` | Get loop state for session |
| `DELETE` | `/api/sessions/{id}/loop` | Reset loop state |
| `GET` | `/api/loops` | List all active loop states |

### Files & artifacts

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/uploads` | Upload file (multipart) |
| `GET` | `/api/artifact/{id}` | Serve artifact (PDF inline, ?dl=1 to download) |

### SSE event format

```json
{"type": "status",   "content": "thinking"}
{"type": "loop",     "data": {"phase": "execute", "iteration": 1}}
{"type": "tool",     "data": {"tool": "web_search", "args": {...}, "summary": ""}}
{"type": "tool_result", "data": {"tool": "web_search", "summary": "..."}}
{"type": "artifact", "data": {"id": "...", "type": "pdf", "title": "...", "url": "/api/artifact/...", "size_kb": 42}}
{"type": "loop",     "data": {"phase": "verify", "verdict": "PASS", "notes": "...", "iteration": 1}}
{"type": "final",    "content": "Here's the result..."}
{"type": "loop",     "data": {"phase": "done"}}
{"type": "done",     "data": {"message": {...}}}    // persisted message object
```

---

## Configuration

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `KILOCODE_API_KEY` | yes | — | KiloCode or OpenAI-compatible API key |
| `MONGO_URL` | yes | — | MongoDB connection string |
| `DB_NAME` | no | `cogent` | MongoDB database name |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `REACT_APP_BACKEND_URL` | yes | — | Backend base URL (e.g. `http://localhost:8000`) |

---

## Development

### Running tests

```bash
cd backend
python -m pytest tests/ -v
```

### Creating agent skills

Cogent discovers skills from `.cogent/skills/` directories. Each skill is a directory containing a `SKILL.md` file with YAML frontmatter. Skills can be:

- **Imported** from a GitHub repo containing `SKILL.md` files
- **Forged** via LLM analysis of a code repository

```bash
POST /api/skills/import  {"repo_url": "https://github.com/user/repo"}
POST /api/skills/forge   {"repo_url": "https://github.com/user/repo"}
```

### Loop engineering

The loop state persists to `memory/loops/{session_id}.json`. Reset with:

```bash
DELETE /api/sessions/{id}/loop
```

Each session's loop operates independently with:
- Max 5 iterations per task
- Token budget of ~200K tokens per task
- Maker/checker verification against criteria

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3, FastAPI, Motor (async MongoDB driver) |
| LLM | KiloCode API (OpenAI-compatible), Claude Sonnet |
| Frontend | React 19, shadcn/ui, Tailwind CSS, CRACO, axios |
| Scheduler | APScheduler (async) |
| PDF | ReportLab |
| Web search | DuckDuckGo (via duckduckgo_search) |
| File extract | pypdf, openpyxl |

---

## Terminal UI (OpenTUI)

Cogent includes a terminal-based user interface powered by [OpenTUI](https://opentui.com) — a TypeScript library on a native Zig core. Use it as an alternative to the React web UI when working in the terminal.

### Quick start

```bash
# From the project root
cd tui && bun install && bun run build

# Run the TUI (server must be running separately)
./bin/cogent
# or
bun run start

# Start with an explicit server URL
./bin/cogent --url http://localhost:8000

# Global install via bun link
cd tui && bun run link
# Now `cogent` is available anywhere
```

### Usage

```
cogent [options]

  -u, --url <url>     Server URL (default: http://localhost:8000)
  -s, --server        Auto-start the Cogent backend server
  -h, --help          Show this help message
  -v, --version       Show version
```

### TUI commands

| Command | Action |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear the conversation |
| `/connect` | Reconnect to server |
| `/quit` | Exit Cogent |

| Key | Action |
|---|---|
| `Ctrl+C` | Exit Cogent |

### Architecture

The TUI is a standalone bundle in `tui/`:

```
tui/
├── bin/cogent              # Global launcher script
├── src/
│   ├── cli.tsx             # Thin entrypoint (--help/--version before OpenTUI)
│   ├── runner/main.tsx     # Main runner (creates renderer, renders App)
│   ├── App.tsx             # Root layout component
│   ├── theme.ts            # Color palette
│   ├── types.ts            # Message type definitions
│   ├── client/gateway.ts   # SSE gateway client
│   ├── hooks/useConversation.ts  # Stateful conversation management
│   └── components/
│       ├── Header.tsx      # ASCII logo + branding
│       ├── ChatArea.tsx    # Scrollable message list
│       ├── InputBar.tsx    # Prompt input
│       └── StatusBar.tsx   # Connection info, counters
├── dist/                   # Built output (cli.js + native .so)
├── package.json
└── tsconfig.json
```

The TUI connects to the Cogent backend via SSE streaming at `/api/sessions/{id}/messages/stream`. It renders chat messages, tool calls, status updates, and loop-engineering events into a scrollable terminal interface.
