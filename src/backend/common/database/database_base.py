"""Abstract base class for database operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class DatabaseBase(ABC):
    """Abstract interface for document-based storage.

    All database implementations (CosmosDB, in-memory, etc.) must
    implement these methods.
    """

    # ── Document CRUD ──────────────────────────────────────────────────

    @abstractmethod
    async def create_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        """Create a new document."""
        ...

    @abstractmethod
    async def read_document(
        self, document_id: str, partition_key: str
    ) -> Optional[dict[str, Any]]:
        """Read a document by ID."""
        ...

    @abstractmethod
    async def upsert_document(
        self, document: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        """Create or update a document."""
        ...

    @abstractmethod
    async def delete_document(
        self, document_id: str, partition_key: str
    ) -> None:
        """Delete a document by ID."""
        ...

    @abstractmethod
    async def query_documents(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query documents using a SQL-like query."""
        ...

    # ── Plan Operations ────────────────────────────────────────────────

    @abstractmethod
    async def get_plans_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all plans for a user."""
        ...

    @abstractmethod
    async def get_plan(
        self, plan_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Get a specific plan."""
        ...

    # ── Agent Message Operations ───────────────────────────────────────

    @abstractmethod
    async def get_messages_by_plan(
        self, plan_id: str
    ) -> list[dict[str, Any]]:
        """Get all agent messages for a plan."""
        ...

    @abstractmethod
    async def save_agent_message(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        """Save an agent message."""
        ...

    # ── Team Config Operations ─────────────────────────────────────────

    @abstractmethod
    async def get_team_configs(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """Get all team configurations for a user."""
        ...

    @abstractmethod
    async def get_team_config(
        self, team_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Get a specific team configuration."""
        ...

    @abstractmethod
    async def save_team_config(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Save a team configuration."""
        ...
