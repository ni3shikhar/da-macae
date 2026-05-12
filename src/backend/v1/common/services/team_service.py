"""Team configuration management service.

Handles loading team configs from JSON files, CRUD operations on team
configs in the database, and team selection for users.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import structlog

from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration

logger = structlog.get_logger(__name__)


def _resolve_teams_dir() -> Path:
    """Resolve the teams directory from env var or relative to project root."""
    env_dir = os.getenv("TEAM_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    # In Docker: file is at /app/v1/common/services/team_service.py so parents[3]=/app
    # Locally: file is deeper (src/backend/v1/common/services/) so parents[5]=project root
    docker_path = Path("/app/data/agent_teams")
    if docker_path.exists():
        return docker_path
    try:
        local_path = Path(__file__).resolve().parents[5] / "data" / "agent_teams"
        if local_path.exists():
            return local_path
    except IndexError:
        pass
    return docker_path


DEFAULT_TEAMS_DIR = _resolve_teams_dir()


class TeamService:
    """Service for managing team configurations."""

    def __init__(self, database: DatabaseBase) -> None:
        self._db = database

    async def load_default_teams(
        self, teams_dir: Path | None = None
    ) -> list[TeamConfiguration]:
        """Load built-in team configs from JSON files into the database.

        Returns the list of loaded team configs.
        """
        teams_dir = teams_dir or DEFAULT_TEAMS_DIR
        loaded: list[TeamConfiguration] = []

        if not teams_dir.exists():
            logger.warning("teams_dir_not_found", path=str(teams_dir))
            return loaded

        # Team JSON files embed the docker-compose MCP hostname for local dev.
        # In Azure Container Apps the MCP server is at a different FQDN, so
        # substitute it from MCP_SERVER_URL when set.
        mcp_url_override = os.getenv("MCP_SERVER_URL")
        for json_file in teams_dir.glob("*.json"):
            try:
                content = json_file.read_text(encoding="utf-8")
                if mcp_url_override:
                    content = content.replace(
                        "http://mcp-server:8001", mcp_url_override
                    )
                data = json.loads(content)
                team = TeamConfiguration(**data)
                team.user_id = "system"  # Built-in teams are system-level

                # Check if already exists
                existing = await self._db.get_team_config(team.id, "system")
                if not existing:
                    await self._db.save_team_config(team.model_dump())
                    logger.info("team_loaded", name=team.name, id=team.id)
                loaded.append(team)
            except Exception:
                logger.exception("team_load_failed", file=str(json_file))

        return loaded

    async def get_team_configs(self, user_id: str) -> list[TeamConfiguration]:
        """Get all team configs available to a user (system + user-specific)."""
        docs = await self._db.get_team_configs(user_id)
        return [TeamConfiguration(**doc) for doc in docs]

    async def get_team_config(
        self, team_id: str, user_id: str
    ) -> TeamConfiguration | None:
        """Get a specific team config."""
        doc = await self._db.get_team_config(team_id, user_id)
        return TeamConfiguration(**doc) if doc else None

    async def save_team_config(
        self, config: TeamConfiguration
    ) -> TeamConfiguration:
        """Save or update a team config."""
        doc = config.model_dump()
        await self._db.save_team_config(doc)
        return config

    async def delete_team_config(
        self, team_id: str, user_id: str
    ) -> bool:
        """Delete a team config. Returns True if deleted."""
        try:
            await self._db.delete_document(team_id, partition_key=user_id)
            return True
        except Exception:
            logger.exception("team_delete_failed", team_id=team_id)
            return False

    async def select_team_for_user(
        self, user_id: str, team_id: str
    ) -> bool:
        """Set the active team for a user session."""
        doc = {
            "id": f"current_team_{user_id}",
            "user_id": user_id,
            "team_id": team_id,
            "doc_type": "user_current_team",
        }
        await self._db.upsert_document(doc, partition_key=user_id)
        return True

    async def get_current_team(self, user_id: str) -> str | None:
        """Get the current active team ID for a user."""
        doc = await self._db.read_document(
            f"current_team_{user_id}", partition_key=user_id
        )
        return doc.get("team_id") if doc else None
