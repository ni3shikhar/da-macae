"""Agent-specific models for the magentic agent layer."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentCapabilities(BaseModel):
    """Runtime capabilities resolved for an agent instance."""

    has_mcp: bool = False
    has_search: bool = False
    has_code_interpreter: bool = False
    has_bing_search: bool = False
    is_reasoning: bool = False
    is_proxy: bool = False


class AgentRunContext(BaseModel):
    """Context passed to an agent during execution."""

    plan_id: str
    step_id: str
    user_id: str
    task: str
    previous_outputs: dict[str, str] = Field(default_factory=dict)
    thread_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    subtask_label: Optional[str] = None


class AgentRunResult(BaseModel):
    """Result returned from an agent execution."""

    agent_name: str
    content: str
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
