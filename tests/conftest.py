"""pytest configuration and shared fixtures for Cogent integration tests.

Provides:
- ``test_db`` — an in-memory Motor mongo collection set (mocked via dicts)
- ``loop_state`` — a fresh ``LoopState`` for state-machine tests

The fake-Motor classes live in ``conftest_helpers.py`` so they can be
imported by any test file (conftest modules are pytest plugins and cannot
be imported as regular Python modules).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import AsyncGenerator

import pytest

# Ensure *this* directory is on sys.path so conftest_helpers can be imported.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from conftest_helpers import FakeMotorDatabase  # noqa: E402

# Ensure the backend package is on sys.path so we can import production code.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Stub dotenv so tests don't require a .env file ─────────────────────────
@pytest.fixture(autouse=True)
def _stub_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace real dotenv with a no-op module so tests never fail on a
    missing ``.env`` file."""
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda path: None  # type: ignore[method-assign]
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_stub)


# ── Stub the KiloCode API key (required by some code paths) ────────────────
@pytest.fixture(autouse=True)
def _stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a KiloCode key is present so provider-import code paths don't
    crash on startup — the tests that call those paths will override as
    needed."""
    monkeypatch.setenv("KILOCODE_API_KEY", "test-key-00000000")


# ── In-memory database fixture ────────────────────────────────────────────

@pytest.fixture
async def test_db() -> AsyncGenerator[FakeMotorDatabase, None]:
    """An in-memory Motor-like database for integration tests.

    Each test gets a fresh database with empty collections.  No real
    MongoDB process is required.
    """
    db = FakeMotorDatabase()
    yield db


# ── Loop state fixture ─────────────────────────────────────────────────────
@pytest.fixture
def loop_state():
    """Return a ``LoopState`` instance isolated to a random session id."""
    import loop_engine as le
    state = le.LoopState(session_id="test-session-0000")
    le.init_circuit_breaker(state)
    return state
