"""MagenticAgentFactory — Creates agent instances from team JSON configs.

This factory reads an ``AgentDefinition`` from a team configuration and
instantiates the appropriate agent type (FoundryAgentTemplate, ProxyAgent,
or a reasoning variant).
"""

from __future__ import annotations

from typing import Any

import structlog

from common.models.messages import AgentDefinition, AgentType
from v1.magentic_agents.foundry_agent import FoundryAgentTemplate
from v1.magentic_agents.proxy_agent import ProxyAgent

logger = structlog.get_logger(__name__)

# Union type for all agent implementations
AgentInstance = FoundryAgentTemplate | ProxyAgent


class MagenticAgentFactory:
    """Factory that creates agent instances from declarative definitions.

    Supports:
    - ``foundry`` → FoundryAgentTemplate (Azure AI Foundry agent)
    - ``proxy`` → ProxyAgent (human-in-the-loop)
    - ``reasoning`` → FoundryAgentTemplate with o1/o3-mini model

    When ``project_client`` is *None* but ``openai_client`` is provided,
    agents fall back to Azure OpenAI + MCP tool calling instead of
    returning hardcoded simulated outputs.
    """

    def __init__(
        self,
        *,
        project_client: Any | None = None,
        proxy_agent: ProxyAgent | None = None,
        openai_client: Any | None = None,
        anthropic_client: Any | None = None,
        anthropic_model: str = "",
        mcp_server_url: str = "",
        openai_chat_deployment: str = "",
    ) -> None:
        self._project_client = project_client
        self._proxy_agent = proxy_agent or ProxyAgent()
        self._openai_client = openai_client
        self._anthropic_client = anthropic_client
        self._anthropic_model = anthropic_model
        self._mcp_server_url = mcp_server_url
        self._openai_chat_deployment = openai_chat_deployment
        # Active LLM provider: "openai" | "claude"  (auto-detected from available clients)
        if openai_client:
            self._llm_provider = "openai"
        elif anthropic_client:
            self._llm_provider = "claude"
        else:
            self._llm_provider = "simulated"

    @property
    def llm_provider(self) -> str:
        """Return the active LLM provider name."""
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value: str) -> None:
        allowed = {"openai", "claude", "simulated"}
        if value not in allowed:
            raise ValueError(f"Unknown LLM provider '{value}'. Allowed: {allowed}")
        self._llm_provider = value
        logger.info("llm_provider_changed", provider=value)

    @property
    def available_providers(self) -> list[str]:
        """Return a list of providers that have clients configured."""
        providers: list[str] = []
        if self._openai_client:
            providers.append("openai")
        if self._anthropic_client:
            providers.append("claude")
        providers.append("simulated")
        return providers

    def _effective_clients(self) -> tuple[Any | None, Any | None, str]:
        """Return (openai_client, anthropic_client, anthropic_model) based on active provider."""
        if self._llm_provider == "claude" and self._anthropic_client:
            return None, self._anthropic_client, self._anthropic_model
        if self._llm_provider == "openai" and self._openai_client:
            return self._openai_client, None, ""
        # Fallback: try whatever is available
        return self._openai_client, self._anthropic_client, self._anthropic_model

    async def create_agent(self, definition: AgentDefinition) -> AgentInstance:
        """Create an agent instance from a definition.

        The agent is created and (for Foundry agents) initialised in
        Azure AI Foundry.
        """
        logger.info(
            "creating_agent",
            name=definition.name,
            type=definition.agent_type.value,
            model=definition.model,
        )

        if definition.agent_type == AgentType.PROXY:
            return self._proxy_agent

        oai, anth, anth_model = self._effective_clients()

        if definition.agent_type == AgentType.REASONING:
            # Reasoning agents use the same FoundryAgentTemplate but with
            # o1/o3 models that have reasoning capabilities
            agent = FoundryAgentTemplate(
                definition=definition,
                project_client=self._project_client,
                openai_client=oai,
                anthropic_client=anth,
                anthropic_model=anth_model,
                mcp_server_url=self._mcp_server_url,
                openai_chat_deployment=self._openai_chat_deployment,
            )
            await agent.initialize()
            return agent

        # Default: Foundry agent
        agent = FoundryAgentTemplate(
            definition=definition,
            project_client=self._project_client,
            openai_client=oai,
            anthropic_client=anth,
            anthropic_model=anth_model,
            mcp_server_url=self._mcp_server_url,
            openai_chat_deployment=self._openai_chat_deployment,
        )
        await agent.initialize()
        return agent

    async def create_agents_from_team(
        self, definitions: list[AgentDefinition]
    ) -> dict[str, AgentInstance]:
        """Create all agents for a team and return a name→instance mapping."""
        agents: dict[str, AgentInstance] = {}
        for defn in definitions:
            try:
                agent = await self.create_agent(defn)
                agents[defn.name] = agent
            except Exception:
                logger.warning(
                    "agent_creation_failed_falling_back_to_local",
                    name=defn.name,
                    type=defn.agent_type.value,
                )
                # Fall back to local mode (no project_client) so the agent
                # still exists and can return simulated outputs.
                try:
                    agent = await self._create_local_fallback(defn)
                    agents[defn.name] = agent
                except Exception:
                    logger.exception(
                        "agent_local_fallback_failed",
                        name=defn.name,
                    )
        logger.info("team_agents_created", count=len(agents))
        return agents

    async def _create_local_fallback(
        self, definition: AgentDefinition
    ) -> AgentInstance:
        """Create an agent without Foundry — uses OpenAI + MCP if available."""
        if definition.agent_type == AgentType.PROXY:
            return self._proxy_agent

        oai, anth, anth_model = self._effective_clients()
        agent = FoundryAgentTemplate(
            definition=definition,
            project_client=None,
            openai_client=oai,
            anthropic_client=anth,
            anthropic_model=anth_model,
            mcp_server_url=self._mcp_server_url,
            openai_chat_deployment=self._openai_chat_deployment,
        )
        await agent.initialize()
        return agent

    async def cleanup_agents(
        self, agents: dict[str, AgentInstance]
    ) -> None:
        """Clean up all agent instances (delete from Azure AI Foundry)."""
        for name, agent in agents.items():
            try:
                if isinstance(agent, FoundryAgentTemplate):
                    await agent.cleanup()
            except Exception:
                logger.exception("agent_cleanup_failed", name=name)
