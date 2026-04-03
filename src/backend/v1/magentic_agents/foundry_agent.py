"""FoundryAgentTemplate — AI agent backed by Azure AI Foundry.

Each FoundryAgent wraps an Azure AI Foundry assistant with optional
MCP tools, Azure AI Search RAG, Code Interpreter, and Bing grounding.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from common.models.messages import AgentDefinition, AgentType
from v1.magentic_agents.common.lifecycle import AzureAgentBase
from v1.magentic_agents.models.agent_models import (
    AgentCapabilities,
    AgentRunContext,
    AgentRunResult,
)

logger = structlog.get_logger(__name__)


class FoundryAgentTemplate:
    """Template for creating Azure AI Foundry-backed agents.

    Given an ``AgentDefinition`` from a team JSON config, this class:
    1. Resolves capabilities (MCP, RAG, code-interpreter, etc.)
    2. Creates the underlying Azure agent via ``AzureAgentBase``
    3. Provides a ``run()`` method that executes a task and returns results
    """

    def __init__(
        self,
        definition: AgentDefinition,
        *,
        project_client: Any | None = None,
        openai_client: Any | None = None,
        anthropic_client: Any | None = None,
        anthropic_model: str = "",
        mcp_server_url: str = "",
        openai_chat_deployment: str = "",
    ) -> None:
        self.definition = definition
        self.name = definition.name
        self.capabilities = self._resolve_capabilities(definition)

        # Collect MCP tool names from the agent definition
        mcp_tool_names: list[str] = []
        resolved_mcp_url = mcp_server_url
        for mcp_cfg in definition.mcp_tools:
            mcp_tool_names.extend(mcp_cfg.tool_names)
            if not resolved_mcp_url and mcp_cfg.server_url:
                resolved_mcp_url = mcp_cfg.server_url

        # When using OpenAI directly (no Foundry), use the actual deployment name
        effective_model = definition.model
        if not project_client and openai_client and openai_chat_deployment:
            effective_model = openai_chat_deployment

        self._base = AzureAgentBase(
            name=definition.name,
            model=effective_model,
            instructions=definition.system_prompt,
            project_client=project_client,
            openai_client=openai_client,
            anthropic_client=anthropic_client,
            anthropic_model=anthropic_model,
            mcp_server_url=resolved_mcp_url,
            mcp_tool_names=mcp_tool_names,
        )
        self._project_client = project_client

    @staticmethod
    def _resolve_capabilities(defn: AgentDefinition) -> AgentCapabilities:
        return AgentCapabilities(
            has_mcp=len(defn.mcp_tools) > 0,
            has_search=len(defn.search_tools) > 0,
            has_code_interpreter=defn.code_interpreter,
            has_bing_search=defn.bing_search,
            is_reasoning=defn.model in ("o1", "o1-mini", "o3-mini"),
            is_proxy=defn.agent_type == AgentType.PROXY,
        )

    async def initialize(self) -> str:
        """Create the agent in Azure AI Foundry.

        Returns the agent ID.
        """
        tools = self._build_tools()
        tool_resources = self._build_tool_resources()

        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = tools
        if tool_resources:
            kwargs["tool_resources"] = tool_resources

        return await self._base.create(**kwargs)

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build the tools list for the Azure AI Foundry agent."""
        tools: list[dict[str, Any]] = []

        if self.capabilities.has_code_interpreter:
            tools.append({"type": "code_interpreter"})

        if self.capabilities.has_search:
            for search_cfg in self.definition.search_tools:
                tools.append(
                    {
                        "type": "azure_ai_search",
                        "azure_ai_search": {
                            "index_name": search_cfg.index_name,
                        },
                    }
                )

        if self.capabilities.has_bing_search:
            tools.append({"type": "bing_grounding"})

        # MCP tools are registered separately via the MCP server connection
        return tools

    def _build_tool_resources(self) -> dict[str, Any]:
        """Build tool resources for the agent."""
        resources: dict[str, Any] = {}
        # Additional resource configuration can be added here
        return resources

    async def run(
        self,
        context: AgentRunContext,
        *,
        on_progress: Any | None = None,
    ) -> AgentRunResult:
        """Execute a task using this agent.

        Args:
            context: The execution context with task, plan info, and prior outputs.
            on_progress: Optional callback for live tool-call progress.

        Returns:
            AgentRunResult with the agent's response.
        """
        start = time.monotonic()

        # Build the full prompt with context
        prompt = self._build_prompt(context)

        try:
            response = await self._base.run(
                task=prompt, thread_id=context.thread_id,
                on_progress=on_progress,
                subtask_label=context.subtask_label,
            )
            duration = time.monotonic() - start

            # Unpack dict response: {"text": str, "usage": {...}}
            if isinstance(response, dict):
                text = response.get("text", "")
                usage = response.get("usage", {})
            else:
                text = str(response)
                usage = {}

            logger.info(
                "agent_run_complete",
                agent=self.name,
                plan_id=context.plan_id,
                step_id=context.step_id,
                duration=f"{duration:.2f}s",
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                llm_calls=usage.get("llm_calls", 0),
            )

            return AgentRunResult(
                agent_name=self.name,
                content=text,
                success=True,
                duration_seconds=duration,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                llm_calls=usage.get("llm_calls", 0),
            )
        except Exception as exc:
            duration = time.monotonic() - start
            logger.exception(
                "agent_run_failed",
                agent=self.name,
                plan_id=context.plan_id,
            )
            return AgentRunResult(
                agent_name=self.name,
                content="",
                success=False,
                error=str(exc),
                duration_seconds=duration,
            )

    def _build_prompt(self, context: AgentRunContext) -> str:
        """Build the full prompt.

        Note: previous_outputs are already injected into context.task
        by the orchestration manager, so we do NOT append them again
        here to avoid doubling token usage.
        """
        return context.task

    async def cleanup(self) -> None:
        """Delete the agent from Azure AI Foundry."""
        await self._base.delete()
