<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/Cogent-AI%20Coworker-7c5cf5?style=for-the-badge&logo=python&logoColor=white">
    <img alt="Cogent" src="https://img.shields.io/badge/Cogent-AI%20Coworker-7c5cf5?style=for-the-badge&logo=python&logoColor=white">
  </picture>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/github/stars/mike/cogent?style=flat&logo=github" alt="Stars"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.12+-blue?logo=python" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React"></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI"></a>
  <a href="#"><img src="https://img.shields.io/badge/MongoDB-Motor-47A248?logo=mongodb" alt="MongoDB"></a>
  <a href="#"><img src="https://img.shields.io/badge/MCP-Registry-000000?logo=github" alt="MCP"></a>
  <a href="#"><img src="https://img.shields.io/badge/SSE-Streaming-FF6B6B" alt="SSE"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-green" alt="License"></a>
</p>

<p align="center">
  <b>Cogent</b> — An AI-powered coworker that ships real work.<br>
  Not a chatbot. A colleague who researches, writes documents, builds web apps,<br>
  remembers facts, schedules recurring tasks, deploys MCP servers,<br>
  activates skills, and refines output through a Plan→Execute→Verify loop.
</p>

---

## Features

### Core AI Loop

- **Plan→Execute→Verify** — every task runs through an iterative refinement loop with maker/checker split, budget management, and circuit-breaker stagnation detection
- **Multi-turn tool use** — Cogent uses tools autonomously (web search, PDF generation, webapp deployment, memory, scheduling, skills, MCP) via OpenAI-compatible function calling
- **SSE streaming** — granular real-time events: `status`, `tool`, `tool_result`, `artifact`, `reasoning`, `provider`, `loop`, `final`, `done`
- **Provider fallback chain** — VirtualProvider auto-fails over on 429/5xx across 6 providers (KiloCode, OpenRouter, OpenCode Zen, Ollama local/cloud)
- **Headroom compression** — optional 60–95% token reduction before LLM calls (CCR-reversible)
- **Context compression** — token-aware summarization of old turns to stay within budget

### GUI + TUI

| Interface | Stack | Purpose |
|-----------|-------|---------|
| **React UI** | React 19 + shadcn/ui + Tailwind + CRACO | Full chat interface at `localhost:3000/app` |
| **Terminal TUI** | OpenTUI (TypeScript + Zig core) | Terminal client at `tui/`, `cogent` CLI |

### Agent Skills System

- **Discover** skills from `.cogent/skills/` (portable SKILL.md format per agentskills.io)
- **Import** from any GitHub repo that contains SKILL.md files
- **Forge** new skills via LLM analysis of any code repository
- **Activate** skills at runtime via `activate_skill` tool call
- **Resource bundles** — skills carry scripts, references, and assets in subdirectories
- **Optional catalog** — `optional-skills/` with curated categories: security (code-audit, threat-model), devops (docker-management), research (web-research)
- **Dual discovery** — system skills in `.agents/skills/` + `.cogent/skills/`, configurable via `COGENT_SKILLS_PATHS`

### GitHub MCP Registry Integration

Cogent integrates directly with [github.com/mcp](https://github.com/mcp) — the official GitHub MCP server registry:

- **Browse & search** — 350+ servers with language/topic filtering, pagination
- **Auto-detect install** — reads `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` to determine the exact install method
- **Multi-method fallback** — npx → npm → pip → uvx → cargo → go install → source → docker
- **One-click install** — runs the package manager, writes `manifest.yaml` with MCP config
- **Runtime config** — update server configs post-install via the UI
- **Installed server catalog** — 12 pre-installed servers (Linear, n8n, Playwright, Notion, Context7, netdata, markitdown, GitHub MCP, Apify, Upstash)

### File Extraction

| Format | Library | Notes |
|--------|---------|-------|
| PDF | `pypdf` | Full text extraction |
| CSV/TSV | Native | Capped at 200 rows |
| Excel | `openpyxl` | Up to 5 sheets, 150 rows each |
| Code/text | Native | `.py`, `.js`, `.ts`, `.md`, `.json`, `.html`, `.log`, `.yaml`, `.css` |

### Scheduled Tasks

- APScheduler-backed recurring tasks (`daily`, `weekly`, `monthly`)
- Cron storage with output history in `memory/cron/`
- Blueprint catalog with 8 templates (news briefing, market report, etc.)
- Manual "Run now" trigger from UI

### Memory

- File-based long-term memory (`memory/memories/MEMORY.md`, `USER.md`)
- Cross-session key-value recall
- CRUD API for management
- Auth token store (`memory/auth.json`)
- Cache layer (`memory/cache/`) with TTL support

### Kanban Task Board

- Columns: backlog → ready → in_progress → review → done → archived
- Priorities: critical, high, medium, low, none
- Comments, tags, event history, lifecycle tracking

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Frontend (React 19 + shadcn/ui)              │
│  Port 3000 · Dark theme · SSE streaming · Drag-drop uploads      │
│  Panels: Chat, Memory, Tasks, Skills, MCP Registry               │
│  gateway.ts — SSE event client (Fetch + ReadableStream)          │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + Python 3.12)                │
│  Port 8000                                                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Core Layer                                              │    │
│  │  server.py        — Routes, CORS, middleware             │    │
│  │  llm_service.py   — LLM loop, SSE streaming, tool parse  │    │
│  │  tools.py         — 18+ tool implementations             │    │
│  │  loop_engine.py   — Plan→Execute→Verify state machine    │    │
│  │  cogent_prompt.py — Structured system prompt builder     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Infrastructure Layer                                   │    │
│  │  cogent_config.py     — 3-layer config (YAML+env+override) │  │
│  │  cogent_providers.py  — VirtualProvider + fallback chain │    │
│  │  cogent_gateway.py    — SSE delivery router              │    │
│  │  cogent_acp.py        — Agent Communication Protocol     │    │
│  │  cogent_hooks.py      — 9 lifecycle hook points          │    │
│  │  cogent_services.py   — Auxiliary service router         │    │
│  │  cogent_headroom.py   — Headroom compression integration │    │
│  │  cogent_logging.py    — Rotating file handlers           │    │
│  │  cogent_budget.py     — Iteration + token budget tracker │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  State & Persistence Layer                              │    │
│  │  cogent_state.py      — JSON-file-backed sessions       │    │
│  │  cogent_memory.py     — §-delimited markdown KV store   │    │
│  │  cogent_kanban.py     — Task board                      │    │
│  │  cogent_cron.py       — Cron jobs + output history      │    │
│  │  cogent_auth.py       — Credential token store          │    │
│  │  cogent_cache.py      — TTL-based file cache            │    │
│  │  cogent_checkpoints.py — State snapshots for rollback   │    │
│  │  cogent_processes.py  — Background process registry     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Agent & Tools Layer                                    │    │
│  │  agent/              — TurnContext, ContextCompressor   │    │
│  │  agent_skills.py     — Skill discovery + activation     │    │
│  │  skills_catalog.py   — Installed + optional skills      │    │
│  │  skill_forge.py      — Import/forge skills from GitHub  │    │
│  │  tools_registry.py   — Hermes-style tool registry       │    │
│  │  agent_reach_tools.py— YouTube, GitHub, RSS, V2EX,Bili  │    │
│  │  firecrawl_service.py— Web search + scrape via Firecrawl│    │
│  │  blueprint_catalog.py— 8 task blueprint templates       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  MCP Registry Layer                                     │    │
│  │  mcp_registry.py   — GitHub MCP registry fetch + cache  │    │
│  │                     Auto-detect install methods         │    │
│  │                     Install + remove + config MCP servers│    │
│  │  optional-mcps/    — 12 pre-installed server manifests  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CLI Layer                                              │    │
│  │  cli/main.py — server, tools, auth, cron, kanban,       │    │
│  │                cache, processes, status, config, logs,   │    │
│  │                memory, checkpoints, blueprints, skills   │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────────────┘
                 │
          ┌──────┴──────┐
          ▼              ▼
    ┌──────────┐   ┌──────────┐
    │ MongoDB  │   │ KiloCode │
    │ (Motor)  │   │  (LLM)   │
    └──────────┘   └──────────┘
```

### Persistence Layout

```
memory/
├── loops/            # Loop state (per-session JSON)
├── sessions/         # Session index + metadata
├── memories/         # Long-term memory (MEMORY.md, USER.md)
├── kanban.json       # Task board
├── auth.json         # Stored credentials
├── processes.json    # Process registry
├── cache/            # TTL-based file cache
├── snapshots/        # State snapshots
├── cron/             # Cron job definitions + output history
│   ├── jobs.json
│   └── output/
└── cogent.json       # General state

optional-skills/      # Curated skill catalog (security, devops, research)
optional-mcps/        # MCP server catalog entries (12 servers)
datagen/              # Batch data generation configs
scripts/              # Install, setup, test, and utility scripts
sandboxes/            # Container sandbox staging
```

---

## Quick Start

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+ / npm 9+
- **MongoDB** — local or Atlas
- **KiloCode API key** — from [kilo.app](https://kilo.app) (or any OpenAI-compatible endpoint)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add KILOCODE_API_KEY and MONGO_URL
```

### 2. MongoDB

```bash
docker run -d -p 27017:27017 --name cogent-mongo mongo:7
```

### 3. Start Backend

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000/api`

### 4. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
echo "REACT_APP_BACKEND_URL=http://localhost:8000" > .env.local
npm start
```

Opens at `http://localhost:3000`. Navigate to `/app` for the chat.

### 5. TUI (optional)

```bash
cd tui && bun install && bun run build
./bin/cogent --url http://localhost:8000
```

### 6. Verify

```bash
curl http://localhost:8000/api/
# → {"service":"cogent","status":"ok"}
```

---

## Virtual Provider Chain

Cogent routes LLM calls through a priority-ordered fallback chain. When one provider returns 429 or 5xx, the next is tried automatically.

| Priority | Provider | Model | API Key Env |
|----------|----------|-------|-------------|
| 1 | KiloCode | `nex-agi/nex-n2-pro:free` | `KILOCODE_API_KEY` |
| 2 | OpenRouter | `openrouter/owl-alpha` | `OPENROUTER_API_KEY` |
| 3 | OpenCode Zen | `deepseek-v4-flash-free` | `OPENCODE_API_KEY` |
| 4 | KiloCode (alt) | `nvidia/nemotron-3-ultra` | `KILOCODE_API_KEY` |
| 5 | Ollama Cloud | `glm-5.2:cloud` | `OLLAMA_API_KEY` |
| 6 | Ollama Local | `qwen3.6` | `OLLAMA_API_KEY` |

Rate limiting (5–7s randomized delay) prevents free-tier quota exhaustion.

---

## MCP Registry

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/mcp/registry` | Browse GitHub MCP registry (search, filter by language/topic) |
| `POST` | `/api/mcp/registry/sync` | Sync latest server list from GitHub |
| `GET` | `/api/mcp/server/{id}` | Server detail + README + install methods |
| `GET` | `/api/mcp/installed` | List installed MCP servers |
| `POST` | `/api/mcp/install` | Install an MCP server (auto-detect method) |
| `POST` | `/api/mcp/remove` | Remove an installed MCP server |
| `POST` | `/api/mcp/config` | Update runtime config |
| `GET` | `/api/mcp/languages` | Language breakdown |
| `GET` | `/api/mcp/topics` | Topic frequency |
| `GET` | `/api/mcp/servers/available` | Registry sync status + Docker availability |

### Install Methods

Cogent auto-detects the best install method from the GitHub package manifest:

- **npx** → auto-converted to `npm install -g` for install, npx for runtime
- **pip / uvx** — Python packages
- **cargo** — Rust crates
- **go install** — Go modules
- **gem** — Ruby gems
- **source** — git clone + build
- **docker** — ghcr.io container

### Pre-Installed Servers

Apify, Context7, GitHub MCP, Linear, markitdown, n8n, netdata, Notion, Playwright, Upstash Context7

---

## Agent Skills

### Quick Start

```bash
# Import skills from any GitHub repo
curl -X POST /api/skills/import -d '{"repo_url": "https://github.com/user/skill-repo"}'

# Forge a new skill from a code repo (LLM-generates SKILL.md)
curl -X POST /api/skills/forge -d '{"repo_url": "https://github.com/user/code-repo"}'

# List installed skills
curl /api/skills
```

### Skill Structure

Each skill lives in its own directory with a `SKILL.md` file:

```
.cogent/skills/
└── my-skill/
    ├── SKILL.md          # Instructions + YAML frontmatter (name, description)
    ├── references/       # Reference files (loaded via read_skill_resource)
    ├── scripts/          # Helper scripts
    └── assets/           # Images, templates, etc.
```

Skill format follows the [agentskills.io](https://agentskills.io) portable specification.

---

## Loop Engineering

Every task runs through Cogent's Plan→Execute→Verify state machine:

| Phase | Purpose |
|-------|---------|
| **Plan** | Accept task, establish criteria |
| **Execute** | Work via tool calls, thinking, generation |
| **Verify** | Maker/checker split self-verifies against criteria |
| **Refine** | On partial/fail, incorporates feedback and retries (up to 90 iterations) |

Safety features: circuit breaker (CLOSED/HALF_OPEN/OPEN), same-args detection, consecutive-failure guard, token budget enforcement (~100K per task).

---

## API Reference

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create session |
| `DELETE` | `/api/sessions/{id}` | Delete session and messages |

### Messages

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions/{id}/messages` | List messages |
| `POST` | `/api/sessions/{id}/messages` | Send (non-streaming) |
| `POST` | `/api/sessions/{id}/messages/stream` | Send (SSE streaming) |

### Memory & Tasks

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST/DELETE` | `/api/memory` | Key-value memory CRUD |
| `GET/DELETE` | `/api/tasks` | List/delete scheduled tasks |
| `POST` | `/api/tasks/{id}/run` | Trigger immediate execution |

### Loop Engineering

| Method | Path | Description |
|--------|------|-------------|
| `GET/DELETE` | `/api/sessions/{id}/loop` | Get/reset loop state |
| `GET` | `/api/loops` | All active loops |

### Files & Artifacts

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/uploads` | Upload file (multipart) |
| `GET` | `/api/artifact/{id}` | Serve artifact (PDF inline, `?dl=1` download) |

### Skills

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/skills` | List installed |
| `GET/DELETE` | `/api/skills/{name}` | Detail / remove |
| `POST` | `/api/skills/import` | Import from GitHub repo |
| `POST` | `/api/skills/forge` | Forge from repo analysis |

### SSE Event Types

```json
{"type": "status",     "content": "thinking"}
{"type": "loop",       "data": {"phase": "execute", "iteration": 1}}
{"type": "tool",       "data": {"tool": "web_search", "args": {...}}}
{"type": "tool_result","data": {"tool": "web_search", "summary": "..."}}
{"type": "artifact",   "data": {"id": "...", "type": "pdf", "url": "/api/artifact/..."}}
{"type": "reasoning",  "content": "thinking step..."}
{"type": "provider",   "data": {"from": "kilocode", "to": "openrouter", "reason": "429 rate limited"}}
{"type": "final",      "content": "Here's the result..."}
{"type": "done",       "data": {"message": {...}}}
```

---

## Configuration

### `config.yaml` (3-layer: defaults → YAML → env)

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `model` | `provider` | `kilocode` | Default LLM provider |
| `model` | `base_url` | KiloCode API | OpenAI-compatible endpoint |
| `agent` | `max_turns` | `50` | Max tool-using turns per message |
| `agent` | `max_iterations` | `90` | Max Plan→Execute→Verify cycles |
| `rate_limit` | `min/max_delay_ms` | `5000/7000` | Inter-request delay range |
| `web` | `search_backend` | `firecrawl` | Web search engine |
| `headroom` | `enabled` | `true` | Enable Headroom compression |
| `mcp` | `enabled` | `true` | MCP registry integration |

See `config.yaml` for the full 114-line configuration reference.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Motor (async MongoDB) |
| LLM | KiloCode API, OpenRouter, OpenCode Zen, Ollama |
| Frontend | React 19, shadcn/ui, Tailwind CSS, CRACO |
| TUI | OpenTUI (TypeScript + Zig) |
| Scheduler | APScheduler (asyncio) |
| PDF | ReportLab |
| Web search | Firecrawl (cloud or self-hosted) |
| File extract | pypdf, openpyxl |
| Web scraping | Firecrawl |
| Content channels | yt-dlp, gh CLI, feedparser, bili-cli |
| Compression | Headroom (CCR) |

---

## Development

```bash
# Run tests
cd backend && python -m pytest tests/ -v

# Create a skill
POST /api/skills/import  {"repo_url": "https://github.com/user/repo"}
POST /api/skills/forge   {"repo_url": "https://github.com/user/repo"}
```

### Project Structure

```
cogent/
├── AGENT.md               # AI agent instructions
├── AGENTS.md               # Agent topology & delegation protocols
├── SOUL.md                 # Agent personality definition
├── config.yaml             # 114-line central configuration
├── backend/
│   ├── server.py           # FastAPI + 40+ route endpoints
│   ├── llm_service.py      # LLM loop + SSE streaming
│   ├── tools.py            # 18 tool implementations
│   ├── loop_engine.py      # Plan→Execute→Verify state machine
│   ├── cogent_config.py    # 3-layer config loader
│   ├── cogent_providers.py # VirtualProvider + fallback chain
│   ├── cogent_memory.py    # File-based KV memory
│   ├── cogent_gateway.py   # SSE delivery router
│   ├── cogent_acp.py       # ACP adapter
│   ├── cogent_hooks.py     # 9 lifecycle hook points
│   ├── cogent_services.py  # Auxiliary service router
│   ├── mcp_registry.py     # GitHub MCP registry integration
│   ├── agent_skills.py     # Skill discovery + activation
│   ├── skills_catalog.py   # Catalog installed + optional skills
│   ├── skill_forge.py      # Import/forge skills from GitHub
│   ├── tools_registry.py   # Hermes-style tool registry
│   ├── agent_reach_tools.py# YouTube, GitHub, RSS, V2EX, Bilibili
│   ├── firecrawl_service.py# Web search + scrape
│   ├── blueprint_catalog.py# 8 task blueprint templates
│   ├── agent/              # TurnContext, ContextCompressor
│   ├── cli/                # 14 management commands
│   └── hooks/              # Auto-discovered hook scripts
├── frontend/
│   ├── src/chat/           # ChatApp, Sidebar, MCPPanel, SkillsPanel
│   └── src/lib/gateway.ts  # SSE gateway client
├── tui/                    # Terminal UI (OpenTUI)
├── .cogent/skills/         # Installed agent skills
├── optional-skills/        # Curated skill catalog
├── optional-mcps/          # MCP server manifests
├── memory/                 # All state persistence
├── datagen/                # Batch generation configs
├── scripts/                # Utility scripts
└── tests/                  # Python test suite
```

---

## License

MIT
