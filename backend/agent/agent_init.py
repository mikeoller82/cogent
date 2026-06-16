"""Agent initialization — bootstrap helper that wires config, logging, and state."""
from __future__ import annotations
import logging
import uuid

from cogent_config import get_config
from cogent_logging import set_session_context
from cogent_state import create_session, touch_session
from cogent_memory import memory_summary

logger = logging.getLogger("cogent.agent.agent_init")


def bootstrap_agent(session_id: str | None = None) -> str:
    """Initialize or resume an agent session. Returns session_id.

    1. Creates/loads session state
    2. Ensures logging context
    3. Returns ready session ID for the conversation loop
    """
    cfg = get_config()

    if session_id:
        touch_session(session_id)
        set_session_context(session_id)
        logger.info("Resumed session %s", session_id)
    else:
        session_id = str(uuid.uuid4())
        create_session(session_id)
        set_session_context(session_id)
        logger.info("Created session %s", session_id)

    memory = memory_summary()
    logger.debug("Memory facts loaded (%d chars)", len(memory))

    return str(session_id)
