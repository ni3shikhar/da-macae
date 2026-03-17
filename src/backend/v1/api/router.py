"""FastAPI API router — all REST and WebSocket endpoints.

Endpoints follow the MACAE pattern:
- POST /api/v1/process_request  — Submit a new migration task
- GET  /api/v1/plans            — List plans for a user
- GET  /api/v1/plan             — Get a specific plan
- POST /api/v1/plan_approval    — Approve or reject a plan
- POST /api/v1/cancel_plan      — Cancel a running or pending plan
- POST /api/v1/user_clarification — Respond to a ProxyAgent question
- GET  /api/v1/team_configs     — List available team configurations
- GET  /api/v1/team_config      — Get a specific team configuration
- POST /api/v1/select_team      — Set active team for a user
- POST /api/v1/init_team        — Create/save a team configuration
- GET  /api/v1/agent_messages   — Get messages for a plan
- GET  /api/v1/blob/{c}/{path}  — Download a blob from storage
- WS   /ws/{user_id}            — WebSocket for real-time streaming
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from common.models.messages import (
    AgentMessage,
    AgentType,
    CancelPlanInput,
    PlanApprovalInput,
    ProcessRequestInput,
    SelectTeamInput,
    StepApprovalInput,
    SubtaskResponseInput,
    TeamConfiguration,
    UserClarificationInput,
    WebSocketMessage,
    WebSocketMessageType,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1"])

# ── Module-level references (set by app.py during startup) ──────────

_orchestration_manager = None
_team_service = None
_database = None
_proxy_agent = None
_approval_manager = None
_agent_factory = None
_ws_connections: dict[str, WebSocket] = {}


def configure_router(
    *,
    orchestration_manager: Any,
    team_service: Any,
    database: Any,
    proxy_agent: Any,
    approval_manager: Any,
    agent_factory: Any = None,
) -> None:
    """Inject dependencies into the router module."""
    global _orchestration_manager, _team_service, _database
    global _proxy_agent, _approval_manager, _agent_factory
    _orchestration_manager = orchestration_manager
    _team_service = team_service
    _database = database
    _proxy_agent = proxy_agent
    _approval_manager = approval_manager
    _agent_factory = agent_factory


# ── WebSocket Helpers ──────────────────────────────────────────────────


async def send_ws_message(user_id: str, message: WebSocketMessage) -> None:
    """Send a WebSocket message to a connected user."""
    ws = _ws_connections.get(user_id)
    if ws:
        try:
            await ws.send_json(message.model_dump())
        except Exception:
            logger.exception("ws_send_error", user_id=user_id)
            _ws_connections.pop(user_id, None)


async def send_clarification_request(
    user_id: str, plan_id: str, question: str
) -> str:
    """Send a clarification request via WebSocket (used by ProxyAgent)."""
    await send_ws_message(
        user_id,
        WebSocketMessage(
            type=WebSocketMessageType.HUMAN_CLARIFICATION_REQUEST,
            data={"plan_id": plan_id, "question": question},
        ),
    )
    # The actual response comes via /user_clarification endpoint
    # which resolves the ProxyAgent's future
    return ""


async def send_approval_request(user_id: str, plan: Any) -> None:
    """Send plan approval request via WebSocket (used by HumanApprovalManager)."""
    await send_ws_message(
        user_id,
        WebSocketMessage(
            type=WebSocketMessageType.PLAN_APPROVAL,
            data={"plan_id": plan.plan_id, "plan": plan.model_dump()},
        ),
    )


# ── REST Endpoints ─────────────────────────────────────────────────────


@router.post("/process_request")
async def process_request(body: ProcessRequestInput) -> JSONResponse:
    """Submit a new migration task for processing."""
    if not _orchestration_manager or not _team_service:
        return JSONResponse(
            status_code=503, content={"error": "Service not initialized"}
        )

    # Get user's active team config
    team_id = body.team_id
    if not team_id:
        team_id = await _team_service.get_current_team(body.user_id)
    if not team_id:
        return JSONResponse(
            status_code=400, content={"error": "No team selected"}
        )

    team_config = await _team_service.get_team_config(team_id, body.user_id)
    if not team_config:
        return JSONResponse(
            status_code=404, content={"error": f"Team '{team_id}' not found"}
        )

    # Process asynchronously (task self-registers in orchestration manager)
    asyncio.create_task(
        _orchestration_manager.process_request(
            user_id=body.user_id,
            message=body.message,
            team_config=team_config,
        )
    )

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "message": "Processing started"},
    )


@router.get("/plans")
async def get_plans(user_id: str) -> JSONResponse:
    """List all plans for a user."""
    if not _database:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    plans = await _database.get_plans_by_user(user_id)
    return JSONResponse(content=plans)


@router.get("/plan")
async def get_plan(plan_id: str, user_id: str) -> JSONResponse:
    """Get a specific plan by ID."""
    if not _database:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    plan = await _database.get_plan(plan_id, user_id)
    if not plan:
        return JSONResponse(status_code=404, content={"error": "Plan not found"})
    return JSONResponse(content=plan)


@router.post("/plan_approval")
async def plan_approval(body: PlanApprovalInput) -> JSONResponse:
    """Approve or reject a plan."""
    if not _approval_manager:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})

    resolved = _approval_manager.resolve_approval(
        user_id=body.user_id,
        plan_id=body.plan_id,
        approved=body.approved,
        feedback=body.feedback,
    )
    if not resolved:
        return JSONResponse(
            status_code=404,
            content={"error": "No pending approval found for this plan"},
        )
    return JSONResponse(content={"status": "ok"})


@router.post("/cancel_plan")
async def cancel_plan(body: CancelPlanInput) -> JSONResponse:
    """Cancel a running or pending plan."""
    if not _orchestration_manager:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})

    cancelled = await _orchestration_manager.cancel_plan(
        plan_id=body.plan_id,
        user_id=body.user_id,
        reason=body.reason,
    )
    if not cancelled:
        return JSONResponse(
            status_code=404,
            content={"error": "Plan not found or already finished"},
        )
    return JSONResponse(content={"status": "cancelled", "plan_id": body.plan_id})


@router.post("/step_approval")
async def step_approval(body: StepApprovalInput) -> JSONResponse:
    """Approve or reject a specific step (agent) after sub-task review."""
    if not _approval_manager:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})

    resolved = _approval_manager.resolve_step_approval(
        user_id=body.user_id,
        plan_id=body.plan_id,
        step_number=body.step_number,
        approved=body.approved,
        feedback=body.feedback,
    )
    if not resolved:
        return JSONResponse(
            status_code=404,
            content={"error": "No pending step approval found"},
        )
    return JSONResponse(content={"status": "ok"})


@router.post("/subtask_response")
async def subtask_response(body: SubtaskResponseInput) -> JSONResponse:
    """Provide input for a completed sub-task (continue / skip / answer)."""
    if not _approval_manager:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})

    resolved = _approval_manager.resolve_subtask_input(
        user_id=body.user_id,
        plan_id=body.plan_id,
        step_number=body.step_number,
        subtask_id=body.subtask_id,
        action=body.action,
        answer=body.answer,
    )
    if not resolved:
        return JSONResponse(
            status_code=404,
            content={"error": "No pending sub-task input found"},
        )
    return JSONResponse(content={"status": "ok"})


@router.post("/user_clarification")
async def user_clarification(body: UserClarificationInput) -> JSONResponse:
    """Respond to a ProxyAgent clarification request."""
    if not _proxy_agent:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})

    resolved = _proxy_agent.resolve_clarification(
        user_id=body.user_id,
        plan_id=body.plan_id,
        response=body.response,
    )
    if not resolved:
        return JSONResponse(
            status_code=404,
            content={"error": "No pending clarification found"},
        )

    # Persist the user's answer so the frontend chat history is complete
    if _database:
        try:
            await _database.save_agent_message(
                AgentMessage(
                    plan_id=body.plan_id,
                    step_id="user-clarification",
                    agent="user",
                    agent_type=AgentType.PROXY,
                    content=body.response,
                ).model_dump()
            )
        except Exception:
            logger.exception("save_user_clarification_message_failed")

    return JSONResponse(content={"status": "ok"})


@router.post("/user_message")
async def user_message(body: UserClarificationInput) -> JSONResponse:
    """Save a user message to the plan's chat history.

    Unlike /user_clarification this always succeeds: it persists the
    message and, if a ProxyAgent clarification is pending, resolves it
    as a side-effect.
    """
    # Try to resolve a pending ProxyAgent clarification (best-effort)
    if _proxy_agent:
        _proxy_agent.resolve_clarification(
            user_id=body.user_id,
            plan_id=body.plan_id,
            response=body.response,
        )

    # Always persist the user message
    if _database:
        try:
            await _database.save_agent_message(
                AgentMessage(
                    plan_id=body.plan_id,
                    step_id="user-message",
                    agent="user",
                    agent_type=AgentType.PROXY,
                    content=body.response,
                ).model_dump()
            )
        except Exception:
            logger.exception("save_user_message_failed")

    # Echo back via WebSocket so the sender sees it immediately
    try:
        await send_ws_message(
            body.user_id,
            WebSocketMessage(
                type=WebSocketMessageType.AGENT_RESPONSE,
                data={
                    "plan_id": body.plan_id,
                    "agent": "user",
                    "content": body.response,
                },
            ),
        )
    except Exception:
        pass  # non-critical

    return JSONResponse(content={"status": "ok"})


@router.get("/team_configs")
async def get_team_configs(user_id: str) -> JSONResponse:
    """List available team configurations."""
    if not _team_service:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    configs = await _team_service.get_team_configs(user_id)
    return JSONResponse(content=[c.model_dump() for c in configs])


@router.get("/team_config")
async def get_team_config(team_id: str, user_id: str) -> JSONResponse:
    """Get a specific team configuration."""
    if not _team_service:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    config = await _team_service.get_team_config(team_id, user_id)
    if not config:
        return JSONResponse(status_code=404, content={"error": "Team not found"})
    return JSONResponse(content=config.model_dump())


@router.post("/select_team")
async def select_team(body: SelectTeamInput) -> JSONResponse:
    """Set the active team for a user."""
    if not _team_service:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    await _team_service.select_team_for_user(body.user_id, body.team_id)
    return JSONResponse(content={"status": "ok"})


@router.post("/init_team")
async def init_team(config: TeamConfiguration) -> JSONResponse:
    """Create or update a team configuration."""
    if not _team_service:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    saved = await _team_service.save_team_config(config)
    return JSONResponse(content=saved.model_dump())


@router.get("/agent_messages")
async def get_agent_messages(plan_id: str) -> JSONResponse:
    """Get all agent messages for a plan."""
    if not _database:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    messages = await _database.get_messages_by_plan(plan_id)
    return JSONResponse(content=messages)


# ── LLM Provider ───────────────────────────────────────────────────────


@router.get("/llm_provider")
async def get_llm_provider() -> JSONResponse:
    """Return the active LLM provider and available providers."""
    if not _agent_factory:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    return JSONResponse(content={
        "active": _agent_factory.llm_provider,
        "available": _agent_factory.available_providers,
    })


@router.post("/llm_provider")
async def set_llm_provider(body: dict) -> JSONResponse:
    """Switch the active LLM provider (openai | claude | simulated)."""
    if not _agent_factory:
        return JSONResponse(status_code=503, content={"error": "Not initialized"})
    provider = body.get("provider", "")
    try:
        _agent_factory.llm_provider = provider
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    return JSONResponse(content={
        "status": "ok",
        "active": _agent_factory.llm_provider,
    })


# ── Blob Download ──────────────────────────────────────────────────────


@router.get("/blob/{container}/{blob_path:path}")
async def download_blob(container: str, blob_path: str) -> StreamingResponse:
    """Download a blob from Azure Storage / Azurite.

    Returns the blob content as a streaming download so the browser
    triggers a file-save dialog.
    """
    from azure.storage.blob.aio import BlobServiceClient

    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    if not conn_str:
        return JSONResponse(status_code=500, content={"error": "Storage not configured"})

    try:
        async with BlobServiceClient.from_connection_string(conn_str) as bsc:
            blob_client = bsc.get_blob_client(container=container, blob=blob_path)
            download = await blob_client.download_blob()
            props = download.properties

            content_type = (props.content_settings.content_type
                           if props.content_settings and props.content_settings.content_type
                           else "application/octet-stream")
            file_name = blob_path.rsplit("/", 1)[-1] if "/" in blob_path else blob_path

            async def _stream():
                async for chunk in download.chunks():
                    yield chunk

            return StreamingResponse(
                _stream(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{file_name}"',
                    "Content-Length": str(props.size),
                },
            )
    except Exception as exc:
        logger.error("blob_download_failed", container=container, blob=blob_path, error=str(exc))
        return JSONResponse(status_code=404, content={"error": f"Blob not found: {exc}"})


# ── Health Check ───────────────────────────────────────────────────────


@router.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy", "service": "da-macae-backend"})


# ── WebSocket Endpoint ────────────────────────────────────────────────


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    """WebSocket endpoint for real-time streaming."""
    await websocket.accept()
    _ws_connections[user_id] = websocket
    logger.info("ws_connected", user_id=user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == WebSocketMessageType.USER_CLARIFICATION_RESPONSE.value:
                    if _proxy_agent:
                        _proxy_agent.resolve_clarification(
                            user_id=user_id,
                            plan_id=msg.get("data", {}).get("plan_id", ""),
                            response=msg.get("data", {}).get("response", ""),
                        )
                elif msg_type == WebSocketMessageType.PLAN_APPROVAL.value:
                    if _approval_manager:
                        _approval_manager.resolve_approval(
                            user_id=user_id,
                            plan_id=msg.get("data", {}).get("plan_id", ""),
                            approved=msg.get("data", {}).get("approved", False),
                            feedback=msg.get("data", {}).get("feedback", ""),
                        )
                else:
                    logger.debug("ws_unknown_message", type=msg_type)

            except json.JSONDecodeError:
                logger.warning("ws_invalid_json", user_id=user_id)

    except WebSocketDisconnect:
        logger.info("ws_disconnected", user_id=user_id)
    finally:
        _ws_connections.pop(user_id, None)
