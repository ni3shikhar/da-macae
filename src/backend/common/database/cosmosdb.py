"""Azure Cosmos DB implementation of the database interface."""

from __future__ import annotations

from typing import Any, Optional

import structlog
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient

from common.config.app_config import CosmosDBConfig
from common.database.database_base import DatabaseBase

logger = structlog.get_logger(__name__)


class CosmosDBDatabase(DatabaseBase):
    """Azure Cosmos DB (NoSQL) implementation.

    Uses a single container with ``user_id`` as partition key.
    Document types are distinguished by a ``doc_type`` field.
    """

    def __init__(self, config: CosmosDBConfig) -> None:
        self._config = config
        self._client: AsyncCosmosClient | None = None
        self._container = None

    async def initialize(self) -> None:
        """Create the async client and ensure database/container exist."""
        self._client = AsyncCosmosClient(
            self._config.endpoint, credential=self._config.key
        )
        database = await self._client.create_database_if_not_exists(
            id=self._config.database_name
        )
        self._container = await database.create_container_if_not_exists(
            id=self._config.container_name,
            partition_key=PartitionKey(path="/user_id"),
        )
        logger.info(
            "cosmosdb_initialized",
            database=self._config.database_name,
            container=self._config.container_name,
        )

    async def close(self) -> None:
        """Close the async client."""
        if self._client:
            await self._client.close()

    # ── Document CRUD ──────────────────────────────────────────────────

    async def create_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        document["user_id"] = partition_key
        result = await self._container.create_item(body=document)
        return result

    async def read_document(
        self, document_id: str, partition_key: str
    ) -> Optional[dict[str, Any]]:
        try:
            return await self._container.read_item(
                item=document_id, partition_key=partition_key
            )
        except Exception:
            return None

    async def upsert_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        document["user_id"] = partition_key
        return await self._container.upsert_item(body=document)

    async def delete_document(
        self, document_id: str, partition_key: str
    ) -> None:
        await self._container.delete_item(
            item=document_id, partition_key=partition_key
        )

    async def query_documents(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        items = self._container.query_items(
            query=query,
            parameters=parameters or [],
            partition_key=partition_key,
        )
        return [item async for item in items]

    # ── Plan Operations ────────────────────────────────────────────────

    async def get_plans_by_user(self, user_id: str) -> list[dict[str, Any]]:
        return await self.query_documents(
            query="SELECT * FROM c WHERE c.doc_type = 'plan' AND c.user_id = @uid ORDER BY c.created_at DESC",
            parameters=[{"name": "@uid", "value": user_id}],
            partition_key=user_id,
        )

    async def get_plan(
        self, plan_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        results = await self.query_documents(
            query="SELECT * FROM c WHERE c.doc_type = 'plan' AND c.plan_id = @pid AND c.user_id = @uid",
            parameters=[
                {"name": "@pid", "value": plan_id},
                {"name": "@uid", "value": user_id},
            ],
            partition_key=user_id,
        )
        return results[0] if results else None

    # ── Agent Message Operations ───────────────────────────────────────

    async def get_messages_by_plan(
        self, plan_id: str
    ) -> list[dict[str, Any]]:
        return await self.query_documents(
            query="SELECT * FROM c WHERE c.doc_type = 'agent_message' AND c.plan_id = @pid ORDER BY c.timestamp ASC",
            parameters=[{"name": "@pid", "value": plan_id}],
        )

    async def save_agent_message(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        message["doc_type"] = "agent_message"
        user_id = message.get("user_id", "system")
        return await self.upsert_document(message, partition_key=user_id)

    # ── Team Config Operations ─────────────────────────────────────────

    async def get_team_configs(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        # Get both user-specific and system-level team configs
        return await self.query_documents(
            query="SELECT * FROM c WHERE c.doc_type = 'team_config' AND (c.user_id = @uid OR c.user_id = 'system')",
            parameters=[{"name": "@uid", "value": user_id}],
        )

    async def get_team_config(
        self, team_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        results = await self.query_documents(
            query="SELECT * FROM c WHERE c.doc_type = 'team_config' AND c.id = @tid AND (c.user_id = @uid OR c.user_id = 'system')",
            parameters=[
                {"name": "@tid", "value": team_id},
                {"name": "@uid", "value": user_id},
            ],
        )
        return results[0] if results else None

    async def save_team_config(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        config["doc_type"] = "team_config"
        user_id = config.get("user_id", "system")
        return await self.upsert_document(config, partition_key=user_id)
