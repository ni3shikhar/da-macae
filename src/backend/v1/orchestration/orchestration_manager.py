"""OrchestrationManager — Core workflow engine.

Implements the full Plan → Approve → Execute cycle:
1. Receive user request
2. RAI validation
3. Generate plan via planner LLM
4. Human approval gate
5. Execute plan steps via magentic agents
6. Stream results via WebSocket
7. Synthesise final output
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import structlog

from common.config.app_config import AppConfig
from common.database.database_base import DatabaseBase
from common.models.messages import (
    AgentMessage,
    AgentType,
    MPlan,
    Plan,
    PlanStatus,
    PlanStep,
    StepStatus,
    TeamConfiguration,
    WebSocketMessage,
    WebSocketMessageType,
)
from common.utils.utils import validate_rai
from v1.magentic_agents.foundry_agent import FoundryAgentTemplate
from v1.magentic_agents.magentic_agent_factory import AgentInstance, MagenticAgentFactory
from v1.magentic_agents.models.agent_models import AgentRunContext
from v1.magentic_agents.proxy_agent import ProxyAgent
from v1.orchestration.helper.plan_to_mplan_converter import parse_planner_response
from v1.orchestration.human_approval_manager import HumanApprovalManager

logger = structlog.get_logger(__name__)

# Callback to send WebSocket messages
SendWSCallback = Callable[
    [str, WebSocketMessage],  # user_id, message
    Coroutine[Any, Any, None],
]


class OrchestrationManager:
    """Manages the full lifecycle of a migration plan.

    Coordinates:
    - Planner LLM to generate execution plans
    - Human approval for plan review
    - Agent factory to create agent instances
    - Step-by-step execution with dependency resolution
    - Real-time streaming via WebSocket
    - Result persistence to database
    """

    def __init__(
        self,
        config: AppConfig,
        database: DatabaseBase,
        agent_factory: MagenticAgentFactory,
        approval_manager: HumanApprovalManager,
        *,
        openai_client: Any | None = None,
        proxy_agent: ProxyAgent | None = None,
    ) -> None:
        self._config = config
        self._db = database
        self._factory = agent_factory
        self._approval_manager = approval_manager
        self._openai_client = openai_client
        self._proxy_agent = proxy_agent
        self._send_ws: SendWSCallback | None = None

        # Active agent instances keyed by plan_id
        self._active_agents: dict[str, dict[str, AgentInstance]] = {}

        # Cancellation tracking
        self._cancelled_plans: set[str] = set()
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}

    # ── Cancellation ───────────────────────────────────────────────────

    def _is_cancelled(self, plan_id: str) -> bool:
        """Check if a plan has been cancelled."""
        return plan_id in self._cancelled_plans

    async def cancel_plan(self, plan_id: str, user_id: str, reason: str = "") -> bool:
        """Cancel a running plan.

        - Sets plan status to CANCELLED in the database.
        - Resolves all pending approval / input gates so blocked awaits unblock.
        - Cancels the asyncio task if still running.
        - Cleans up active agents.

        Returns True if the plan was found and cancellation initiated.
        """
        logger.info(
            "cancel_plan_requested",
            plan_id=plan_id,
            user_id=user_id,
            reason=reason,
        )

        # Mark cancelled (the _execute_plan loop checks this)
        self._cancelled_plans.add(plan_id)

        # Update database
        plan_doc = await self._db.get_plan(plan_id, user_id)
        if plan_doc:
            plan = Plan(**plan_doc)
            plan.overall_status = PlanStatus.CANCELLED
            # Mark any in-progress steps as cancelled
            if plan.m_plan and plan.m_plan.steps:
                for step in plan.m_plan.steps:
                    if step.status == StepStatus.IN_PROGRESS:
                        step.status = StepStatus.FAILED
                        step.error = reason or "Cancelled by user"
                        step.completed_at = datetime.now(timezone.utc).isoformat()
            await self._save_plan(plan)
        else:
            logger.warning("cancel_plan_not_found", plan_id=plan_id)
            return False

        # Resolve any pending approval / input gates
        self._approval_manager.cancel_pending_for_plan(user_id, plan_id)

        # Cancel the asyncio task
        task = self._running_tasks.pop(plan_id, None)
        if task and not task.done():
            task.cancel()
            logger.info("cancel_plan_task_cancelled", plan_id=plan_id)

        # Cleanup active agents
        agents = self._active_agents.pop(plan_id, None)
        if agents:
            try:
                await self._factory.cleanup_agents(agents)
            except Exception:
                logger.exception("cancel_plan_cleanup_error", plan_id=plan_id)

        # Notify frontend
        await self._notify_ws(
            user_id,
            WebSocketMessageType.PLAN_UPDATE,
            plan.model_dump(),
        )
        await self._notify_ws(
            user_id,
            WebSocketMessageType.PLAN_COMPLETE,
            {
                "plan_id": plan_id,
                "summary": reason or "Plan cancelled by user",
                "cancelled": True,
            },
        )

        logger.info("cancel_plan_completed", plan_id=plan_id)
        return True

    # ── LLM Chat Completion Dispatcher ─────────────────────────────────

    async def _llm_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        timeout: int = 90,
    ) -> str | None:
        """Route a chat completion to the active LLM provider.

        Returns the assistant's text response, or None if no client is
        available (caller should fall back to heuristics/defaults).

        ``messages`` uses the OpenAI format (list of role/content dicts).
        When dispatching to Claude the system message is extracted and
        passed via the ``system`` kwarg.
        """
        provider = self._factory.llm_provider

        # ── Claude ──────────────────────────────────────────────────
        if provider == "claude" and self._factory._anthropic_client:
            # Separate system message from user/assistant messages
            system_text = ""
            claude_messages: list[dict[str, str]] = []
            for msg in messages:
                if msg["role"] == "system":
                    system_text = msg["content"]
                else:
                    claude_messages.append(msg)
            # Claude requires at least one user message
            if not claude_messages:
                claude_messages = [{"role": "user", "content": system_text}]
                system_text = ""

            response = await self._factory._anthropic_client.messages.create(
                model=self._factory._anthropic_model,
                system=system_text,
                messages=claude_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.content[0].text

        # ── OpenAI ──────────────────────────────────────────────────
        if self._openai_client:
            response = await self._openai_client.chat.completions.create(
                model=self._config.azure_openai.chat_deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content

        # No usable client
        return None

    def set_websocket_callback(self, callback: SendWSCallback) -> None:
        """Set the callback for sending WebSocket messages to users."""
        self._send_ws = callback

    # ── Main Entry Point ───────────────────────────────────────────────

    async def process_request(
        self,
        user_id: str,
        message: str,
        team_config: TeamConfiguration,
    ) -> Plan:
        """Process a user request through the full orchestration pipeline.

        Steps:
        1. RAI validation
        2. Create plan document
        3. Generate plan via planner LLM
        4. Human approval
        5. Execute plan
        6. Return completed plan
        """
        plan_id = str(uuid.uuid4())

        # 1. RAI Validation
        if self._config.rai_enabled:
            is_safe = await validate_rai(
                message,
                openai_client=self._openai_client,
                model=self._config.azure_openai.chat_deployment,
            )
            if not is_safe:
                return await self._create_failed_plan(
                    plan_id, user_id, message, "Content blocked by safety filter"
                )

        # 2. Create initial plan
        plan = Plan(
            plan_id=plan_id,
            user_id=user_id,
            initial_goal=message,
            overall_status=PlanStatus.PLANNING,
            team_id=team_config.id,
        )
        await self._save_plan(plan)
        await self._notify_ws(user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump())

        # Register current task for cancellation support
        try:
            current_task = asyncio.current_task()
            if current_task:
                self._running_tasks[plan_id] = current_task
        except RuntimeError:
            pass

        # 2b. Pre-plan clarification — ask user for details if goal is vague
        clarification_context = ""
        try:
            clarification_context = await self._pre_plan_clarification(
                user_id, plan_id, message, team_config, plan
            )
        except Exception as exc:
            logger.warning(
                "pre_plan_clarification_failed",
                plan_id=plan_id,
                error=str(exc),
            )
            # Non-fatal — proceed without clarification

        # Build the enriched goal with any clarification answers
        enriched_goal = message
        if clarification_context:
            enriched_goal = (
                f"{message}\n\n## User Clarification\n{clarification_context}"
            )

        # 3. Generate plan via planner LLM
        try:
            m_plan = await self._generate_plan(
                enriched_goal, team_config, plan_id
            )
            plan.m_plan = m_plan
            plan.overall_status = PlanStatus.AWAITING_APPROVAL
            await self._save_plan(plan)
            await self._notify_ws(user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump())
        except Exception as exc:
            logger.exception("plan_generation_failed", plan_id=plan_id)
            return await self._create_failed_plan(
                plan_id, user_id, message, f"Plan generation failed: {exc}"
            )

        # 4. Human approval
        approved, feedback = await self._approval_manager.request_approval(
            user_id, plan
        )
        if not approved:
            # Could be a cancel or a rejection
            if self._is_cancelled(plan_id):
                logger.info("plan_cancelled_during_approval", plan_id=plan_id)
                self._cancelled_plans.discard(plan_id)
                self._running_tasks.pop(plan_id, None)
                return plan
            plan.overall_status = PlanStatus.REJECTED
            await self._save_plan(plan)
            await self._notify_ws(user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump())
            return plan

        # Check cancellation before execution
        if self._is_cancelled(plan_id):
            logger.info("plan_cancelled_before_execution", plan_id=plan_id)
            self._cancelled_plans.discard(plan_id)
            self._running_tasks.pop(plan_id, None)
            return plan

        # 5. Execute plan
        plan.overall_status = PlanStatus.EXECUTING
        await self._save_plan(plan)
        await self._notify_ws(user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump())

        try:
            plan = await self._execute_plan(plan, team_config)
        except asyncio.CancelledError:
            logger.info("plan_task_cancelled", plan_id=plan_id)
            # Status already set by cancel_plan(), just ensure cleanup
            if plan.overall_status != PlanStatus.CANCELLED:
                plan.overall_status = PlanStatus.CANCELLED
                await self._save_plan(plan)
        except Exception as exc:
            logger.exception("plan_execution_failed", plan_id=plan_id)
            plan.overall_status = PlanStatus.FAILED
            await self._save_plan(plan)
        finally:
            # Cleanup cancellation tracking
            self._cancelled_plans.discard(plan_id)
            self._running_tasks.pop(plan_id, None)

        # 6. Notify completion
        if plan.overall_status != PlanStatus.CANCELLED:
            await self._notify_ws(
                user_id,
                WebSocketMessageType.PLAN_COMPLETE,
                {"plan_id": plan_id, "summary": plan.m_plan.summary if plan.m_plan else ""},
            )
        return plan

    # ── Pre-Plan Clarification ─────────────────────────────────────────

    async def _pre_plan_clarification(
        self,
        user_id: str,
        plan_id: str,
        goal: str,
        team_config: TeamConfiguration,
        plan: Plan,
    ) -> str:
        """Optionally ask the user clarifying questions before generating a plan.

        Asks ONE question at a time.  After each answer the LLM (or heuristic)
        re-evaluates whether more info is needed.  Loops up to
        ``_MAX_CLARIFICATION_ROUNDS`` times so the user never sees a wall of
        questions.
        """
        _MAX_CLARIFICATION_ROUNDS = 5
        collected_answers: list[str] = []
        context_so_far = goal

        for round_num in range(_MAX_CLARIFICATION_ROUNDS):
            question = await self._generate_clarification_questions(
                context_so_far, team_config
            )
            if not question:
                break  # No more clarification needed

            logger.info(
                "pre_plan_clarification_needed",
                plan_id=plan_id,
                round=round_num + 1,
                question=question[:200],
            )

            # Update plan status so frontend shows the clarification input
            plan.overall_status = PlanStatus.CLARIFYING
            await self._save_plan(plan)
            await self._notify_ws(
                user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump()
            )

            # Persist the clarification question as an agent message so the
            # frontend can retrieve it via polling (not only via WebSocket).
            await self._db.save_agent_message(
                AgentMessage(
                    plan_id=plan_id,
                    step_id=f"pre-plan-clarification-{round_num + 1}",
                    agent="system",
                    agent_type=AgentType.PROXY,
                    content=question,
                ).model_dump()
            )

            if not self._proxy_agent:
                # No proxy agent — skip clarification
                plan.overall_status = PlanStatus.PLANNING
                await self._save_plan(plan)
                return ""

            from v1.magentic_agents.models.agent_models import AgentRunContext

            ctx = AgentRunContext(
                plan_id=plan_id,
                step_id=f"pre-plan-clarification-{round_num + 1}",
                user_id=user_id,
                task=question,
                previous_outputs={},
            )
            result = await self._proxy_agent.run(ctx)
            answer = result.content
            collected_answers.append(f"Q: {question}\nA: {answer}")

            # Enrich context for the next round's evaluation
            context_so_far = (
                f"{goal}\n\n## Clarifications so far\n"
                + "\n\n".join(collected_answers)
            )

        # Restore to PLANNING status
        plan.overall_status = PlanStatus.PLANNING
        await self._save_plan(plan)
        await self._notify_ws(
            user_id, WebSocketMessageType.PLAN_UPDATE, plan.model_dump()
        )

        return "\n\n".join(collected_answers) if collected_answers else ""

    async def _generate_clarification_questions(
        self,
        goal: str,
        team_config: TeamConfiguration,
    ) -> str:
        """Use the LLM (or heuristics) to decide the SINGLE most important
        clarifying question to ask next.

        Returns a single question string, or empty string if the goal
        (plus any prior answers) is clear enough.
        """
        prompt = (
            "You are a data migration planning assistant. A user submitted a migration request "
            "(possibly with follow-up clarifications already answered).\n\n"
            "Determine if the request is STILL missing critical information.\n\n"
            "Critical information includes:\n"
            "- Source database type and connection details\n"
            "- Target database/platform\n"
            "- Whether a target environment already exists or needs to be created\n"
            "- Specific tables or schemas to migrate (or if it's a full migration)\n"
            "- Any transformation or data quality requirements\n"
            "- Target Azure service for pipelines (ADF, Synapse, or Fabric) if applicable\n\n"
            "RULES:\n"
            "- If the request is clear and complete, respond with exactly: CLEAR\n"
            "- If clarification is needed, respond with EXACTLY ONE short question — "
            "the single most important piece of missing information. Do NOT ask multiple questions.\n\n"
            f"User request (with any prior clarifications):\n{goal}"
        )
        try:
            answer = await self._llm_chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
                timeout=60,
            )
            if answer is not None:
                answer = answer.strip()
                if answer.upper() == "CLEAR":
                    return ""
                return answer
        except Exception:
            logger.exception("clarification_question_generation_failed")
            return ""

        # Fallback: no LLM client available — use heuristics
        if True:
            # Local mode heuristic — return the FIRST missing piece only
            goal_lower = goal.lower()

            if not any(kw in goal_lower for kw in [
                "sql", "postgres", "mysql", "oracle", "cosmos", "mongo",
                "azure", "aws", "synapse", "fabric", "databricks",
                "source", "from",
            ]):
                return "What is the source database type and connection details?"

            if not any(kw in goal_lower for kw in [
                "target", "to ", "destination", "into",
                "azure", "synapse", "fabric", "cosmos", "databricks",
            ]):
                return "What is the target database or platform?"

            if not any(kw in goal_lower for kw in [
                "environment", "provision", "create", "existing", "infra",
            ]):
                return (
                    "Does the target environment already exist, or should it be "
                    "provisioned as part of this migration?"
                )

            return ""

    # ── Plan Generation ────────────────────────────────────────────────

    async def _generate_plan(
        self,
        goal: str,
        team_config: TeamConfiguration,
        plan_id: str,
    ) -> MPlan:
        """Use the planner LLM to generate an execution plan."""
        agent_names = [a.name for a in team_config.agents]
        agent_descriptions = "\n".join(
            f"- {a.name}: {a.description}" for a in team_config.agents
        )

        planner_prompt = team_config.planner_system_prompt or self._default_planner_prompt()

        messages = [
            {"role": "system", "content": planner_prompt},
            {
                "role": "user",
                "content": (
                    f"## User Goal\n{goal}\n\n"
                    f"## Available Agents\n{agent_descriptions}\n\n"
                    "Create a step-by-step execution plan. For each step, specify:\n"
                    "- step_number\n"
                    "- agent (must be one of the available agents)\n"
                    "- task (what the agent should do)\n"
                    "- description (details)\n"
                    "- dependencies (list of step numbers this depends on)\n\n"
                    "IMPORTANT: Include an early step to verify that the target environment "
                    "exists and provision it if not present.\n\n"
                    "Return your plan as JSON."
                ),
            },
        ]

        # Retry up to 2 times with increasing timeout via active LLM provider
        raw_plan: str | None = None
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                raw_plan = await self._llm_chat_completion(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000,
                    timeout=90 + attempt * 30,
                )
                if raw_plan is not None:
                    break
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "plan_generation_attempt_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                )

        if raw_plan is None:
            if last_exc:
                raise last_exc
            # No LLM client available — generate a default migration plan
            raw_plan = self._generate_default_plan(goal, agent_names)

        return parse_planner_response(raw_plan, plan_id, agent_names)

    def _default_planner_prompt(self) -> str:
        return """You are a data migration planning specialist. Given a user's migration goal
and a team of specialist agents, create an optimal execution plan.

Consider:
- Dependencies between steps (schema discovery must come before mapping)
- Parallel execution where possible
- Data quality validation at appropriate points
- A final reporting/summary step
- ALWAYS include an early step to verify the target environment exists and provision
  it if not present (use InfrastructureAgent). This step should run in parallel with
  source discovery so it completes before any migration steps that need the target.
- ALWAYS include a pipeline generation step (use PipelineGenerationAgent) after
  transformation and data quality steps. This agent creates linked-service
  connections and migration pipelines for Azure Data Factory, Synapse Analytics,
  or Microsoft Fabric based on the source type and target Azure service.

Return a JSON object with a "task" field and a "steps" array."""

    def _generate_default_plan(self, goal: str, agents: list[str]) -> str:
        """Generate a default migration plan for local development.

        Includes an environment setup step early in the pipeline so the
        target environment is provisioned/verified before migration begins.
        """
        import json

        default_steps = [
            {"step_number": 1, "agent": "DiscoveryAgent", "task": "Discover source database schema and metadata", "dependencies": []},
            {"step_number": 2, "agent": "InfrastructureAgent", "task": "Verify target environment exists and provision resources if not present", "dependencies": []},
            {"step_number": 3, "agent": "AnalysisAgent", "task": "Analyze migration complexity and risks", "dependencies": [1]},
            {"step_number": 4, "agent": "MappingAgent", "task": "Generate source-to-target schema mapping", "dependencies": [1, 3]},
            {"step_number": 5, "agent": "TransformationAgent", "task": "Define data transformation rules", "dependencies": [4]},
            {"step_number": 6, "agent": "DataQualityAgent", "task": "Create data validation rules", "dependencies": [4, 5]},
            {"step_number": 7, "agent": "PipelineGenerationAgent", "task": "Generate linked-service connections and migration pipeline definitions for the target Azure service (ADF/Synapse/Fabric)", "dependencies": [2, 5, 6]},
            {"step_number": 8, "agent": "ReportingAgent", "task": "Generate migration summary report", "dependencies": [1, 2, 3, 4, 5, 6, 7]},
        ]
        # Filter to available agents
        available = {a.lower().replace("agent", "") for a in agents}
        steps = [
            s for s in default_steps
            if s["agent"].lower().replace("agent", "") in available or s["agent"] in agents
        ]
        if not steps:
            steps = default_steps  # Use all if none match

        return json.dumps({"task": goal, "steps": steps})

    # ── Sub-task Generation ──────────────────────────────────────────

    async def _generate_subtasks(
        self,
        agent_name: str,
        task: str,
        tool_names: list[str],
    ) -> list[dict[str, str]]:
        """Generate a short list of sub-tasks an agent will perform.

        Returns a list of dicts: [{"id": "1", "label": "..."}]
        Uses a quick LLM call. Falls back to a single generic sub-task.
        """
        import json as _json

        tools_hint = ", ".join(tool_names[:15]) if tool_names else "general tools"

        try:
            raw = await self._llm_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You break down an agent's task into 3-6 concise sub-tasks. "
                            "Each sub-task should be a short action phrase (max 10 words). "
                            "Return ONLY a JSON array of strings. No markdown, no explanation."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Agent: {agent_name}\n"
                            f"Task: {task}\n"
                            f"Available tools: {tools_hint}\n\n"
                            "Break this into 3-6 ordered sub-tasks:"
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=300,
                timeout=60,
            )
            if raw is not None:
                raw = raw.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                labels = _json.loads(raw)
                if isinstance(labels, list) and all(isinstance(l, str) for l in labels):
                    return [
                        {"id": str(i + 1), "label": label}
                        for i, label in enumerate(labels[:8])
                    ]
        except Exception:
            logger.warning("subtask_generation_failed", agent=agent_name)

        # Fallback — single sub-task matching the overall task
        return [{"id": "1", "label": task}]

    # ── Plan Execution ─────────────────────────────────────────────────

    async def _execute_plan(
        self, plan: Plan, team_config: TeamConfiguration
    ) -> Plan:
        """Execute the plan step by step, respecting dependencies."""
        if not plan.m_plan or not plan.m_plan.steps:
            plan.overall_status = PlanStatus.COMPLETED
            return plan

        # Create agent instances
        agents = await self._factory.create_agents_from_team(team_config.agents)
        self._active_agents[plan.plan_id] = agents

        step_outputs: dict[str, str] = {}

        try:
            total_steps = len(plan.m_plan.steps)
            for step in plan.m_plan.steps:
                # ── Cancellation check ──
                if self._is_cancelled(plan.plan_id):
                    logger.info("plan_cancelled_in_step_loop", plan_id=plan.plan_id)
                    plan.overall_status = PlanStatus.CANCELLED
                    break

                # Check dependencies are complete
                deps_met = True
                for dep in step.dependencies:
                    dep_step = next(
                        (s for s in plan.m_plan.steps if s.step_number == dep),
                        None,
                    )
                    if dep_step and dep_step.status != StepStatus.COMPLETED:
                        step.status = StepStatus.SKIPPED
                        deps_met = False
                        break
                if not deps_met:
                    await self._notify_ws(
                        plan.user_id,
                        WebSocketMessageType.STEP_STATUS,
                        {
                            "step_number": step.step_number,
                            "agent": step.agent,
                            "task": step.task,
                            "status": StepStatus.SKIPPED.value,
                            "total_steps": total_steps,
                            "message": f"Skipped — dependency not met",
                        },
                    )
                    continue

                # Execute step — notify start
                step.status = StepStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc).isoformat()
                await self._save_plan(plan)
                await self._notify_ws(
                    plan.user_id,
                    WebSocketMessageType.STEP_STATUS,
                    {
                        "step_number": step.step_number,
                        "agent": step.agent,
                        "task": step.task,
                        "status": StepStatus.IN_PROGRESS.value,
                        "total_steps": total_steps,
                        "message": f"Agent {step.agent} is working on: {step.task}",
                    },
                )
                await self._notify_ws(
                    plan.user_id,
                    WebSocketMessageType.PLAN_UPDATE,
                    plan.model_dump(),
                )

                agent = agents.get(step.agent)
                if not agent:
                    step.status = StepStatus.FAILED
                    step.error = f"Agent '{step.agent}' not found in team"
                    step.completed_at = datetime.now(timezone.utc).isoformat()
                    await self._notify_ws(
                        plan.user_id,
                        WebSocketMessageType.STEP_STATUS,
                        {
                            "step_number": step.step_number,
                            "agent": step.agent,
                            "task": step.task,
                            "status": StepStatus.FAILED.value,
                            "total_steps": total_steps,
                            "error": step.error,
                            "message": f"Agent '{step.agent}' not found",
                        },
                    )
                    continue

                # ── Generate & send sub-tasks for this agent ──────────
                agent_tool_names: list[str] = []
                if isinstance(agent, FoundryAgentTemplate):
                    for mcp_cfg in agent.definition.mcp_tools:
                        agent_tool_names.extend(mcp_cfg.tool_names)

                subtasks = await self._generate_subtasks(
                    step.agent, step.task, agent_tool_names,
                )
                await self._notify_ws(
                    plan.user_id,
                    WebSocketMessageType.AGENT_SUBTASKS,
                    {
                        "step_number": step.step_number,
                        "agent": step.agent,
                        "subtasks": subtasks,
                        "total_steps": total_steps,
                    },
                )

                # ── Per-agent approval gate ───────────────────────
                # Send approval request so user can review sub-tasks
                await self._notify_ws(
                    plan.user_id,
                    WebSocketMessageType.STEP_APPROVAL_REQUEST,
                    {
                        "step_number": step.step_number,
                        "agent": step.agent,
                        "task": step.task,
                        "subtasks": subtasks,
                        "total_steps": total_steps,
                    },
                )

                step_approved, step_feedback = (
                    await self._approval_manager.request_step_approval(
                        user_id=plan.user_id,
                        plan_id=plan.plan_id,
                        step_number=step.step_number,
                    )
                )

                if not step_approved:
                    # Check if this rejection was due to plan cancellation
                    if self._is_cancelled(plan.plan_id):
                        plan.overall_status = PlanStatus.CANCELLED
                        break
                    step.status = StepStatus.SKIPPED
                    step.completed_at = datetime.now(timezone.utc).isoformat()
                    step.error = step_feedback or "Rejected by user"
                    # Mark all sub-tasks as failed
                    for st in subtasks:
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.SUBTASK_UPDATE,
                            {
                                "step_number": step.step_number,
                                "agent": step.agent,
                                "subtask_id": st["id"],
                                "status": "failed",
                            },
                        )
                    await self._notify_ws(
                        plan.user_id,
                        WebSocketMessageType.STEP_STATUS,
                        {
                            "step_number": step.step_number,
                            "agent": step.agent,
                            "task": step.task,
                            "status": StepStatus.SKIPPED.value,
                            "total_steps": total_steps,
                            "message": f"Step skipped — rejected by user"
                            + (f": {step_feedback}" if step_feedback else ""),
                        },
                    )
                    await self._save_plan(plan)
                    continue

                # ── Sequential sub-task execution with user input gates ──
                # Instead of one big agent.run(), execute each sub-task
                # individually, pausing for user input between each.

                # Build context with outputs from dependency steps
                prev_outputs = {
                    k: v for k, v in step_outputs.items()
                    if any(
                        s.agent == k
                        for s in plan.m_plan.steps
                        if s.step_number in step.dependencies
                    )
                }

                subtask_results: list[str] = []
                step_failed = False
                accumulated_context = ""  # Carries forward across sub-tasks
                user_provided_inputs: list[str] = []  # Explicit user answers

                for st_idx, st in enumerate(subtasks):
                    # ── Cancellation check ──
                    if self._is_cancelled(plan.plan_id):
                        logger.info(
                            "plan_cancelled_in_subtask_loop",
                            plan_id=plan.plan_id,
                            step=step.step_number,
                            subtask=st["id"],
                        )
                        step_failed = True
                        break

                    # Mark this sub-task as in_progress
                    await self._notify_ws(
                        plan.user_id,
                        WebSocketMessageType.SUBTASK_UPDATE,
                        {
                            "step_number": step.step_number,
                            "agent": step.agent,
                            "subtask_id": st["id"],
                            "status": "in_progress",
                        },
                    )

                    # Build a focused prompt for this individual sub-task
                    subtask_prompt_parts = [
                        f"You are executing sub-task {st_idx + 1} of "
                        f"{len(subtasks)} for the overall task: {step.task}\n\n"
                        f"Current sub-task: {st['label']}\n",
                    ]
                    if user_provided_inputs:
                        subtask_prompt_parts.append(
                            "\n## IMPORTANT — User-Provided Information:\n"
                            "The user has already answered the following. "
                            "Do NOT ask for this information again.\n"
                        )
                        for upi in user_provided_inputs:
                            subtask_prompt_parts.append(f"- {upi}\n")
                    if accumulated_context:
                        subtask_prompt_parts.append(
                            f"\n## Results from previous sub-tasks:\n"
                            f"{accumulated_context}\n"
                        )
                    if prev_outputs:
                        subtask_prompt_parts.append(
                            "\n## Previous Agent Outputs\n"
                        )
                        for ag_name, ag_output in prev_outputs.items():
                            subtask_prompt_parts.append(
                                f"### {ag_name}\n{ag_output}\n"
                            )

                    subtask_task = "\n".join(subtask_prompt_parts)

                    context = AgentRunContext(
                        plan_id=plan.plan_id,
                        step_id=step.id,
                        user_id=plan.user_id,
                        task=subtask_task,
                        previous_outputs=prev_outputs,
                    )

                    # Progress callback scoped to this sub-task
                    async def _tool_progress(
                        agent_name: str,
                        tool_name: str,
                        status: str,
                        detail: str,
                        *,
                        _step=step,
                        _total=total_steps,
                    ) -> None:
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.TOOL_PROGRESS,
                            {
                                "step_number": _step.step_number,
                                "agent": agent_name,
                                "tool_name": tool_name,
                                "status": status,
                                "detail": detail,
                                "total_steps": _total,
                            },
                        )

                    # Execute the agent for this single sub-task
                    result = await agent.run(
                        context, on_progress=_tool_progress,
                    )

                    if result.success:
                        subtask_results.append(result.content)
                        accumulated_context += (
                            f"\n### Sub-task {st_idx + 1}: {st['label']}\n"
                            f"{result.content}\n"
                        )

                        # Mark sub-task completed
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.SUBTASK_UPDATE,
                            {
                                "step_number": step.step_number,
                                "agent": step.agent,
                                "subtask_id": st["id"],
                                "status": "completed",
                            },
                        )

                        # Send the sub-task result to chat
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.AGENT_RESPONSE,
                            {
                                "agent": step.agent,
                                "content": (
                                    f"**Sub-task {st_idx + 1}/{len(subtasks)}: "
                                    f"{st['label']}**\n\n{result.content}"
                                ),
                                "step_number": step.step_number,
                                "subtask_id": st["id"],
                            },
                        )
                    else:
                        # Mark sub-task failed
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.SUBTASK_UPDATE,
                            {
                                "step_number": step.step_number,
                                "agent": step.agent,
                                "subtask_id": st["id"],
                                "status": "failed",
                            },
                        )
                        await self._notify_ws(
                            plan.user_id,
                            WebSocketMessageType.AGENT_RESPONSE,
                            {
                                "agent": step.agent,
                                "content": (
                                    f"**Sub-task {st_idx + 1}/{len(subtasks)}: "
                                    f"{st['label']}** — FAILED\n\n"
                                    f"{result.error or 'Unknown error'}"
                                ),
                                "step_number": step.step_number,
                                "subtask_id": st["id"],
                            },
                        )

                    # ── Input gate: ALWAYS wait for user after every sub-task ──
                    # This ensures questions are asked one at a time and the
                    # user can provide answers before proceeding.
                    is_last = st_idx >= len(subtasks) - 1
                    next_label = (
                        subtasks[st_idx + 1]["label"] if not is_last else ""
                    )

                    await self._notify_ws(
                        plan.user_id,
                        WebSocketMessageType.SUBTASK_INPUT_REQUEST,
                        {
                            "step_number": step.step_number,
                            "agent": step.agent,
                            "subtask_id": st["id"],
                            "subtask_label": st["label"],
                            "subtask_index": st_idx,
                            "total_subtasks": len(subtasks),
                            "next_subtask": next_label,
                            "is_last_subtask": is_last,
                            "result_preview": (
                                result.content[:500]
                                if result.success else
                                result.error or ""
                            )[:500],
                        },
                    )

                    user_response = (
                        await self._approval_manager.request_subtask_input(
                            user_id=plan.user_id,
                            plan_id=plan.plan_id,
                            step_number=step.step_number,
                            subtask_id=st["id"],
                        )
                    )

                    action = user_response.get("action", "continue")
                    answer = user_response.get("answer", "")

                    if action == "cancel":
                        # Cancelled via cancel_pending_for_plan
                        logger.info(
                            "subtask_cancelled",
                            plan_id=plan.plan_id,
                            step=step.step_number,
                        )
                        step_failed = True
                        break

                    if action == "skip":
                        # Mark remaining sub-tasks as skipped
                        for remaining in subtasks[st_idx + 1:]:
                            await self._notify_ws(
                                plan.user_id,
                                WebSocketMessageType.SUBTASK_UPDATE,
                                {
                                    "step_number": step.step_number,
                                    "agent": step.agent,
                                    "subtask_id": remaining["id"],
                                    "status": "failed",
                                },
                            )
                        break
                    # Capture user input regardless of action button used
                    if answer and answer.strip():
                        user_provided_inputs.append(
                            f"[After sub-task {st_idx + 1} "
                            f"({st['label']})]: {answer.strip()}"
                        )
                        accumulated_context += (
                            f"\n### User input after sub-task "
                            f"{st_idx + 1}:\n{answer}\n"
                        )

                    # ── Re-run if agent asked questions instead of acting ──
                    # Detect question-like responses (short, contains "?",
                    # no evidence of tool execution) and re-run with user
                    # answer appended so tools actually get called.
                    agent_asked_question = (
                        result.success
                        and "?" in result.content
                        and len(result.content) < 800
                        and answer
                        and answer.strip()
                    )
                    if agent_asked_question:
                        logger.info(
                            "subtask_rerun_with_user_answer",
                            agent=step.agent,
                            subtask=st["label"],
                            original_len=len(result.content),
                            user_answer=answer[:200],
                        )
                        # Rebuild prompt with user answer injected
                        rerun_parts = [
                            f"You are executing sub-task {st_idx + 1} of "
                            f"{len(subtasks)} for the overall task: "
                            f"{step.task}\n\n"
                            f"Current sub-task: {st['label']}\n",
                            "\n## IMPORTANT — User-Provided Information:\n"
                            "The user has already provided answers below. "
                            "Use this information and CALL YOUR TOOLS NOW "
                            "to create the resources. Do NOT ask more "
                            "questions.\n",
                        ]
                        for upi in user_provided_inputs:
                            rerun_parts.append(f"- {upi}\n")
                        if accumulated_context:
                            rerun_parts.append(
                                f"\n## Results from previous sub-tasks:\n"
                                f"{accumulated_context}\n"
                            )
                        if prev_outputs:
                            rerun_parts.append(
                                "\n## Previous Agent Outputs\n"
                            )
                            for ag_name, ag_output in prev_outputs.items():
                                rerun_parts.append(
                                    f"### {ag_name}\n{ag_output}\n"
                                )

                        rerun_context = AgentRunContext(
                            plan_id=plan.plan_id,
                            step_id=step.id,
                            user_id=plan.user_id,
                            task="\n".join(rerun_parts),
                            previous_outputs=prev_outputs,
                        )
                        rerun_result = await agent.run(
                            rerun_context, on_progress=_tool_progress,
                        )
                        if rerun_result.success:
                            # Replace the original question with actual result
                            subtask_results[-1] = rerun_result.content
                            accumulated_context = (
                                accumulated_context.rsplit(
                                    f"### Sub-task {st_idx + 1}:", 1
                                )[0]
                                + f"\n### Sub-task {st_idx + 1}: "
                                f"{st['label']}\n{rerun_result.content}\n"
                            )
                            result = rerun_result
                            # Update chat with actual result
                            await self._notify_ws(
                                plan.user_id,
                                WebSocketMessageType.AGENT_RESPONSE,
                                {
                                    "agent": step.agent,
                                    "content": (
                                        f"**Sub-task {st_idx + 1}/"
                                        f"{len(subtasks)}: "
                                        f"{st['label']}** (re-run with "
                                        f"your input)\n\n"
                                        f"{rerun_result.content}"
                                    ),
                                    "step_number": step.step_number,
                                    "subtask_id": st["id"],
                                },
                            )

                    # If the sub-task failed, stop executing further
                    if not result.success:
                        step_failed = True
                        # Mark remaining sub-tasks as failed
                        for remaining in subtasks[st_idx + 1:]:
                            await self._notify_ws(
                                plan.user_id,
                                WebSocketMessageType.SUBTASK_UPDATE,
                                {
                                    "step_number": step.step_number,
                                    "agent": step.agent,
                                    "subtask_id": remaining["id"],
                                    "status": "failed",
                                },
                            )
                        break

                # ── Step completion ───────────────────────────────
                combined_output = "\n\n".join(subtask_results)
                if step_failed:
                    step.status = StepStatus.FAILED
                    step.error = result.error or "Sub-task execution failed"
                else:
                    step.status = StepStatus.COMPLETED
                    step.output = combined_output
                    step_outputs[step.agent] = combined_output

                step.completed_at = datetime.now(timezone.utc).isoformat()

                # Calculate duration
                duration_str = ""
                if step.started_at and step.completed_at:
                    try:
                        start_t = datetime.fromisoformat(step.started_at)
                        end_t = datetime.fromisoformat(step.completed_at)
                        dur = (end_t - start_t).total_seconds()
                        duration_str = f"{dur:.1f}s"
                    except Exception:
                        pass

                # Notify step completion/failure
                await self._notify_ws(
                    plan.user_id,
                    WebSocketMessageType.STEP_STATUS,
                    {
                        "step_number": step.step_number,
                        "agent": step.agent,
                        "task": step.task,
                        "status": step.status.value,
                        "total_steps": total_steps,
                        "duration": duration_str,
                        "output": (combined_output[:500] if combined_output else ""),
                        "error": step.error or "",
                        "message": (
                            f"{step.agent} completed in {duration_str}"
                            if not step_failed
                            else f"{step.agent} failed: {step.error}"
                        ),
                    },
                )

                # Save agent message (combined output)
                await self._db.save_agent_message(
                    AgentMessage(
                        plan_id=plan.plan_id,
                        step_id=step.id,
                        agent=step.agent,
                        content=combined_output,
                        agent_type=AgentType.FOUNDRY,
                    ).model_dump()
                )

                await self._save_plan(plan)

            # Determine final status (preserve CANCELLED if already set)
            if plan.overall_status != PlanStatus.CANCELLED:
                failed = any(s.status == StepStatus.FAILED for s in plan.m_plan.steps)
                plan.overall_status = PlanStatus.FAILED if failed else PlanStatus.COMPLETED

            # Generate summary
            if plan.overall_status == PlanStatus.COMPLETED:
                plan.m_plan.summary = self._build_summary(plan.m_plan, step_outputs)
                plan.m_plan.status = PlanStatus.COMPLETED

        finally:
            # Cleanup agents
            await self._factory.cleanup_agents(agents)
            self._active_agents.pop(plan.plan_id, None)

        await self._save_plan(plan)
        return plan

    def _build_summary(self, m_plan: MPlan, outputs: dict[str, str]) -> str:
        """Build a summary of the completed plan execution."""
        completed = sum(1 for s in m_plan.steps if s.status == StepStatus.COMPLETED)
        total = len(m_plan.steps)
        return (
            f"Migration plan completed: {completed}/{total} steps successful.\n\n"
            + "\n".join(
                f"**{agent}**: {output[:200]}..."
                if len(output) > 200
                else f"**{agent}**: {output}"
                for agent, output in outputs.items()
            )
        )

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _save_plan(self, plan: Plan) -> None:
        """Save/update plan in database."""
        plan.updated_at = datetime.now(timezone.utc).isoformat()
        doc = plan.model_dump()
        doc["doc_type"] = "plan"
        await self._db.upsert_document(doc, partition_key=plan.user_id)

    async def _create_failed_plan(
        self, plan_id: str, user_id: str, goal: str, error: str
    ) -> Plan:
        plan = Plan(
            plan_id=plan_id,
            user_id=user_id,
            initial_goal=goal,
            overall_status=PlanStatus.FAILED,
        )
        await self._save_plan(plan)
        await self._notify_ws(
            user_id,
            WebSocketMessageType.ERROR,
            {"message": error, "plan_id": plan_id},
        )
        return plan

    async def _notify_ws(
        self,
        user_id: str,
        msg_type: WebSocketMessageType,
        data: dict[str, Any],
    ) -> None:
        """Send a WebSocket notification if callback is registered."""
        if self._send_ws:
            try:
                await self._send_ws(
                    user_id,
                    WebSocketMessage(type=msg_type, data=data),
                )
            except Exception:
                logger.exception("ws_send_failed", user_id=user_id, type=msg_type)
