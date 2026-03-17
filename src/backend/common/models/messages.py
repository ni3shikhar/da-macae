"""Core data models shared across the application.

All Cosmos DB documents and API request/response models are defined here.
Uses Pydantic v2 for validation and serialisation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────


class AgentType(str, Enum):
    """Types of agents available in the system."""

    FOUNDRY = "foundry"
    PROXY = "proxy"
    REASONING = "reasoning"
    RAI = "rai"


class PlanStatus(str, Enum):
    """Lifecycle status of a plan."""

    CREATED = "created"
    PLANNING = "planning"
    CLARIFYING = "clarifying"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Lifecycle status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WebSocketMessageType(str, Enum):
    """Types of WebSocket messages."""

    PLAN_UPDATE = "plan_update"
    AGENT_RESPONSE = "agent_response"
    STREAMING_CONTENT = "streaming_content"
    HUMAN_CLARIFICATION_REQUEST = "human_clarification_request"
    PLAN_COMPLETE = "plan_complete"
    ERROR = "error"
    USER_CLARIFICATION_RESPONSE = "user_clarification_response"
    PLAN_APPROVAL = "plan_approval"
    STEP_STATUS = "step_status"
    TOOL_PROGRESS = "tool_progress"
    AGENT_SUBTASKS = "agent_subtasks"
    SUBTASK_UPDATE = "subtask_update"
    STEP_APPROVAL_REQUEST = "step_approval_request"
    SUBTASK_INPUT_REQUEST = "subtask_input_request"


# ── Agent Configuration Models ─────────────────────────────────────────


class MCPToolConfig(BaseModel):
    """Configuration for an MCP tool attached to an agent."""

    server_url: str
    tool_names: list[str] = Field(default_factory=list)


class SearchToolConfig(BaseModel):
    """Configuration for Azure AI Search tool attached to an agent."""

    index_name: str
    description: str = ""


class AgentDefinition(BaseModel):
    """Definition of an agent within a team configuration.

    This is the JSON-serializable descriptor used in team configs.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    agent_type: AgentType = AgentType.FOUNDRY
    model: str = "gpt-4o"
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    mcp_tools: list[MCPToolConfig] = Field(default_factory=list)
    search_tools: list[SearchToolConfig] = Field(default_factory=list)
    code_interpreter: bool = False
    bing_search: bool = False


class StartingTask(BaseModel):
    """A pre-defined task that appears in the team UI."""

    title: str
    description: str = ""
    prompt: str


class TeamConfiguration(BaseModel):
    """A complete team configuration defining agents and their tasks."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "system"
    name: str
    description: str = ""
    agents: list[AgentDefinition] = Field(default_factory=list)
    starting_tasks: list[StartingTask] = Field(default_factory=list)
    planner_system_prompt: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Connection / Pipeline Configuration Models ─────────────────────────


class AzureServiceType(str, Enum):
    """Target Azure data service for pipeline generation."""

    ADF = "adf"
    SYNAPSE = "synapse"
    FABRIC = "fabric"


class ConnectionConfig(BaseModel):
    """Configuration for a data-source connection used in pipeline generation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str  # sql_server, postgresql, cosmosdb, …
    azure_service: AzureServiceType = AzureServiceType.ADF
    connection_name: str = ""
    connection_params: dict[str, str] = Field(default_factory=dict)
    linked_service_json: Optional[str] = None  # Generated output
    deployed: bool = False
    status: str = "pending"  # pending | generated | deployed | error
    error: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PipelineConfig(BaseModel):
    """Configuration for a generated migration pipeline."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_name: str = ""
    azure_service: AzureServiceType = AzureServiceType.ADF
    source_connection_id: str = ""
    target_connection_id: str = ""
    tables: list[str] = Field(default_factory=list)
    pipeline_json: Optional[str] = None  # Generated output
    deployed: bool = False
    status: str = "pending"


# ── Plan & Step Models ─────────────────────────────────────────────────


class PlanStep(BaseModel):
    """A single step in a migration execution plan."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    agent: str
    task: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    dependencies: list[int] = Field(default_factory=list)


class MPlan(BaseModel):
    """Magentic Plan — the executable plan with ordered steps."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    task: str
    steps: list[PlanStep] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.CREATED
    summary: str = ""


class Plan(BaseModel):
    """Top-level plan document stored in Cosmos DB."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    initial_goal: str
    overall_status: PlanStatus = PlanStatus.CREATED
    m_plan: Optional[MPlan] = None
    team_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Agent Message Models ───────────────────────────────────────────────


class AgentMessage(BaseModel):
    """A message produced by an agent during plan execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    step_id: str = ""
    agent: str
    agent_type: AgentType = AgentType.FOUNDRY
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Session Models ─────────────────────────────────────────────────────


class Session(BaseModel):
    """User session document."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    current_team_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── WebSocket Models ──────────────────────────────────────────────────


class WebSocketMessage(BaseModel):
    """WebSocket message envelope."""

    type: WebSocketMessageType
    data: dict[str, Any] = Field(default_factory=dict)


# ── API Request / Response Models ──────────────────────────────────────


class ProcessRequestInput(BaseModel):
    """Input for the /process_request endpoint."""

    user_id: str
    message: str
    team_id: str = ""


class PlanApprovalInput(BaseModel):
    """Input for the /plan_approval endpoint."""

    plan_id: str
    user_id: str
    approved: bool
    feedback: str = ""


class StepApprovalInput(BaseModel):
    """Input for the /step_approval endpoint."""

    plan_id: str
    user_id: str
    step_number: int
    approved: bool
    feedback: str = ""


class SubtaskResponseInput(BaseModel):
    """Input for the /subtask_response endpoint.

    After each sub-task completes, the user can provide an answer
    or signal to continue/skip.
    """

    plan_id: str
    user_id: str
    step_number: int
    subtask_id: str
    action: str = "continue"  # "continue", "skip", or "answer"
    answer: str = ""


class UserClarificationInput(BaseModel):
    """Input for the /user_clarification endpoint."""

    plan_id: str
    user_id: str
    response: str


class CancelPlanInput(BaseModel):
    """Input for the /cancel_plan endpoint."""

    plan_id: str
    user_id: str
    reason: str = ""


class SelectTeamInput(BaseModel):
    """Input for the /select_team endpoint."""

    user_id: str
    team_id: str
