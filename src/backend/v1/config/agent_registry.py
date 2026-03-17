"""Global agent registry for managing active agent lifecycles."""

from __future__ import annotations

from typing import Any

import structlog

from v1.magentic_agents.magentic_agent_factory import AgentInstance

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Singleton registry tracking all active agent instances.

    Provides lookup by name, team, or plan, and handles cleanup
    when agents are no longer needed.
    """

    def __init__(self) -> None:
        # agent_name → AgentInstance
        self._agents: dict[str, AgentInstance] = {}
        # plan_id → set of agent_names
        self._plan_agents: dict[str, set[str]] = {}

    def register(
        self,
        name: str,
        agent: AgentInstance,
        plan_id: str | None = None,
    ) -> None:
        """Register an agent instance."""
        self._agents[name] = agent
        if plan_id:
            self._plan_agents.setdefault(plan_id, set()).add(name)
        logger.debug("agent_registered", name=name, plan_id=plan_id)

    def get(self, name: str) -> AgentInstance | None:
        """Get an agent by name."""
        return self._agents.get(name)

    def get_all(self) -> dict[str, AgentInstance]:
        """Get all registered agents."""
        return dict(self._agents)

    def get_by_plan(self, plan_id: str) -> dict[str, AgentInstance]:
        """Get all agents associated with a plan."""
        names = self._plan_agents.get(plan_id, set())
        return {n: self._agents[n] for n in names if n in self._agents}

    def unregister(self, name: str) -> AgentInstance | None:
        """Unregister and return an agent."""
        agent = self._agents.pop(name, None)
        for plan_agents in self._plan_agents.values():
            plan_agents.discard(name)
        if agent:
            logger.debug("agent_unregistered", name=name)
        return agent

    def unregister_plan(self, plan_id: str) -> list[AgentInstance]:
        """Unregister all agents associated with a plan."""
        names = self._plan_agents.pop(plan_id, set())
        agents = []
        for name in names:
            agent = self._agents.pop(name, None)
            if agent:
                agents.append(agent)
        logger.debug("plan_agents_unregistered", plan_id=plan_id, count=len(agents))
        return agents

    @property
    def count(self) -> int:
        return len(self._agents)
