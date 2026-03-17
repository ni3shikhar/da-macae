"""Convert a planner LLM response into an executable MPlan."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import structlog

from common.models.messages import MPlan, PlanStep, StepStatus

logger = structlog.get_logger(__name__)


def parse_planner_response(
    raw_response: str,
    plan_id: str,
    available_agents: list[str],
) -> MPlan:
    """Parse the planner LLM's response into a structured MPlan.

    The planner is expected to return JSON or a structured text format.
    This parser handles both.

    Expected JSON format:
    ```json
    {
        "task": "...",
        "steps": [
            {
                "step_number": 1,
                "agent": "DiscoveryAgent",
                "task": "Discover source schema",
                "description": "...",
                "dependencies": []
            }
        ]
    }
    ```

    Also handles numbered text format:
    ```
    1. [DiscoveryAgent] Discover source database schema
    2. [AnalysisAgent] Analyze migration complexity (depends on: 1)
    ```
    """
    # Try JSON first
    plan = _try_parse_json(raw_response, plan_id, available_agents)
    if plan:
        return plan

    # Fall back to text parsing
    plan = _try_parse_text(raw_response, plan_id, available_agents)
    if plan:
        return plan

    # Last resort: single-step plan
    logger.warning("planner_response_unparseable", response=raw_response[:200])
    return MPlan(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        task=raw_response[:200],
        steps=[
            PlanStep(
                step_number=1,
                agent=available_agents[0] if available_agents else "Unknown",
                task=raw_response,
                status=StepStatus.PENDING,
            )
        ],
    )


def _try_parse_json(
    raw: str, plan_id: str, available_agents: list[str]
) -> MPlan | None:
    """Try to parse the response as JSON."""
    # Extract JSON from markdown code blocks if present
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    json_str = json_match.group(1) if json_match else raw.strip()

    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, dict) or "steps" not in data:
        return None

    steps: list[PlanStep] = []
    for i, step_data in enumerate(data["steps"], start=1):
        agent_name = step_data.get("agent", "")
        # Validate agent name against available agents
        if agent_name not in available_agents and available_agents:
            # Try fuzzy match
            agent_name = _fuzzy_match_agent(agent_name, available_agents)

        steps.append(
            PlanStep(
                step_number=step_data.get("step_number", i),
                agent=agent_name,
                task=step_data.get("task", ""),
                description=step_data.get("description", ""),
                status=StepStatus.PENDING,
                dependencies=step_data.get("dependencies", []),
            )
        )

    return MPlan(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        task=data.get("task", ""),
        steps=steps,
    )


def _try_parse_text(
    raw: str, plan_id: str, available_agents: list[str]
) -> MPlan | None:
    """Try to parse numbered text format."""
    # Pattern: "1. [AgentName] Task description (depends on: 1, 2)"
    pattern = r"(\d+)\.\s*\[([^\]]+)\]\s*(.+?)(?:\(depends?\s*on:?\s*([\d,\s]+)\))?\s*$"
    matches = re.findall(pattern, raw, re.MULTILINE)

    if not matches:
        return None

    steps: list[PlanStep] = []
    for step_num_str, agent_name, task, deps_str in matches:
        agent_name = agent_name.strip()
        if agent_name not in available_agents and available_agents:
            agent_name = _fuzzy_match_agent(agent_name, available_agents)

        dependencies = []
        if deps_str.strip():
            dependencies = [int(d.strip()) for d in deps_str.split(",") if d.strip()]

        steps.append(
            PlanStep(
                step_number=int(step_num_str),
                agent=agent_name,
                task=task.strip(),
                status=StepStatus.PENDING,
                dependencies=dependencies,
            )
        )

    return MPlan(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        task=raw.split("\n")[0] if raw else "",
        steps=steps,
    )


def _fuzzy_match_agent(name: str, available: list[str]) -> str:
    """Best-effort match an agent name to available agents."""
    name_lower = name.lower().replace(" ", "").replace("_", "")
    for agent in available:
        if agent.lower().replace(" ", "").replace("_", "") == name_lower:
            return agent
    # Partial match
    for agent in available:
        if name_lower in agent.lower() or agent.lower() in name_lower:
            return agent
    return name  # Return original if no match
