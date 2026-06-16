"""Per-session iteration and token budget tracker.

Analogous to Hermes' ``iteration_budget.py`` — thread-safe consume/refund
counter for agent iterations, plus a token budget ceiling.

Usage::

    from cogent_budget import IterationBudget

    budget = IterationBudget(max_iterations=50, max_tokens=200_000)
    if budget.consume():
        # do work
        pass
    budget.refund()  # give back one iteration (e.g. for tool calls)
"""

from __future__ import annotations

import threading
from typing import Optional


class IterationBudget:
    """Thread-safe budget tracker for agent iterations and tokens.

    Each session or sub-agent gets its own ``IterationBudget``.
    """

    def __init__(self, max_iterations: int = 50,
                 max_tokens: int = 200_000) -> None:
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self._iterations_used = 0
        self._tokens_used = 0
        self._lock = threading.Lock()

    # ── Iteration budget ───────────────────────────────────────────────

    def consume(self) -> bool:
        """Try to consume one iteration.  Returns True if allowed."""
        with self._lock:
            if self._iterations_used >= self.max_iterations:
                return False
            self._iterations_used += 1
            return True

    def refund(self) -> None:
        """Give back one iteration (e.g. for tool-only turns)."""
        with self._lock:
            if self._iterations_used > 0:
                self._iterations_used -= 1

    @property
    def iterations_used(self) -> int:
        with self._lock:
            return self._iterations_used

    @property
    def iterations_remaining(self) -> int:
        with self._lock:
            return max(0, self.max_iterations - self._iterations_used)

    @property
    def iteration_exhausted(self) -> bool:
        with self._lock:
            return self._iterations_used >= self.max_iterations

    # ── Token budget ───────────────────────────────────────────────────

    def record_tokens(self, count: int) -> None:
        """Record *count* tokens consumed."""
        with self._lock:
            self._tokens_used += count

    @property
    def tokens_used(self) -> int:
        with self._lock:
            return self._tokens_used

    @property
    def tokens_remaining(self) -> int:
        with self._lock:
            return max(0, self.max_tokens - self._tokens_used)

    @property
    def token_exhausted(self) -> bool:
        with self._lock:
            return self._tokens_used >= self.max_tokens

    @property
    def exhausted(self) -> bool:
        """True if either budget is exhausted."""
        return self.iteration_exhausted or self.token_exhausted

    @property
    def warn_pct(self) -> float:
        """Return the fraction of the iteration budget used (0..1)."""
        with self._lock:
            return self._iterations_used / max(self.max_iterations, 1)

    # ── Dict representation (for persistence) ──────────────────────────

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "max_iterations": self.max_iterations,
                "max_tokens": self.max_tokens,
                "iterations_used": self._iterations_used,
                "tokens_used": self._tokens_used,
            }
