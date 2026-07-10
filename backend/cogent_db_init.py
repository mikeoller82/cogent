"""Database initialization and index creation.

Indexes here MUST match collections that the live code path actually writes
to. The user list lives in ``memory/users.json`` (see ``cogent_auth_v2``),
so we deliberately don't create a ``users`` collection in MongoDB.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger("cogent.db_init")


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create database indexes for performance.

    Idempotent — Motor's ``create_index`` is a no-op when the index exists.
    Failures are logged at WARNING so a missing Mongo replica can't wedge
    application startup.
    """
    try:
        # Sessions collection
        await db.sessions.create_index([("workspace_id", 1), ("updated_at", -1)])
        await db.sessions.create_index("id", unique=True)

        # Messages collection
        await db.messages.create_index([("session_id", 1), ("created_at", 1)])
        await db.messages.create_index("id", unique=True)

        # Memories collection
        await db.memories.create_index([("workspace_id", 1), ("key", 1)], unique=True)

        # Scheduled tasks collection
        await db.scheduled_tasks.create_index([("workspace_id", 1), ("status", 1)])
        await db.scheduled_tasks.create_index("id", unique=True)

        # Uploads collection
        await db.uploads.create_index([("workspace_id", 1), ("created_at", -1)])
        await db.uploads.create_index("id", unique=True)

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning("Failed to create indexes: %s", e)
