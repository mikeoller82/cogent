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

Extended with Loop Engineering framework (Oller 2025):
  - Goal Representation: structured task + criteria + constraints + stop conditions
  - State Model: 5 differentiated layers (static/dynamic/tool/reflective/governance)
  - Observation Collector: structured observation records (success/failure/partial)
  - Evaluator: 4 signals per iteration (confidence, progress, drift, risk)
  - Controller: organized policy set (confidence threshold, risk budget, progress score, entropy, escalation)
  - Loop Trace: structured iteration records per Appendix B schema
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

# ── Structured dataclasses (Loop Engineering framework) ─────────────────


@dataclass
class GoalRepr:
    """Structured goal representation — task, criteria, constraints, stop conditions."""
    task: str = ""
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    stop_conditions: List[str] = field(default_factory=list)


@dataclass
class Observation:
    """Structured observation record — what actually happened vs what was intended."""
    status: str = ""           # success | failure | partial
    action_type: str = ""
    target: str = ""
    input_summary: str = ""
    output_summary: str = ""
    error: str = ""
    timestamp: str = ""


@dataclass
class EvaluationSignals:
    """Four signals the evaluator produces each iteration + legacy verdict."""
    confidence: str = "medium"   # low | medium | high
    progress: str = "medium"     # low | medium | high | negative
    drift: str = "low"           # low | medium | high
    risk: str = "low"            # low | medium | high | critical
    verdict: str = ""            # PASS | FAIL | PARTIAL (legacy compat)
    notes: str = ""


# ── Debounce constants ────────────────────────────────────────────────────
SAVE_DEBOUNCE_LIMIT = 5
_pending_save_count: Dict[str, int] = {}

# ── Constants ────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
LOOP_STATE_DIR = PROJECT_ROOT / "memory" / "loops"

MAX_ITERATIONS = 90
MAX_TOKENS_PER_TASK = 100_000
WARN_TOKEN_PCT = 0.75
CONTINUE_MAX = 90

PHASE_IDLE = "idle"
PHASE_PLAN = "plan"
PHASE_EXECUTE = "execute"
PHASE_VERIFY = "verify"
PHASE_DONE = "done"
PHASE_ESCALATE = "escalate"
PHASE_ERROR = "error"

VALID_PHASES = {PHASE_IDLE, PHASE_PLAN, PHASE_EXECUTE, PHASE_VERIFY,
                PHASE_DONE, PHASE_ESCALATE, PHASE_ERROR}

CB_CLOSED = "CLOSED"
CB_HALF_OPEN = "HALF_OPEN"
CB_OPEN = "OPEN"

CB_NO_PROGRESS_THRESHOLD = 3
CB_SAME_ERROR_THRESHOLD = 5
CB_NO_PROGRESS_WARN = 2
CB_COOLDOWN_SECONDS = 1800

MAX_CONSECUTIVE_TEST_LOOPS = 3
MAX_CONSECUTIVE_DONE_SIGNALS = 5
SAFETY_CIRCUIT_BREAKER_LIMIT = 12

MAX_SAME_ARGS_CALLS = 5
MAX_CONSECUTIVE_FAILURES = 3
MAX_CRITICAL_FAILURES = 8
TOOL_FAILURE_HISTORY_MAX = 50

CONTROLLER_ENTROPY_THRESHOLD = 0.5
CONTROLLER_LOW_CONFIDENCE_REVISION_LIMIT = 3

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

RALPH_STATUS_RE = re.compile(
    r"^[ \t]*(?:---RALPH_STATUS---|---END_RALPH_STATUS---|RALPH_STATUS:)", re.MULTILINE
)
EXIT_SIGNAL_RE = re.compile(r"^[ \t]*EXIT_SIGNAL:\s*(true|false)", re.MULTILINE)
STATUS_RE = re.compile(r"^[ \t]*STATUS:\s*(\w+)", re.MULTILINE)


# ── State ────────────────────────────────────────────────────────────────

@dataclass
class LoopState:
    """Persistent loop state for one session.

    State layers (Loop Engineering framework):
      - Static: session_id, started_at, goal_representation (immutable after start)
      - Dynamic: phase, iteration, attempts, last_output*, current plan
      - Tool: tool_failure_history, observations
      - Reflective: reflective_lessons
      - Governance: cb_*, budget_*, risk_level, loop_trace
    """
    session_id: str
    phase: str = PHASE_IDLE
    iteration: int = 0
    task_description: str = ""
    verification_criteria: List[str] = field(default_factory=list)
    continue_count: int = 0
    last_plan_text: str = ""

    goal_representation: GoalRepr = field(default_factory=GoalRepr)
    reflective_lessons: List[str] = field(default_factory=list)
    loop_trace: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    risk_level: str = "low"

    attempts: List[Dict[str, Any]] = field(default_factory=list)
    tokens_estimated: int = 0
    errors: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)

    last_output_summary: str = ""
    verification_result: Optional[str] = None
    verification_notes: str = ""

    budget_max: int = MAX_TOKENS_PER_TASK
    budget_warn_pct: float = WARN_TOKEN_PCT

    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    cb_state: str = CB_CLOSED
    cb_consecutive_no_progress: int = 0
    cb_consecutive_same_error: int = 0
    cb_last_progress_loop: int = 0
    cb_total_opens: int = 0
    cb_opened_at: Optional[str] = None

    exit_signals: List[int] = field(default_factory=list)
    explicit_exit_signals: List[int] = field(default_factory=list)
    completion_indicators: List[int] = field(default_factory=list)
    done_signals: List[int] = field(default_factory=list)
    test_only_loops: List[int] = field(default_factory=list)

    tool_failure_history: List[tuple] = field(default_factory=list)
    tool_loop_detected_stop: bool = False

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
    path = _state_path(session_id)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = LoopState(**data)
            if isinstance(state.goal_representation, dict):
                state.goal_representation = GoalRepr(**state.goal_representation)
            if state.observations and isinstance(state.observations[0], dict):
                state.observations = [Observation(**o) for o in state.observations]
            return state
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Corrupt loop state for %s: %s; starting fresh", session_id, exc)
    return LoopState(session_id=session_id)


def save_state(state: LoopState, force: bool = False) -> None:
    sid = state.session_id
    count = _pending_save_count.get(sid, 0) + 1
    _pending_save_count[sid] = count
    if not force and count < SAVE_DEBOUNCE_LIMIT:
        return
    _pending_save_count[sid] = 0
    state.updated_at = datetime.utcnow().isoformat() + "Z"
    path = _state_path(state.session_id)
    path.write_text(json.dumps(asdict(state), indent=2, default=str), encoding="utf-8")


# ── State transitions ────────────────────────────────────────────────────

def transition(state: LoopState, new_phase: str, note: str = "") -> None:
    if new_phase not in VALID_PHASES:
        logger.warning("Invalid phase %s; ignoring", new_phase)
        return
    old = state.phase
    state.phase = new_phase
    if note:
        state.decisions.append(f"[{old}->{new_phase}] {note}")
    logger.debug("Loop %s: %s -> %s -- %s", state.session_id, old, new_phase, note)


def begin_task(state: LoopState, task: str, criteria: Optional[List[str]] = None) -> None:
    state.phase = PHASE_PLAN
    state.iteration = 0
    state.task_description = task
    state.verification_criteria = criteria or []
    state.goal_representation = GoalRepr(
        task=task,
        success_criteria=criteria or [],
    )
    state.reflective_lessons = []
    state.loop_trace = []
    state.observations = []
    state.risk_level = "low"
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
    state.cb_state = CB_CLOSED
    state.cb_consecutive_no_progress = 0
    state.cb_consecutive_same_error = 0
    state.cb_last_progress_loop = 0
    state.exit_signals = []
    state.explicit_exit_signals = []
    state.completion_indicators = []
    state.done_signals = []
    state.test_only_loops = []
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
    save_state(state)


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


# ── Circuit Breaker ──────────────────────────────────────────────────────

def init_circuit_breaker(state: LoopState) -> None:
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
    init_circuit_breaker(state)

    if has_progress or files_changed > 0:
        state.cb_consecutive_no_progress = 0
        state.cb_last_progress_loop = loop_number
    elif exit_signal:
        state.cb_consecutive_no_progress = 0
        state.cb_last_progress_loop = loop_number
    else:
        state.cb_consecutive_no_progress += 1

    if has_errors:
        state.cb_consecutive_same_error += 1
    else:
        state.cb_consecutive_same_error = 0

    state.last_files_changed = files_changed
    state.last_errors_detected = has_errors

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
    """Check if execution should halt via circuit breaker.

    When the circuit breaker is OPEN, execution halts to prevent
    wasted iterations on a stuck loop.
    """
    init_circuit_breaker(state)
    if state.cb_state == CB_OPEN:
        return True
    return False


# ── Tool-loop guardrail functions ────────────────────────────────────────

import hashlib


def _hash_args(args: dict) -> str:
    args_str = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(args_str.encode()).hexdigest()[:8]


def record_tool_result(state: LoopState, tool_name: str, args: dict, success: bool) -> None:
    args_hash = _hash_args(args)
    state.tool_failure_history.append((tool_name, args_hash, success))
    if len(state.tool_failure_history) > TOOL_FAILURE_HISTORY_MAX:
        state.tool_failure_history = state.tool_failure_history[-TOOL_FAILURE_HISTORY_MAX:]
    save_state(state)


def check_tool_loop(state: LoopState, tool_name: str, args: dict) -> tuple[bool, str, bool]:
    args_hash = _hash_args(args)

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


# ── Observation Collector (Loop Engineering) ────────────────────────────

def record_observation(state: LoopState, obs: Observation) -> None:
    if not obs.timestamp:
        obs.timestamp = datetime.utcnow().isoformat() + "Z"
    state.observations.append(obs)
    save_state(state)


# ── Entropy Detection (Loop Engineering) ────────────────────────────────

def detect_entropy(state: LoopState, analysis: dict) -> float:
    """Detect uncertainty/instability signals. Returns 0.0-1.0 score.

    High entropy means the agent is uncertain, conflicted, or stuck.
    """
    signals = 0.0

    if analysis.get("asking_questions"):
        signals += 0.25

    if state.tool_loop_detected_stop:
        signals += 0.3

    if state.cb_consecutive_same_error >= 2:
        signals += 0.2 * min(state.cb_consecutive_same_error, 5) / 5

    if state.cb_consecutive_no_progress >= CB_NO_PROGRESS_WARN:
        signals += 0.15 * min(state.cb_consecutive_no_progress, 5) / 5

    if analysis.get("is_stuck"):
        signals += 0.3

    if len(state.loop_trace) >= 3:
        recent_decisions = [t.get("controller_decision", "") for t in state.loop_trace[-3:]]
        if len(set(recent_decisions)) >= 3:
            signals += 0.2

    return min(signals, 1.0)


# ── Risk Classification (Loop Engineering) ──────────────────────────────

HIGH_RISK_ACTIONS = {"run_shell", "file_write", "capture_screenshot", "process_media"}
MEDIUM_RISK_ACTIONS = {"schedule_task", "save_memory", "import_skill",
                       "agent_reach_doctor", "generate_pdf", "generate_webapp"}
LOW_RISK_ACTIONS = {"web_search", "web_scrape", "recall_memory", "youtube_transcript",
                    "github_repo_info", "github_search", "github_search_code",
                    "v2ex_hot_topics", "v2ex_topic_detail", "rss_read", "bilibili_search",
                    "activate_skill", "read_skill_resource", "get_loop_state"}


def classify_action_risk(action_type: str, args: dict) -> str:
    if action_type in HIGH_RISK_ACTIONS:
        return "high"
    elif action_type in MEDIUM_RISK_ACTIONS:
        return "medium"
    elif action_type in LOW_RISK_ACTIONS:
        return "low"
    return "medium"


def update_risk_level(state: LoopState, action_type: str, args: dict) -> None:
    action_risk = classify_action_risk(action_type, args)
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    current = risk_order.get(state.risk_level, 0)
    proposed = risk_order.get(action_risk, 0)
    if proposed > current:
        state.risk_level = action_risk
        state.decisions.append(f"Risk level raised to {action_risk} (action: {action_type})")
        save_state(state, force=True)


# ── Progress Scorer (Loop Engineering) ──────────────────────────────────

def score_progress(state: LoopState, analysis: dict) -> str:
    if analysis.get("has_completion_signal") and analysis.get("confidence_score", 0) >= 50:
        return "high"

    if state.last_files_changed > 0:
        return "high"

    if analysis.get("exit_signal") and analysis.get("has_completion_signal"):
        return "high"

    if state.cb_consecutive_no_progress >= CB_NO_PROGRESS_THRESHOLD:
        return "negative"

    if analysis.get("is_stuck"):
        return "negative"

    if state.cb_consecutive_no_progress >= CB_NO_PROGRESS_WARN:
        return "low"

    if state.cb_state == CB_HALF_OPEN:
        return "low"

    return "medium"


# ── Controller (Loop Engineering) ────────────────────────────────────────

def controller_step(state: LoopState, eval_signals: EvaluationSignals,
                    analysis: dict) -> str:
    """Run controller policies and return a decision.

    Decisions: continue | revise | escalate | stop
    """
    if state.budget_exhausted:
        return "escalate"

    if state.risk_level == "critical":
        return "escalate"

    entropy = detect_entropy(state, analysis)
    if entropy >= CONTROLLER_ENTROPY_THRESHOLD:
        if state.risk_level in ("high", "critical"):
            return "escalate"
        return "revise"

    progress = score_progress(state, analysis)

    if progress == "negative":
        return "revise"

    if eval_signals.confidence == "low":
        if len(state.loop_trace) >= CONTROLLER_LOW_CONFIDENCE_REVISION_LIMIT:
            return "escalate"
        return "revise"

    if eval_signals.verdict == "PASS":
        return "stop"

    if progress == "low":
        return "revise"

    if eval_signals.verdict in ("FAIL", "PARTIAL"):
        return "revise"

    return "continue"


# ── Loop Trace (Appendix B schema) ──────────────────────────────────────

def record_loop_trace(state: LoopState, signals: EvaluationSignals,
                      decision: str, analysis: dict) -> dict:
    trace = {
        "iteration": state.iteration,
        "goal": {
            "task": state.goal_representation.task or state.task_description,
            "success_criteria": (state.goal_representation.success_criteria
                                 or state.verification_criteria),
        },
        "plan": {
            "current_phase": state.phase,
        },
        "evaluation": {
            "confidence": signals.confidence,
            "progress": signals.progress,
            "drift": signals.drift,
            "risk": signals.risk,
        },
        "controller_decision": decision,
        "entropy_score": detect_entropy(state, analysis),
        "risk_level": state.risk_level,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    state.loop_trace.append(trace)
    return trace


# ── Response Analysis (Ralph-style) ──────────────────────────────────────

def parse_ralph_status_block(text: str) -> dict:
    result = {"exit_signal": None, "explicit": False}

    if not RALPH_STATUS_RE.search(text):
        return result

    m = EXIT_SIGNAL_RE.search(text)
    if m:
        result["exit_signal"] = m.group(1) == "true"
        result["explicit"] = True
        return result

    m = STATUS_RE.search(text)
    if m and m.group(1).upper() == "COMPLETE":
        result["exit_signal"] = True

    return result


def count_questions(text: str) -> int:
    count = 0
    for pattern in QUESTION_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        except re.error:
            pass
    return count


def analyze_response_text(text: str) -> dict:
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

    status = parse_ralph_status_block(text)
    if status["explicit"]:
        result["exit_signal"] = status["exit_signal"]
        result["explicit_exit_signal"] = True
        if status["exit_signal"]:
            result["has_completion_signal"] = True
            result["confidence_score"] = 100

    for keyword in COMPLETION_KEYWORDS:
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text.lower()):
            result["has_completion_signal"] = True
            result["confidence_score"] += 10

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

    error_count = len(re.findall(
        r"(^Error:|^ERROR:|^error:|\]: error|Link: error|"
        r"Error occurred|failed with error|[Ee]xception|Fatal|FATAL)",
        text, re.MULTILINE
    ))
    if error_count > 5:
        result["is_stuck"] = True

    for pattern in NO_WORK_PATTERNS:
        if pattern.lower() in text.lower():
            result["has_completion_signal"] = True
            result["confidence_score"] += 15
            result["work_summary"] = "No work remaining"

    q_count = count_questions(text)
    result["question_count"] = q_count
    if q_count > 0:
        result["asking_questions"] = True

    if not result["explicit_exit_signal"]:
        if result["confidence_score"] >= 70 and result["has_completion_signal"]:
            result["exit_signal"] = True

    if not result["work_summary"]:
        summary_match = re.search(
            r"(?i)(summary|completed|implemented)[:\s]+(.+?)(?:\n|$)", text
        )
        if summary_match:
            result["work_summary"] = summary_match.group(2).strip()[:100]
        else:
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 30]
            result["work_summary"] = lines[0][:100] if lines else "Output analyzed"

    return result


def update_exit_signals(state: LoopState, analysis: dict) -> None:
    loop_num = state.iteration

    if analysis.get("is_test_only"):
        state.test_only_loops.append(loop_num)
    elif analysis.get("has_completion_signal", False) or analysis.get("has_progress", False):
        state.test_only_loops = []

    if analysis.get("has_completion_signal"):
        state.done_signals.append(loop_num)

    if analysis.get("exit_signal"):
        state.completion_indicators.append(loop_num)
        state.exit_signals.append(loop_num)
        if analysis.get("explicit_exit_signal"):
            state.explicit_exit_signals.append(loop_num)

    state.test_only_loops = state.test_only_loops[-5:]
    state.done_signals = state.done_signals[-5:]
    state.completion_indicators = state.completion_indicators[-5:]
    state.exit_signals = state.exit_signals[-5:]
    state.explicit_exit_signals = state.explicit_exit_signals[-5:]

    save_state(state)


def should_exit_gracefully(state: LoopState) -> Optional[str]:
    """Check exit conditions based on done-signal saturation.

    Returns a reason string if the agent should exit, None otherwise.
    """
    done_count = len(state.done_signals)
    exit_count = len(state.exit_signals)

    if done_count >= MAX_CONSECUTIVE_DONE_SIGNALS:
        return f"Done signal saturation ({done_count} done signals)"
    if exit_count >= SAFETY_CIRCUIT_BREAKER_LIMIT:
        return f"Exit signal saturation ({exit_count} exit signals)"
    if len(state.test_only_loops) >= MAX_CONSECUTIVE_TEST_LOOPS:
        return f"Test-only loop saturation ({len(state.test_only_loops)} test-only loops)"

    return None


# ── System prompt augmentation ──────────────────────────────────────────

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
    if state is None or state.phase == PHASE_IDLE:
        return LOOP_SYSTEM_PROMPT + RALPH_EXIT_SIGNAL_PROMPT

    budget_pct = int((state.tokens_estimated / state.budget_max) * 100) if state.budget_max else 0

    cb_warning = ""
    if state.cb_state != CB_CLOSED:
        cb_warning = f"\n⚠️  CIRCUIT BREAKER: {state.cb_state} — adjust approach to show progress."

    lessons_block = ""
    if state.reflective_lessons:
        lessons = "\n".join(f"- {l}" for l in state.reflective_lessons[-3:])
        lessons_block = f"\n### Lessons from prior iterations\n{lessons}\n"

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
| Risk level | {state.risk_level}{lessons_block}

Continue the protocol:
- **EXECUTE** — do the work using tools.
- **VERIFY** — check your output against the goal.
- If LOW confidence or errors remain -> refine and iterate.
- If HIGH confidence -> signal EXIT_SIGNAL: true via the RALPH_STATUS block.
- If stuck or unsure -> signal EXIT_SIGNAL: false to continue.
"""


# ── Evaluation prompt builder ───────────────────────────────────────────

def build_evaluation_prompt(task: str, output: str, criteria: List[str],
                            recent_observations: Optional[List[Observation]] = None) -> str:
    criteria_block = "\n".join(f"- {c}" for c in criteria) if criteria else "- Meets the stated goal"

    obs_block = ""
    if recent_observations:
        obs_lines = [f"  - {o.action_type}: {o.status} — {o.output_summary[:80]}"
                     for o in recent_observations[-5:]]
        obs_block = "\n## Recent observations\n" + "\n".join(obs_lines)

    return f"""You are a quality evaluator. Assess the output against the task requirements.

## Task
{task}

## Verification criteria
{criteria_block}
{obs_block}
## Output to evaluate
{output}

## Response format
CONFIDENCE: high | medium | low
PROGRESS: high | medium | low | negative
DRIFT: high | medium | low
RISK: high | medium | low | critical
VERDICT: PASS | FAIL | PARTIAL
NOTES: Brief explanation for the ratings
"""


# ── Verification helper (legacy) ─────────────────────────────────────────

def build_verification_prompt(task: str, output: str, criteria: List[str]) -> str:
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


async def run_evaluation(task: str, output: str, criteria: List[str],
                         llm_complete_fn,
                         recent_observations: Optional[List[Observation]] = None
                         ) -> EvaluationSignals:
    """Run the enhanced evaluator with 4 signals (confidence, progress, drift, risk).

    Returns an ``EvaluationSignals`` dataclass.
    """
    prompt = build_evaluation_prompt(task, output, criteria, recent_observations)
    try:
        result = await llm_complete_fn(prompt)
        result = result.strip()
    except Exception as exc:
        logger.warning("Evaluation call failed: %s", exc)
        return EvaluationSignals(verdict="PARTIAL", notes=f"Evaluator error: {exc}",
                                 confidence="low", progress="low", drift="medium", risk="medium")

    signals = EvaluationSignals()

    for line in result.split("\n"):
        line = line.strip()
        lower = line.lower()

        if lower.startswith("confidence:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("high", "medium", "low"):
                signals.confidence = val

        elif lower.startswith("progress:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("high", "medium", "low", "negative"):
                signals.progress = val

        elif lower.startswith("drift:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("high", "medium", "low"):
                signals.drift = val

        elif lower.startswith("risk:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("high", "medium", "low", "critical"):
                signals.risk = val

        elif lower.startswith("verdict:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("PASS", "FAIL", "PARTIAL"):
                signals.verdict = val

        elif lower.startswith("notes:"):
            signals.notes = line.split(":", 1)[1].strip()[:300]

    if not signals.verdict:
        for v in ("PASS", "FAIL", "PARTIAL"):
            if result.startswith(v):
                signals.verdict = v
                break
        if not signals.notes:
            signals.notes = result[:300]

    return signals


# ── Reflection (Loop Engineering) ───────────────────────────────────────

def build_reflection_prompt(task: str, output: str, verdict: str,
                            verifier_notes: str, attempts_count: int) -> str:
    return f"""You are a reflective analyst. Review the following attempt and identify
one concrete lesson that will improve the next attempt.

## Task
{task}

## Previous output
{output[:500]}

## Verification result
Verdict: {verdict}
Notes: {verifier_notes}

## Attempt number
{attempts_count}

## Response format
LESSON: One sentence describing what to do differently.
"""


async def run_reflection(task: str, output: str, verdict: str,
                         verifier_notes: str, attempts_count: int,
                         llm_complete_fn) -> Optional[str]:
    prompt = build_reflection_prompt(task, output, verdict, verifier_notes, attempts_count)
    try:
        result = await llm_complete_fn(prompt)
        result = result.strip()
        for prefix in ("LESSON:", "lesson:"):
            if result.upper().startswith(prefix.upper()):
                return result[len(prefix):].strip()[:200]
        return result[:200]
    except Exception as exc:
        logger.warning("Reflection call failed: %s", exc)
        return None


def store_reflective_lesson(state: LoopState, lesson: str) -> None:
    if lesson:
        state.reflective_lessons.append(
            f"Iteration {state.iteration}: {lesson}"
        )
        save_state(state, force=True)


# ── State layer summary (Loop Engineering) ─────────────────────────────

def state_layer_summary(state: LoopState) -> dict:
    return {
        "static": {
            "session_id": state.session_id,
            "task": state.goal_representation.task or state.task_description,
            "started_at": state.started_at,
        },
        "dynamic": {
            "phase": state.phase,
            "iteration": state.iteration,
            "attempts_count": len(state.attempts),
            "last_output_summary": state.last_output_summary,
            "has_output": bool(state.last_output_summary),
        },
        "tool": {
            "tool_calls": len(state.tool_failure_history),
            "observations": len(state.observations),
            "tool_loop_detected": state.tool_loop_detected_stop,
        },
        "reflective": {
            "lessons_count": len(state.reflective_lessons),
            "latest_lessons": state.reflective_lessons[-3:] if state.reflective_lessons else [],
        },
        "governance": {
            "cb_state": state.cb_state,
            "risk_level": state.risk_level,
            "budget_pct": int((state.tokens_estimated / state.budget_max) * 100) if state.budget_max else 0,
            "trace_count": len(state.loop_trace),
            "decisions_count": len(state.decisions),
        },
    }


# ── Metrics ──────────────────────────────────────────────────────────────

def get_all_loop_states() -> List[Dict[str, Any]]:
    LOOP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for path in sorted(LOOP_STATE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
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
                "risk_level": data.get("risk_level", "low"),
                "reflective_lessons": len(data.get("reflective_lessons", [])),
            })
        except Exception:
            pass
    return results
