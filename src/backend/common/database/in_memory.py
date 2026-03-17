"""In-memory database implementation for local development and testing."""

from __future__ import annotations

import copy
from typing import Any, Optional

import structlog

from common.database.database_base import DatabaseBase

logger = structlog.get_logger(__name__)


class InMemoryDatabase(DatabaseBase):
    """Simple in-memory document store for development without Cosmos DB.

    Documents are stored in a flat dictionary keyed by ``(partition_key, id)``.
    Query support is limited to specific pre-defined patterns.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, Any]] = {}

    async def initialize(self) -> None:
        logger.info("in_memory_database_initialized")

    async def close(self) -> None:
        self._store.clear()

    # ── Document CRUD ──────────────────────────────────────────────────

    async def create_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        doc = copy.deepcopy(document)
        doc["user_id"] = partition_key
        key = (partition_key, doc["id"])
        if key in self._store:
            raise ValueError(f"Document {doc['id']} already exists")
        self._store[key] = doc
        return doc

    async def read_document(
        self, document_id: str, partition_key: str
    ) -> Optional[dict[str, Any]]:
        doc = self._store.get((partition_key, document_id))
        return copy.deepcopy(doc) if doc else None

    async def upsert_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        doc = copy.deepcopy(document)
        doc["user_id"] = partition_key
        self._store[(partition_key, doc["id"])] = doc
        return doc

    async def delete_document(
        self, document_id: str, partition_key: str
    ) -> None:
        self._store.pop((partition_key, document_id), None)

    async def query_documents(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Basic query support — matches on doc_type and parameter fields."""
        params = {p["name"]: p["value"] for p in (parameters or [])}
        results: list[dict[str, Any]] = []

        for (_pk, _id), doc in self._store.items():
            if partition_key and _pk != partition_key:
                continue
            # Simple field matching based on query parameters
            match = True
            for name, value in params.items():
                field = name.lstrip("@")
                # Map common parameter names to document fields
                field_map = {"uid": "user_id", "pid": "plan_id", "tid": "id"}
                doc_field = field_map.get(field, field)
                if doc.get(doc_field) != value:
                    match = False
                    break
            if match:
                results.append(copy.deepcopy(doc))
        return results

    # ── Plan Operations ────────────────────────────────────────────────

    async def get_plans_by_user(self, user_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(doc)
            for (_pk, _id), doc in self._store.items()
            if doc.get("doc_type") == "plan" and doc.get("user_id") == user_id
        ]

    async def get_plan(
        self, plan_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        for (_pk, _id), doc in self._store.items():
            if (
                doc.get("doc_type") == "plan"
                and doc.get("plan_id") == plan_id
                and doc.get("user_id") == user_id
            ):
                return copy.deepcopy(doc)
        return None

    # ── Agent Message Operations ───────────────────────────────────────

    async def get_messages_by_plan(
        self, plan_id: str
    ) -> list[dict[str, Any]]:
        return sorted(
            [
                copy.deepcopy(doc)
                for (_pk, _id), doc in self._store.items()
                if doc.get("doc_type") == "agent_message"
                and doc.get("plan_id") == plan_id
            ],
            key=lambda d: d.get("timestamp", ""),
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
        return [
            copy.deepcopy(doc)
            for (_pk, _id), doc in self._store.items()
            if doc.get("doc_type") == "team_config"
            and doc.get("user_id") in (user_id, "system")
        ]

    async def get_team_config(
        self, team_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        for (_pk, _id), doc in self._store.items():
            if (
                doc.get("doc_type") == "team_config"
                and doc.get("id") == team_id
                and doc.get("user_id") in (user_id, "system")
            ):
                return copy.deepcopy(doc)
        return None

    async def save_team_config(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        config["doc_type"] = "team_config"
        user_id = config.get("user_id", "system")
        return await self.upsert_document(config, partition_key=user_id)
