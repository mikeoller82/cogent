# AGENTS.md — Cogent Agent Topology & Delegation Protocols

> Defines the agent roles, capabilities, and interaction patterns
> that Cogent uses to decompose and execute work.  Analogous to
> Hermes' AGENTS.md — an orchestrator-aware layer that lives above
> the raw tool implementations in ``backend/tools.py``.

## 1. Agent Topography

Cogent can operate as a single agent or decompose work across
specialist sub-agents.  The default mode is a single Plan→Execute→Verify
loop in ``backend/llm_service.py``.  When the task is complex or
multi-domain, Cogent delegates to sub-agents:

```
┌──────────────────────────────────────────┐
│           Cogent (Orchestrator)           │
│  Plan → Execute → Verify loop            │
└──────┬──────┬──────┬──────┬──────────────┘
       │      │      │      │
       ▼      ▼      ▼      ▼
   Researcher  Builder  Reviewer  Scheduler
```

### Delegation criteria

| Signal | Action |
|--------|--------|
| Task requires web research | Spawn **Researcher** with query + context |
| Task requires coding/multiple files | Spawn **Builder** with spec + files |
| Output needs adversarial review | Spawn **Reviewer** with output + criteria |
| Recurring or fire-and-forget | Register with **Scheduler** |
| Task has 3+ independent workstreams | Fan out to parallel sub-agents |
| Unknown codebase area | Spawn **Explorer** (read-only) first |

## 2. Sub-Agent Roles

### [A] Researcher
- **Function:** Information gathering, web research, content extraction.
- **Tools:** ``web_search``, ``web_scrape``, ``read`` (URLs).
- **When to use:** Investigate a claim, compare products, find docs.
- **Output:** Structured findings with citations.

### [B] Builder
- **Function:** Code generation, modification, and testing.
- **Tools:** ``read``, ``edit``, ``write``, ``bash``.
- **When to use:** Implement a feature, fix a bug, refactor code.
- **Output:** Working code changes + verification evidence.

### [C] Reviewer
- **Function:** Quality assurance, security review, edge case analysis.
- **Tools:** ``read``, ``lsp``, ``search``.
- **When to use:** After Builder finishes, before merging.
- **Output:** Categorized findings (blocker / warning / info).

### [D] Explorer (read-only)
- **Function:** Codebase mapping and discovery.
- **Tools:** ``read``, ``find``, ``search``, ``ast_grep``.
- **When to use:** Navigate unfamiliar code, find patterns.
- **Output:** Compressed context summary, relevant file paths.

## 3. Standard Operating Procedure

1. **INGEST:** Parse the request. Identify the deliverable and success criteria.
2. **PLAN:** Decompose into phases. Decide single-agent vs. delegation.
3. **EXECUTE:** Run the plan. Delegate sub-tasks where warranted.
4. **VERIFY:** Check output against criteria. Run tests. Fix failures.
5. **DELIVER:** Present results. Log new knowledge to memory.

## 4. Error Handling

- Unknown task type → Ask for clarification. Do not hallucinate a plan.
- Sub-agent timeout → Retry once with narrower scope, then escalate.
- Test failure → Treat as verification finding, not final state.
- API failure → Log error, retry with backoff, fall back to cache if available.

## 5. Memory Integration

Cogent persists knowledge across sessions in two stores:

| Store | File | Purpose |
|-------|------|---------|
| Agent Memory | ``memory/memories/MEMORY.md`` | Facts, learnings, resolved issues |
| User Memory | ``memory/memories/USER.md`` | Preferences, context, goals |

Sub-agents may read memory but should write it only through the
orchestrator to avoid conflicts.

## 6. Infrastructure Subsystems

Cogent's infrastructure layer mirrors Hermes' architecture, adapted for
a FastAPI + MongoDB + React stack:

| Subsystem | Module | Purpose |
|-----------|--------|---------|
| Config | ``backend/cogent_config.py`` + ``config.yaml`` | 3-layer config (defaults → YAML → env) |
| Logging | ``backend/cogent_logging.py`` | Rotating file handlers, session context tags |
| Constants | ``backend/cogent_constants.py`` | Well-known paths, env-var names, platform helpers |
| Providers | ``backend/cogent_providers.py`` | LLM provider abstraction + KiloCode provider |
| Session State | ``backend/cogent_state.py`` | JSON-file-backed session index + lifecycle |
| Memory | ``backend/cogent_memory.py`` | ``§``-delimited markdown KV store (MEMORY.md, USER.md) |
| Budget | ``backend/cogent_budget.py`` | Iteration + token budget tracker |
| Services | ``backend/cogent_services.py`` | Auxiliary service router (vision, compression) |
| Hooks | ``backend/cogent_hooks.py`` | 9 lifecycle hook points, auto-discovery |
| Kanban | ``backend/cogent_kanban.py`` | Task board with columns, priorities, comments |
| Auth | ``backend/cogent_auth.py`` | Credential token store (memory/auth.json) |
| Cache | ``backend/cogent_cache.py`` | TTL-based file cache (memory/cache/) |
| Processes | ``backend/cogent_processes.py`` | Background process registry (memory/processes.json) |
| Checkpoints | ``backend/cogent_checkpoints.py`` | State snapshots (memory/snapshots/) |
| Cron | ``backend/cogent_cron.py`` | Cron job storage + output history (memory/cron/) |
| Blueprints | ``backend/blueprint_catalog.py`` | Task blueprint templates for the scheduler |
| CLI | ``backend/cli/`` | Management CLI (server, auth, cron, kanban, cache, config, logs, memory, checkpoints, blueprints, skills) |
| Gateway | ``backend/cogent_gateway.py`` | SSE delivery router for the React UI |
| ACP | ``backend/cogent_acp.py`` | Minimal Agent Communication Protocol adapter |
| Tools Registry | ``backend/tools_registry.py`` | Hermes-style tool registry with availability checks |
| Skills Catalog | ``backend/skills_catalog.py`` | Skill discovery from .cogent/skills/ and optional-skills/ |
| Agent Core | ``backend/agent/`` | Turn context, context compression, agent bootstrap |
| UI Gateway | ``frontend/src/lib/gateway.ts`` | SSE gateway client (TypeScript) |

## 7. Data Flow

```
User → React UI → FastAPI (server.py)
                  ├── llm_service.py (Plan→Execute→Verify loop)
                  │   ├── Provider (cogent_providers.py → KiloCode API)
                  │   ├── Memory (cogent_memory.py + MongoDB)
                  │   ├── Budget (cogent_budget.py → iteration limits)
                  │   ├── Agent Core (backend/agent/ → turn context, compression)
                  │   └── Tools (tools.py + tools_registry.py)
                  ├── Session State (cogent_state.py → memory/sessions/)
                  ├── Gateway (cogent_gateway.py → SSE → frontend/src/lib/gateway.ts)
                  ├── ACP (cogent_acp.py → agent-to-agent protocol)
                  ├── Hooks (cogent_hooks.py → backend/hooks/)
                  └── Scheduler (scheduler.py + cogent_cron.py)
                       └── Blueprints (blueprint_catalog.py → memory/cron/)
```

## 8. Persistence Layout

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
├── cogent.json       # General state
└── observability/    # Tool activity logs

optional-skills/      # Curated skill catalog (not auto-installed)
optional-mcps/        # MCP server catalog entries
datagen/              # Batch data generation configs
scripts/              # Install, setup, test, and utility scripts
```
## 7. Data Flow

```
User → React UI → FastAPI (server.py)
                  ├── llm_service.py (Plan→Execute→Verify loop)
                  │   ├── Provider (cogent_providers.py → KiloCode API)
                  │   ├── Memory (cogent_memory.py + MongoDB)
                  │   ├── Budget (cogent_budget.py → iteration limits)
                  │   └── Tools (tools.py + agent_reach_tools.py)
                  ├── Session State (cogent_state.py → memory/sessions/)
                  ├── Hooks (cogent_hooks.py → backend/hooks/)
                  └── Scheduler (scheduler.py + cogent_cron.py)
                       └── Blueprints (blueprint_catalog.py → memory/cron/)
```

## 8. Persistence Layout

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
├── cogent.json       # General state
└── observability/    # Tool activity logs
```
