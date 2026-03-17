"""Factory to create the appropriate database implementation."""

from __future__ import annotations

import structlog

from common.config.app_config import AppConfig
from common.database.database_base import DatabaseBase

logger = structlog.get_logger(__name__)


async def create_database(config: AppConfig) -> DatabaseBase:
    """Create and initialise the database based on configuration.

    Uses CosmosDB when explicitly configured or when credentials are
    provided; otherwise falls back to an in-memory implementation.
    """
    use_cosmos = (
        config.database_backend == "cosmosdb"
        or (config.cosmos_db.key and config.database_backend != "in_memory")
    )

    if use_cosmos:
        from common.database.cosmosdb import CosmosDBDatabase

        db = CosmosDBDatabase(config.cosmos_db)
        await db.initialize()
        logger.info("database_provider", provider="cosmosdb")
        return db

    from common.database.in_memory import InMemoryDatabase

    db = InMemoryDatabase()
    await db.initialize()
    logger.info("database_provider", provider="in_memory")
    return db
