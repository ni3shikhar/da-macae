"""ProxyAgent — Human-in-the-loop agent for clarification requests.

When the orchestrator needs human input (clarification, approval, etc.),
it delegates to the ProxyAgent, which sends a WebSocket message to the
user and waits for a response.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine

import structlog

from v1.magentic_agents.models.agent_models import AgentRunContext, AgentRunResult

logger = structlog.get_logger(__name__)

# Type alias for the callback that sends a WebSocket message and waits
ClarificationCallback = Callable[
    [str, str, str],  # user_id, plan_id, question
    Coroutine[Any, Any, str],  # returns the user's response
]


class ProxyAgent:
    """Human clarification agent.

    Sends a question to the user via WebSocket and waits for a response.
    Implements a configurable timeout after which a default response is used.
    """

    def __init__(
        self,
        name: str = "ProxyAgent",
        timeout_seconds: float = 300.0,
        default_response: str = "No response provided — proceeding with defaults.",
    ) -> None:
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.default_response = default_response

        # Pending clarification futures keyed by (user_id, plan_id)
        self._pending: dict[tuple[str, str], asyncio.Future[str]] = {}

        # Callback to send WebSocket messages
        self._send_clarification: ClarificationCallback | None = None

    def set_clarification_callback(self, callback: ClarificationCallback) -> None:
        """Set the callback used to send clarification requests to the UI."""
        self._send_clarification = callback

    async def run(self, context: AgentRunContext) -> AgentRunResult:
        """Request human clarification and wait for a response."""
        start = time.monotonic()
        question = context.task

        logger.info(
            "proxy_agent_requesting_clarification",
            user_id=context.user_id,
            plan_id=context.plan_id,
            question=question[:100],
        )

        if self._send_clarification is None:
            logger.warning("proxy_agent_no_callback")
            return AgentRunResult(
                agent_name=self.name,
                content=self.default_response,
                success=True,
                metadata={"source": "default_no_callback"},
                duration_seconds=time.monotonic() - start,
            )

        # Create a future for this clarification
        key = (context.user_id, context.plan_id)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[key] = future

        try:
            # Send the clarification request via WebSocket
            await self._send_clarification(
                context.user_id, context.plan_id, question
            )

            # Wait for user response with timeout
            response = await asyncio.wait_for(
                future, timeout=self.timeout_seconds
            )

            duration = time.monotonic() - start
            logger.info(
                "proxy_agent_received_response",
                user_id=context.user_id,
                plan_id=context.plan_id,
                duration=f"{duration:.2f}s",
            )

            return AgentRunResult(
                agent_name=self.name,
                content=response,
                success=True,
                metadata={"source": "human"},
                duration_seconds=duration,
            )
        except asyncio.TimeoutError:
            duration = time.monotonic() - start
            logger.warning(
                "proxy_agent_timeout",
                user_id=context.user_id,
                plan_id=context.plan_id,
                timeout=self.timeout_seconds,
            )
            return AgentRunResult(
                agent_name=self.name,
                content=self.default_response,
                success=True,
                metadata={"source": "timeout_default"},
                duration_seconds=duration,
            )
        finally:
            self._pending.pop(key, None)

    def resolve_clarification(
        self, user_id: str, plan_id: str, response: str
    ) -> bool:
        """Resolve a pending clarification with the user's response.

        Returns True if a pending clarification was found and resolved.
        """
        key = (user_id, plan_id)
        future = self._pending.get(key)
        if future and not future.done():
            future.set_result(response)
            return True
        return False
