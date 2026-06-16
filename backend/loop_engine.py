"""Loop Engineering — iterative refinement engine for Cogent.

Bakes loop-engineering primitives into every task Cogent handles:
  Plan → Execute → Verify → (refine or done)

Inspired by cobusgreyling/loop-engineering:
  - Explicit STATE tracking per session (phase, attempts, decisions)
  - Maker/checker split via self-verification
  - Budget awareness (token estimates, max iterations)
  - Durable state outside any single conversation turn
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.loop_engine")

# ── Constants ────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
LOOP_STATE_DIR = PROJECT_ROOT / "memory" / "loops"

MAX_ITERATIONS = 50         # max Plan→Execute→Verify cycles per task
MAX_TOKENS_PER_TASK = 200_000  # rough budget ceiling
WARN_TOKEN_PCT = 0.75       # warn at 75% of budget
CONTINUE_MAX = 50          # max auto-continuation re-prompts per session

# ── Phase enum ───────────────────────────────────────────────────────────
PHASE_IDLE = "idle"
PHASE_PLAN = "plan"
PHASE_EXECUTE = "execute"
PHASE_VERIFY = "verify"
PHASE_DONE = "done"
PHASE_ESCALATE = "escalate"
PHASE_ERROR = "error"

VALID_PHASES = {
    PHASE_IDLE, PHASE_PLAN, PHASE_EXECUTE,
    PHASE_VERIFY, PHASE_DONE, PHASE_ESCALATE, PHASE_ERROR,
}

# ── State ────────────────────────────────────────────────────────────────

@dataclass
class LoopState:
    """Persistent loop state for one session."""
    session_id: str
    phase: str = PHASE_IDLE
    iteration: int = 0
    task_description: str = ""
    verification_criteria: List[str] = field(default_factory=list)
    continue_count: int = 0  # times auto-continue was triggered
    last_plan_text: str = ""  # last detected plan-like text

    # Tracking
    attempts: List[Dict[str, Any]] = field(default_factory=list)  # {phase, summary, timestamp}
    tokens_estimated: int = 0
    errors: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)  # key choices made

    # Results
    last_output_summary: str = ""
    verification_result: Optional[str] = None  # pass / fail / partial
    verification_notes: str = ""

    # Budget
    budget_max: int = MAX_TOKENS_PER_TASK
    budget_warn_pct: float = WARN_TOKEN_PCT

    # Timestamps
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.phase in (PHASE_PLAN, PHASE_EXECUTE, PHASE_VERIFY)

    @property
    def budget_exhausted(self) -> bool:
        return self.tokens_estimated >= self.budget_max

    @property
    def budget_warning(self) -> bool:
        return self.tokens_estimated >= int(self.budget_max * self.budget_warn_pct)

    @property
    def max_iterations_reached(self) -> bool:
        return self.iteration >= MAX_ITERATIONS


def _state_path(session_id: str) -> Path:
    LOOP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return LOOP_STATE_DIR / f"{session_id}.json"


def load_state(session_id: str) -> LoopState:
    """Load loop state from disk. Returns default state if no file exists."""
    path = _state_path(session_id)
    if not path.is_file():
        return LoopState(session_id=session_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return LoopState(**data)
    except Exception as exc:
        logger.warning("Failed to load loop state for %s: %s", session_id, exc)
        return LoopState(session_id=session_id)


def save_state(state: LoopState) -> None:
    """Persist loop state to disk."""
    state.updated_at = datetime.utcnow().isoformat() + "Z"
    path = _state_path(state.session_id)
    path.write_text(json.dumps(asdict(state), indent=2, default=str), encoding="utf-8")


def delete_state(session_id: str) -> None:
    path = _state_path(session_id)
    if path.is_file():
        path.unlink()


# ── State transitions ────────────────────────────────────────────────────

def transition(state: LoopState, new_phase: str, note: str = "") -> None:
    """Transition the loop to a new phase and log the decision."""
    assert new_phase in VALID_PHASES, f"Invalid phase: {new_phase}"
    old = state.phase
    state.phase = new_phase
    if note:
        state.decisions.append(f"[{old}→{new_phase}] {note}")
    logger.debug("Loop %s: %s → %s — %s", state.session_id, old, new_phase, note)


def begin_task(state: LoopState, task: str, criteria: Optional[List[str]] = None) -> None:
    """Initialize loop state for a new task."""
    state.phase = PHASE_PLAN
    state.iteration = 0
    state.task_description = task
    state.verification_criteria = criteria or []
    state.continue_count = 0
    state.last_plan_text = ""
    state.attempts = []
    state.errors = []
    state.decisions = []
    state.last_output_summary = ""
    state.verification_result = None
    state.verification_notes = ""
    state.tokens_estimated = 0
    state.started_at = datetime.utcnow().isoformat() + "Z"
    state.completed_at = None
    state.decisions.append(f"Task started: {task[:80]}")
    save_state(state)


def record_attempt(state: LoopState, phase: str, summary: str) -> None:
    state.iteration += 1
    state.attempts.append({
        "iteration": state.iteration,
        "phase": phase,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    save_state(state)

def complete_task(state: LoopState, summary: str = "") -> None:
    state.phase = PHASE_DONE
    state.completed_at = datetime.utcnow().isoformat() + "Z"
    state.last_output_summary = summary
    save_state(state)


def fail_task(state: LoopState, error: str) -> None:
    state.phase = PHASE_ERROR
    state.errors.append(error)
    state.completed_at = datetime.utcnow().isoformat() + "Z"
    save_state(state)


def escalate_task(state: LoopState, reason: str) -> None:
    state.phase = PHASE_ESCALATE
    state.decisions.append(f"Escalated: {reason}")
    state.completed_at = datetime.utcnow().isoformat() + "Z"
    save_state(state)


# ── System prompt augmentation ───────────────────────────────────────────

LOOP_SYSTEM_PROMPT = """
## Loop Engineering Protocol

Every task follows Plan → Execute → Verify → Iterate until Goal Success(You do not stop untilthe user task is complete). You manage this cycle yourself by being proactive.

### Protocol

1. **PLAN** — Before doing anything, state your plan:
   - What is the goal? What does "done" look like?
   - What tools will you need?
   - What could go wrong?

2. **EXECUTE** — Do the work. Use tools as needed. One tool call per turn.

3. **VERIFY** — After executing, check your work:
   - Does the output meet the goal?
   - Are there errors, edge cases, or missing pieces?
   - Rate your confidence: HIGH / MEDIUM / LOW

4. **Iterate until Goal Success**:
   - If verification passes → signal completion.
   - If verification fails or is LOW confidence → refine and loop back to EXECUTE.
   - If stuck after multiple attempts → escalate by iterating again until the task is complete and GOAL SUCCESS.

### Budget awareness

- Be concise. Don't generate verbose output when a sentence suffices.
- If the task is large, Iterate small tasks and chunks until GOAL SUCCESS.
- Watch for expensive tools — use them only when needed.

### State tracking

You have access to the current loop state via `get_loop_state` tool.
The state remembers your phase, iteration count, and past attempts.
Use it to avoid repeating failed approaches.
"""


def build_loop_system_block(state: Optional[LoopState] = None) -> str:
    """Build the loop engineering system prompt block with current state context."""
    if state is None or state.phase == PHASE_IDLE:
        # First use — inject the full protocol
        return LOOP_SYSTEM_PROMPT

    # Inject current state for follow-up turns
    budget_pct = int((state.tokens_estimated / state.budget_max) * 100) if state.budget_max else 0
    return f"""
## Loop Engineering — Current State

| Field | Value |
|-------|-------|
| Phase | {state.phase} |
| Iteration | {state.iteration}/{MAX_ITERATIONS} |
| Task | {state.task_description[:120]} |
| Budget used | ~{budget_pct}% ({state.tokens_estimated} tokens) |
| Last verification | {state.verification_result or 'not yet run'} |
| Past attempts | {len(state.attempts)} |

Continue the protocol:
- **EXECUTE** — do the work using tools.
- **VERIFY** — check your output against the goal.
- If LOW confidence or errors remain → refine and iterate.
- If HIGH confidence → signal done.
"""


# ── Verification helper ──────────────────────────────────────────────────

def build_verification_prompt(task: str, output: str, criteria: List[str]) -> str:
    """Build a prompt for the verification pass.

    The verifier is run as a separate completion call to implement the
    maker/checker split — the agent that produced output does not grade
    its own homework.
    """
    criteria_block = "\n".join(f"- {c}" for c in criteria) if criteria else "- Meets the stated goal"
    return f"""You are a quality verifier. Your job is to check whether the output below
satisfies the task requirements. Be strict but fair.

## Task
{task}

## Verification criteria
{criteria_block}

## Output to verify
{output}

## Response format
First line: PASS / FAIL / PARTIAL
Remaining lines: Brief explanation. If FAIL or PARTIAL, state what's missing.
"""


async def run_verification(task: str, output: str, criteria: List[str],
                           llm_complete_fn) -> tuple[str, str]:
    """Run the maker/checker verification pass.

    Returns (verdict, notes) where verdict is one of PASS/FAIL/PARTIAL.
    """
    prompt = build_verification_prompt(task, output, criteria)
    try:
        result = await llm_complete_fn(prompt)
        result = result.strip()
        verdict = "FAIL"
        for v in ("PASS", "FAIL", "PARTIAL"):
            if result.startswith(v):
                verdict = v
                break
        notes = result[len(verdict):].strip().lstrip(":").strip()
        return verdict, notes
    except Exception as exc:
        logger.warning("Verification call failed: %s", exc)
        return "PARTIAL", f"Verifier error: {exc}"


# ── Metrics ──────────────────────────────────────────────────────────────

def get_all_loop_states() -> List[Dict[str, Any]]:
    """List all active loop states for the dashboard."""
    LOOP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for path in sorted(LOOP_STATE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Trim to lightweight summary
            results.append({
                "session_id": data.get("session_id"),
                "phase": data.get("phase"),
                "iteration": data.get("iteration"),
                "task_description": (data.get("task_description") or "")[:100],
                "updated_at": data.get("updated_at"),
            })
        except Exception:
            pass
    return results
