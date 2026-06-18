"""Loop Engineering — iterative refinement engine for Cogent.

Bakes loop-engineering primitives into every task Cogent handles:
  Plan -> Execute -> Verify -> (refine or done)

Inspired by cobusgreyling/loop-engineering and frankbria/ralph-claude-code:
  - Dual-condition exit gate: requires BOTH completion indicators AND explicit EXIT_SIGNAL
  - Circuit breaker: 3-state (CLOSED/HALF_OPEN/OPEN) stagnation detection
  - Response analysis: RALPH_STATUS block parsing, question detection, progress tracking
  - Maker/checker split via self-verification
  - Budget awareness (token estimates, max iterations)
  - Durable state outside any single conversation turn
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.loop_engine")

# ── Debounce constants ────────────────────────────────────────────────────
# save_state writes to disk at most once per N non-critical transitions,
# reducing synchronous disk-write churn on the event-loop thread.
SAVE_DEBOUNCE_LIMIT = 5
_pending_save_count: Dict[str, int] = {}

# ── Constants ────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
LOOP_STATE_DIR = PROJECT_ROOT / "memory" / "loops"

MAX_ITERATIONS = 90         # max Plan->Execute->Verify cycles per task
MAX_TOKENS_PER_TASK = 200_000  # rough budget ceiling
WARN_TOKEN_PCT = 0.75       # warn at 75% of budget
CONTINUE_MAX = 90           # max auto-continuation re-prompts per session

# ── Phase enum ───────────────────────────────────────────────────────────
PHASE_IDLE = "idle"
PHASE_PLAN = "plan"
PHASE_EXECUTE = "execute"
PHASE_VERIFY = "verify"
PHASE_DONE = "done"
PHASE_ESCALATE = "escalate"
PHASE_ERROR = "error"

VALID_PHASES = {PHASE_IDLE, PHASE_PLAN, PHASE_EXECUTE, PHASE_VERIFY,
                PHASE_DONE, PHASE_ESCALATE, PHASE_ERROR}

# ── Circuit Breaker constants (Ralph-style) ──────────────────────────────
CB_CLOSED = "CLOSED"        # Normal operation, progress detected
CB_HALF_OPEN = "HALF_OPEN"  # Monitoring mode, checking for recovery
CB_OPEN = "OPEN"            # Failure detected, execution halted

# Circuit breaker thresholds
CB_NO_PROGRESS_THRESHOLD = 3     # Open circuit after N loops with no progress
CB_SAME_ERROR_THRESHOLD = 5      # Open circuit after N loops with same error
CB_NO_PROGRESS_WARN = 2          # Transition to HALF_OPEN after N no-progress loops
CB_COOLDOWN_SECONDS = 1800       # 30 minutes before OPEN -> HALF_OPEN auto-recovery

# ── Exit detection constants (Ralph-style) ───────────────────────────────
MAX_CONSECUTIVE_TEST_LOOPS = 3
MAX_CONSECUTIVE_DONE_SIGNALS = 2
SAFETY_CIRCUIT_BREAKER_LIMIT = 5  # force exit after 5 consecutive EXIT_SIGNAL=true

# ── Tool-loop guardrails (CowAgent-style) ───────────────────────
MAX_SAME_ARGS_CALLS = 5      # Same tool + args called N times → stop
MAX_CONSECUTIVE_FAILURES = 3  # Same tool + args failed N times → soft stop
MAX_CRITICAL_FAILURES = 8     # Same tool failed N times → hard abort
TOOL_FAILURE_HISTORY_MAX = 50  # max entries kept per session

COMPLETION_KEYWORDS = ["done", "complete", "finished",
                       "all tasks complete", "project complete", "ready for review"]
TEST_ONLY_PATTERNS = ["npm test", "bats", "pytest", "jest",
                      "cargo test", "go test", "running tests"]
NO_WORK_PATTERNS = ["nothing to do", "no changes", "already implemented", "up to date"]
QUESTION_PATTERNS = [
    "should I", "would you", "do you want", "which approach",
    "which option", "how should", "what should", "shall I",
    "do you prefer", "can you clarify", "could you",
    "what do you think", "please confirm", "need clarification",
    "awaiting.*input", "waiting.*response", "your preference",
]

# ── RALPH_STATUS block regex ─────────────────────────────────────────────
RALPH_STATUS_RE = re.compile(
    r"^[ \t]*(?:---RALPH_STATUS---|---END_RALPH_STATUS---|RALPH_STATUS:)", re.MULTILINE
)
EXIT_SIGNAL_RE = re.compile(r"^[ \t]*EXIT_SIGNAL:\s*(true|false)", re.MULTILINE)
STATUS_RE = re.compile(r"^[ \t]*STATUS:\s*(\w+)", re.MULTILINE)


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

    # ── Ralph-style fields ──────────────────────────────────────────────
    # Circuit breaker
    cb_state: str = CB_CLOSED
    cb_consecutive_no_progress: int = 0
    cb_consecutive_same_error: int = 0
    cb_last_progress_loop: int = 0
    cb_total_opens: int = 0
    cb_opened_at: Optional[str] = None

    # Exit signal tracking
    exit_signals: List[int] = field(default_factory=list)  # loop numbers where EXIT_SIGNAL=true
    completion_indicators: List[int] = field(default_factory=list)  # loop numbers with strong completion
    done_signals: List[int] = field(default_factory=list)  # loop numbers with completion signals
    test_only_loops: List[int] = field(default_factory=list)  # loop numbers that were test-only

    # ── Tool-loop guardrails (CowAgent-style) ─────────────────────
    tool_failure_history: List[tuple] = field(default_factory=list)  # (tool_name, args_hash, success)
    tool_loop_detected_stop: bool = False  # set when guardrail breaks the loop

    # Progress tracking (per-loop)
    last_files_changed: int = 0
    last_errors_detected: bool = False
    last_output_length: int = 0
    last_asking_questions: bool = False

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
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LoopState(**data)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Corrupt loop state for %s: %s; starting fresh", session_id, exc)
    return LoopState(session_id=session_id)


def save_state(state: LoopState, force: bool = False) -> None:
    """Persist loop state to disk (debounced when *force* is False).

    Non-critical writes (attempt records, tool results, exit-signal updates)
    are batched so only every N-th call actually flushes to disk.  Critical
    transitions (phase change, task complete/fail/escalate, circuit-breaker
    state change) MUST pass *force* = ``True``.
    """
    sid = state.session_id
    count = _pending_save_count.get(sid, 0) + 1
    _pending_save_count[sid] = count

    if not force and count < SAVE_DEBOUNCE_LIMIT:
        return  # skip write; accumulate more changes

    # Flush to disk
    _pending_save_count[sid] = 0
    state.updated_at = datetime.utcnow().isoformat() + "Z"
    path = _state_path(state.session_id)
    path.write_text(json.dumps(asdict(state), indent=2, default=str), encoding="utf-8")


# ── State transitions ────────────────────────────────────────────────────

def transition(state: LoopState, new_phase: str, note: str = "") -> None:
    """Transition the loop to a new phase and log the decision."""
    if new_phase not in VALID_PHASES:
        logger.warning("Invalid phase %s; ignoring", new_phase)
        return
    old = state.phase
    state.phase = new_phase
    if note:
        state.decisions.append(f"[{old}->{new_phase}] {note}")
    logger.debug("Loop %s: %s -> %s -- %s", state.session_id, old, new_phase, note)


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
    # Reset Ralph-style tracking
    state.cb_state = CB_CLOSED
    state.cb_consecutive_no_progress = 0
    state.cb_consecutive_same_error = 0
    state.cb_last_progress_loop = 0
    state.exit_signals = []
    state.completion_indicators = []
    state.done_signals = []
    state.test_only_loops = []
    # Reset CowAgent-style tool guardrails
    state.tool_failure_history = []
    state.tool_loop_detected_stop = False
    state.last_files_changed = 0
    state.last_errors_detected = False
    state.last_output_length = 0
    state.last_asking_questions = False
    state.decisions.append(f"Task started: {task[:80]}")
    save_state(state, force=True)


def record_attempt(state: LoopState, phase: str, summary: str) -> None:
    state.iteration += 1
    state.attempts.append({
        "phase": phase,
        "summary": summary[:200],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    save_state(state)  # debounced


def complete_task(state: LoopState, summary: str = "") -> None:
    state.phase = PHASE_DONE
    state.completed_at = datetime.utcnow().isoformat() + "Z"
    if summary:
        state.last_output_summary = summary[:200]
    save_state(state, force=True)


def fail_task(state: LoopState, error: str) -> None:
    state.phase = PHASE_ERROR
    state.errors.append(error[:200])
    save_state(state, force=True)


def escalate_task(state: LoopState, reason: str) -> None:
    state.phase = PHASE_ESCALATE
    state.decisions.append(f"Escalated: {reason[:200]}")
    save_state(state, force=True)


# ── Circuit Breaker (Ralph-style) ────────────────────────────────────────

def init_circuit_breaker(state: LoopState) -> None:
    """Initialize or auto-recover circuit breaker on startup."""
    if state.cb_state == CB_OPEN and state.cb_opened_at:
        try:
            opened_epoch = datetime.fromisoformat(state.cb_opened_at.replace("Z", "+00:00")).timestamp()
            now = time.time()
            elapsed = now - opened_epoch
            if elapsed >= CB_COOLDOWN_SECONDS:
                old_state = state.cb_state
                state.cb_state = CB_HALF_OPEN
                state.decisions.append(
                    f"CB {old_state} -> {CB_HALF_OPEN}: cooldown elapsed ({int(elapsed)}s >= {CB_COOLDOWN_SECONDS}s)"
                )
                save_state(state, force=True)
        except (ValueError, TypeError):
            pass


def record_loop_result(
    state: LoopState,
    loop_number: int,
    files_changed: int,
    has_errors: bool,
    has_progress: bool,
    exit_signal: bool,
) -> str:
    """Record loop result and update circuit breaker state.

    Returns the new CB state.
    """
    init_circuit_breaker(state)

    # Progress detection
    if has_progress or files_changed > 0:
        state.cb_consecutive_no_progress = 0
        state.cb_last_progress_loop = loop_number
    elif exit_signal:
        # EXIT_SIGNAL=true is always progress
        state.cb_consecutive_no_progress = 0
        state.cb_last_progress_loop = loop_number
    else:
        state.cb_consecutive_no_progress += 1

    # Error tracking
    if has_errors:
        state.cb_consecutive_same_error += 1
    else:
        state.cb_consecutive_same_error = 0

    # Update persistent state
    state.last_files_changed = files_changed
    state.last_errors_detected = has_errors

    # State transitions
    old_state = state.cb_state
    reason = ""

    if state.cb_state == CB_CLOSED:
        if state.cb_consecutive_no_progress >= CB_NO_PROGRESS_THRESHOLD:
            state.cb_state = CB_OPEN
            state.cb_total_opens += 1
            state.cb_opened_at = datetime.utcnow().isoformat() + "Z"
            reason = f"No progress in {state.cb_consecutive_no_progress} consecutive loops"
        elif state.cb_consecutive_same_error >= CB_SAME_ERROR_THRESHOLD:
            state.cb_state = CB_OPEN
            state.cb_total_opens += 1
            state.cb_opened_at = datetime.utcnow().isoformat() + "Z"
            reason = f"Same error repeated {state.cb_consecutive_same_error} consecutive loops"
        elif state.cb_consecutive_no_progress >= CB_NO_PROGRESS_WARN:
            state.cb_state = CB_HALF_OPEN
            reason = f"Monitoring: {state.cb_consecutive_no_progress} loops without progress"

    elif state.cb_state == CB_HALF_OPEN:
        if has_progress or files_changed > 0:
            state.cb_state = CB_CLOSED
            reason = "Progress detected, circuit recovered"
            state.cb_consecutive_no_progress = 0
        elif state.cb_consecutive_no_progress >= CB_NO_PROGRESS_THRESHOLD:
            state.cb_state = CB_OPEN
            state.cb_total_opens += 1
            state.cb_opened_at = datetime.utcnow().isoformat() + "Z"
            reason = f"No recovery after {state.cb_consecutive_no_progress} loops"

    if state.cb_state != old_state:
        state.decisions.append(f"CB {old_state} -> {state.cb_state}: {reason}")
        logger.info("Circuit breaker %s -> %s: %s", old_state, state.cb_state, reason)

    save_state(state, force=True)
    return state.cb_state


def should_halt_execution(state: LoopState) -> bool:
    """Check if circuit breaker says halt."""
    init_circuit_breaker(state)

    if state.cb_state == CB_OPEN:
        return True

    # Safety: if we've seen too many EXIT_SIGNAL=true without resolving
    if len(state.exit_signals) >= SAFETY_CIRCUIT_BREAKER_LIMIT:
        logger.warning("Safety circuit breaker: %d consecutive EXIT_SIGNAL=true responses",
                       len(state.exit_signals))
        return True

    return False


# ── Tool-loop guardrail functions (CowAgent-style) ───────────────────────

import hashlib


def _hash_args(args: dict) -> str:
    """Deterministic hash of tool arguments for loop detection."""
    args_str = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(args_str.encode()).hexdigest()[:8]


def record_tool_result(state: LoopState, tool_name: str, args: dict, success: bool) -> None:
    """Record a tool execution outcome for loop/failure detection.

    Keeps a rolling window of the last TOOL_FAILURE_HISTORY_MAX entries.
    """
    args_hash = _hash_args(args)
    state.tool_failure_history.append((tool_name, args_hash, success))
    if len(state.tool_failure_history) > TOOL_FAILURE_HISTORY_MAX:
        state.tool_failure_history = state.tool_failure_history[-TOOL_FAILURE_HISTORY_MAX:]
    save_state(state)  # debounced


def check_tool_loop(state: LoopState, tool_name: str, args: dict) -> tuple[bool, str, bool]:
    """Check if the tool call is in a loop and should be stopped.

    Returns (should_stop, reason, is_critical).
    - should_stop: True when repeated calls or failures detected
    - reason: explanation for stopping
    - is_critical: True means abort the entire conversation
    """
    args_hash = _hash_args(args)

    # Count consecutive calls with same tool + args (success or failure)
    same_args_calls = 0
    for name, ahash, _success in reversed(state.tool_failure_history):
        if name == tool_name and ahash == args_hash:
            same_args_calls += 1
        else:
            break
    if same_args_calls >= MAX_SAME_ARGS_CALLS:
        return True, (
            f"Tool '{tool_name}' called with same args {same_args_calls} times — "
            f"stopping to prevent infinite loop"
        ), False

    # Count consecutive failures for same tool + args
    same_args_failures = 0
    for name, ahash, success in reversed(state.tool_failure_history):
        if name == tool_name and ahash == args_hash:
            if not success:
                same_args_failures += 1
            else:
                break
        else:
            break
    if same_args_failures >= MAX_CONSECUTIVE_FAILURES:
        return True, (
            f"Tool '{tool_name}' failed {same_args_failures} times with same args — "
            f"stopping to prevent retry loop"
        ), False

    # Count consecutive failures for same tool (any args)
    same_tool_failures = 0
    for name, _ahash, success in reversed(state.tool_failure_history):
        if name == tool_name:
            if not success:
                same_tool_failures += 1
            else:
                break
        else:
            break
    if same_tool_failures >= MAX_CRITICAL_FAILURES:
        return True, (
            f"Tool '{tool_name}' failed {same_tool_failures} consecutive times — "
            f"aborting this task"
        ), True

    return False, "", False


# ── Response Analysis (Ralph-style) ──────────────────────────────────────

def parse_ralph_status_block(text: str) -> dict:
    """Parse a RALPH_STATUS block from LLM output.

    Supports two formats:
      1) ---RALPH_STATUS---
         EXIT_SIGNAL: true
         ---END_RALPH_STATUS---
      2) RALPH_STATUS:
           EXIT_SIGNAL: true

    Returns dict with exit_signal (bool or None), explicit (bool).
    """
    result = {"exit_signal": None, "explicit": False}

    if not RALPH_STATUS_RE.search(text):
        return result

    # Try to extract EXIT_SIGNAL
    m = EXIT_SIGNAL_RE.search(text)
    if m:
        result["exit_signal"] = m.group(1) == "true"
        result["explicit"] = True
        return result

    # Fall back to STATUS: COMPLETE
    m = STATUS_RE.search(text)
    if m and m.group(1).upper() == "COMPLETE":
        result["exit_signal"] = True

    return result


def count_questions(text: str) -> int:
    """Count question-like patterns in text."""
    count = 0
    for pattern in QUESTION_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        except re.error:
            pass
    return count


def analyze_response_text(text: str) -> dict:
    """Analyze LLM response text for completion signals, test-only patterns, etc.

    Returns dict with:
      - has_completion_signal: bool
      - is_test_only: bool
      - is_stuck: bool
      - exit_signal: bool (from RALPH_STATUS block)
      - explicit_exit_signal: bool (was EXIT_SIGNAL explicitly provided?)
      - asking_questions: bool
      - question_count: int
      - confidence_score: int (0-100 heuristic)
      - work_summary: str
    """
    result = {
        "has_completion_signal": False,
        "is_test_only": False,
        "is_stuck": False,
        "exit_signal": False,
        "explicit_exit_signal": False,
        "asking_questions": False,
        "question_count": 0,
        "confidence_score": 0,
        "work_summary": "",
    }

    if not text:
        return result

    # 1. Parse RALPH_STATUS block
    status = parse_ralph_status_block(text)
    if status["explicit"]:
        result["exit_signal"] = status["exit_signal"]
        result["explicit_exit_signal"] = True
        if status["exit_signal"]:
            result["has_completion_signal"] = True
            result["confidence_score"] = 100

    # 2. Detect completion keywords
    for keyword in COMPLETION_KEYWORDS:
        if keyword.lower() in text.lower():
            result["has_completion_signal"] = True
            result["confidence_score"] += 10

    # 3. Detect test-only patterns
    test_count = 0
    impl_count = 0
    for pat in TEST_ONLY_PATTERNS:
        if pat.lower() in text.lower():
            test_count += 1
    for pat in ["implementing", "creating", "writing", "adding", "function", "class"]:
        if pat.lower() in text.lower():
            impl_count += 1

    if test_count > 0 and impl_count == 0:
        result["is_test_only"] = True
        result["work_summary"] = "Test execution only, no implementation"

    # 4. Detect stuck/error loops
    error_count = len(re.findall(
        r"(^Error:|^ERROR:|^error:|\]: error|Link: error|"
        r"Error occurred|failed with error|[Ee]xception|Fatal|FATAL)",
        text, re.MULTILINE
    ))
    if error_count > 5:
        result["is_stuck"] = True

    # 5. Detect "nothing to do" patterns
    for pattern in NO_WORK_PATTERNS:
        if pattern.lower() in text.lower():
            result["has_completion_signal"] = True
            result["confidence_score"] += 15
            result["work_summary"] = "No work remaining"

    # 6. Detect questions
    q_count = count_questions(text)
    result["question_count"] = q_count
    if q_count > 0:
        result["asking_questions"] = True

    # 7. Heuristic exit signal (only if no explicit EXIT_SIGNAL)
    if not result["explicit_exit_signal"]:
        if result["confidence_score"] >= 70 and result["has_completion_signal"]:
            result["exit_signal"] = True

    # 8. Extract work summary
    if not result["work_summary"]:
        summary_match = re.search(
            r"(?i)(summary|completed|implemented)[:\s]+(.+?)(?:\n|$)", text
        )
        if summary_match:
            result["work_summary"] = summary_match.group(2).strip()[:100]
        else:
            # Grab first meaningful line
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 30]
            result["work_summary"] = lines[0][:100] if lines else "Output analyzed"

    return result


def update_exit_signals(state: LoopState, analysis: dict) -> None:
    """Update exit signal tracking from response analysis."""
    loop_num = state.iteration

    if analysis.get("is_test_only"):
        state.test_only_loops.append(loop_num)
    elif analysis.get("has_completion_signal", False) or analysis.get("has_progress", False):
        # Clear test-only if we had progress
        state.test_only_loops = []

    if analysis.get("has_completion_signal"):
        state.done_signals.append(loop_num)

    if analysis.get("exit_signal"):
        state.completion_indicators.append(loop_num)
        state.exit_signals.append(loop_num)

    # Rolling window: keep only last 5
    state.test_only_loops = state.test_only_loops[-5:]
    state.done_signals = state.done_signals[-5:]
    state.completion_indicators = state.completion_indicators[-5:]
    state.exit_signals = state.exit_signals[-5:]

    save_state(state)  # debounced

def should_exit_gracefully(state: LoopState) -> Optional[str]:
    """Check exit conditions — Ralph-style + CowAgent-style guardrails.

    Returns exit reason string or None if should continue.
    Ordered by severity: safety circuit breaker first, then normal conditions.
    """
    # 0. Tool-loop guardrail triggered (CowAgent-style)
    if state.tool_loop_detected_stop:
        return "tool_loop_guardrail"

    # 1. Safety circuit breaker - 5+ consecutive EXIT_SIGNAL=true
    if len(state.completion_indicators) >= SAFETY_CIRCUIT_BREAKER_LIMIT:
        return "safety_circuit_breaker"

    # 2. Too many consecutive test-only loops
    if len(state.test_only_loops) >= MAX_CONSECUTIVE_TEST_LOOPS:
        return "test_saturation"

    # 3. Multiple done signals
    if len(state.done_signals) >= MAX_CONSECUTIVE_DONE_SIGNALS:
        return "completion_signals"

    # 4. Dual-condition exit: completion_indicators >= 2 AND explicit EXIT_SIGNAL in latest
    if len(state.completion_indicators) >= 2:
        if state.exit_signals and state.iteration in state.exit_signals:
            return "project_complete"

    return None


# ── System prompt augmentation (Ralph-style) ────────────────────────────

RALPH_EXIT_SIGNAL_PROMPT = """
### Exit Signal Protocol

When you have completed all work for the current task, you MUST signal
completion explicitly by including a RALPH_STATUS block at the end of your response:

---RALPH_STATUS---
STATUS: COMPLETE
EXIT_SIGNAL: true
---END_RALPH_STATUS---

If the task is NOT complete and you need to continue working, include:

---RALPH_STATUS---
STATUS: IN_PROGRESS
EXIT_SIGNAL: false
---END_RALPH_STATUS---

RULES:
- Only set EXIT_SIGNAL: true when ALL work is genuinely done.
- If there is still work remaining, set EXIT_SIGNAL: false to continue looping.
- The loop will keep running as long as EXIT_SIGNAL is false.
- Do NOT signal completion early just because a subtask finished.
- Be honest: if you're unsure or need clarification, set EXIT_SIGNAL: false.
"""

LOOP_SYSTEM_PROMPT = """
## Loop Engineering Protocol

Every task follows Plan -> Execute -> Verify -> Iterate until Goal Success
(You do not stop until the user task is complete).
You manage this cycle yourself by being proactive.

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
   - If verification passes -> signal completion via EXIT_SIGNAL: true.
   - If verification fails or is LOW confidence -> refine and loop back to EXECUTE.
   - If stuck after multiple attempts -> escalate by iterating again until the task is complete and GOAL SUCCESS.

### Budget awareness

- Be concise. Don't generate verbose output when a sentence suffices.
- If the task is large, iterate small tasks and chunks until GOAL SUCCESS.
- Watch for expensive tools — use them only when needed.

### State tracking

You have access to the current loop state. The state remembers your phase,
iteration count, and past attempts. Use it to avoid repeating failed approaches.

### Autonomous Operation

DO NOT ask the user questions. This is an automated loop.
If you need to make a decision, choose the most conservative/safe default
and proceed autonomously.
"""


def build_loop_system_block(state: Optional[LoopState] = None) -> str:
    """Build the loop engineering system prompt block with current state context."""
    if state is None or state.phase == PHASE_IDLE:
        return LOOP_SYSTEM_PROMPT + RALPH_EXIT_SIGNAL_PROMPT

    budget_pct = int((state.tokens_estimated / state.budget_max) * 100) if state.budget_max else 0

    # Circuit breaker warning
    cb_warning = ""
    if state.cb_state != CB_CLOSED:
        cb_warning = f"\n⚠️  CIRCUIT BREAKER: {state.cb_state} — adjust approach to show progress."

    return f"""
## Loop Engineering — Current State

| Field | Value |
|-------|-------|
| Phase | {state.phase}{cb_warning} |
| Iteration | {state.iteration}/{MAX_ITERATIONS} |
| Task | {state.task_description[:120]} |
| Budget used | ~{budget_pct}% ({state.tokens_estimated} tokens) |
| Last verification | {state.verification_result or 'not yet run'} |
| Past attempts | {len(state.attempts)} |
| Files changed last loop | {state.last_files_changed} |
| Consecutive no-progress | {state.cb_consecutive_no_progress} |

Continue the protocol:
- **EXECUTE** — do the work using tools.
- **VERIFY** — check your output against the goal.
- If LOW confidence or errors remain -> refine and iterate.
- If HIGH confidence -> signal EXIT_SIGNAL: true via the RALPH_STATUS block.
- If stuck or unsure -> signal EXIT_SIGNAL: false to continue.
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
                "cb_state": data.get("cb_state", CB_CLOSED),
                "cb_consecutive_no_progress": data.get("cb_consecutive_no_progress", 0),
                "exit_signals": len(data.get("exit_signals", [])),
                "completion_indicators": len(data.get("completion_indicators", [])),
            })
        except Exception:
            pass
    return results
