"""DA-MACAÉ v2 — FastAPI Application Entry Point.

Multi-Agent Custom Automation Engine for Data Migration.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the backend package is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.config.app_config import get_config
from common.database.database_factory import create_database
from common.utils.utils import configure_logging
from v1.api.router import (
    configure_router,
    router as v1_router,
    send_approval_request,
    send_clarification_request,
    send_ws_message,
)
from v1.common.services.team_service import TeamService
from v1.magentic_agents.magentic_agent_factory import MagenticAgentFactory
from v1.magentic_agents.proxy_agent import ProxyAgent
from v1.orchestration.human_approval_manager import HumanApprovalManager
from v1.orchestration.orchestration_manager import OrchestrationManager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    config = get_config()
    configure_logging(config.log_level)

    logger.info(
        "starting",
        app=config.app_name,
        environment=config.environment,
    )

    # ── Initialize database ─────────────────────────────────────────
    database = await create_database(config)

    # ── Initialize OpenAI client (if configured) ────────────────────
    openai_client = None
    if config.azure_openai.endpoint and config.azure_openai.api_key:
        try:
            from openai import AsyncAzureOpenAI

            openai_client = AsyncAzureOpenAI(
                azure_endpoint=config.azure_openai.endpoint,
                api_key=config.azure_openai.api_key,
                api_version=config.azure_openai.api_version,
            )
            logger.info("openai_client_initialized")
        except Exception:
            logger.exception("openai_client_init_failed")

    # ── Initialize Azure AI Foundry agents client (if configured) ────
    project_client = None  # Actually an AgentsClient in v2 SDK
    if config.azure_ai_foundry.project_connection_string:
        try:
            from azure.ai.agents.aio import AgentsClient
            from azure.identity.aio import DefaultAzureCredential

            project_client = AgentsClient(
                endpoint=config.azure_ai_foundry.project_connection_string,
                credential=DefaultAzureCredential(),
            )
            logger.info(
                "foundry_agents_client_initialized",
                endpoint=config.azure_ai_foundry.project_connection_string,
            )
        except Exception as exc:
            logger.exception("foundry_agents_client_init_failed", error=str(exc))

    # ── Initialize Anthropic client (if configured) ─────────────────
    anthropic_client = None
    if config.anthropic.api_key:
        try:
            from anthropic import AsyncAnthropic

            anthropic_client = AsyncAnthropic(
                api_key=config.anthropic.api_key,
            )
            logger.info(
                "anthropic_client_initialized",
                model=config.anthropic.model,
            )
        except Exception:
            logger.exception("anthropic_client_init_failed")

    # ── Initialize services ─────────────────────────────────────────
    proxy_agent = ProxyAgent()
    proxy_agent.set_clarification_callback(send_clarification_request)

    approval_manager = HumanApprovalManager()
    approval_manager.set_approval_callback(send_approval_request)

    agent_factory = MagenticAgentFactory(
        project_client=project_client,
        proxy_agent=proxy_agent,
        openai_client=openai_client,
        anthropic_client=anthropic_client,
        anthropic_model=config.anthropic.model,
        mcp_server_url=config.mcp.server_url,
        openai_chat_deployment=config.azure_openai.chat_deployment,
    )

    orchestration_manager = OrchestrationManager(
        config=config,
        database=database,
        agent_factory=agent_factory,
        approval_manager=approval_manager,
        openai_client=openai_client,
        proxy_agent=proxy_agent,
    )
    orchestration_manager.set_websocket_callback(send_ws_message)

    team_service = TeamService(database)

    # ── Configure API router with dependencies ──────────────────────
    configure_router(
        orchestration_manager=orchestration_manager,
        team_service=team_service,
        database=database,
        proxy_agent=proxy_agent,
        approval_manager=approval_manager,
        agent_factory=agent_factory,
    )

    # ── Load default team configurations ────────────────────────────
    await team_service.load_default_teams()

    logger.info("startup_complete", port=config.backend_port)

    yield

    # ── Shutdown ────────────────────────────────────────────────────
    logger.info("shutting_down")
    if hasattr(database, "close"):
        await database.close()
    if project_client:
        await project_client.close()


# ── Create FastAPI App ──────────────────────────────────────────────────

app = FastAPI(
    title="DA-MACAÉ",
    description="Multi-Agent Custom Automation Engine for Data Migration",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────

config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ────────────────────────────────────────────────────

app.include_router(v1_router)


# ── Root endpoint ──────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "DA-MACAÉ",
        "version": "2.0.0",
        "description": "Multi-Agent Custom Automation Engine for Data Migration",
        "docs": "/docs",
    }


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=config.backend_port,
        reload=config.environment != "production",
    )
