"""Human approval manager for plan review and approval workflow.

Implements the Plan → Approve → Execute pattern where users review
the generated plan before execution begins.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

import structlog

from common.models.messages import Plan, PlanStatus

logger = structlog.get_logger(__name__)

# Callback type for sending plan to UI for approval
PlanApprovalCallback = Callable[
    [str, Plan],  # user_id, plan
    Coroutine[Any, Any, None],
]


class HumanApprovalManager:
    """Manages the human approval gate in the plan→approve→execute flow.

    When a plan is generated, it is sent to the user for review.
    The user can approve, reject, or request modifications.
    Also supports per-step (per-agent) approval after sub-tasks are generated.
    """

    def __init__(self) -> None:
        # Pending approval futures keyed by (user_id, plan_id)
        self._pending: dict[tuple[str, str], asyncio.Future[bool]] = {}
        self._feedback: dict[tuple[str, str], str] = {}
        self._send_for_approval: PlanApprovalCallback | None = None

        # Per-step approval futures keyed by (user_id, plan_id, step_number)
        self._step_pending: dict[tuple[str, str, int], asyncio.Future[bool]] = {}
        self._step_feedback: dict[tuple[str, str, int], str] = {}

        # Per-subtask input gates keyed by (user_id, plan_id, step_number, subtask_id)
        # Future resolves to a dict: {"action": "continue"|"skip"|"answer", "answer": "..."}
        self._subtask_pending: dict[
            tuple[str, str, int, str], asyncio.Future[dict[str, str]]
        ] = {}

    def set_approval_callback(self, callback: PlanApprovalCallback) -> None:
        """Set the callback that sends plans to the UI for approval."""
        self._send_for_approval = callback

    async def request_approval(
        self,
        user_id: str,
        plan: Plan,
        timeout_seconds: float = 600.0,
    ) -> tuple[bool, str]:
        """Send a plan for human approval and wait for a response.

        Returns:
            Tuple of (approved: bool, feedback: str)
        """
        key = (user_id, plan.plan_id)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._pending[key] = future
        self._feedback[key] = ""

        logger.info(
            "approval_requested",
            user_id=user_id,
            plan_id=plan.plan_id,
            steps=len(plan.m_plan.steps) if plan.m_plan else 0,
        )

        # Update plan status
        plan.overall_status = PlanStatus.AWAITING_APPROVAL

        # Send to UI
        if self._send_for_approval:
            await self._send_for_approval(user_id, plan)

        try:
            approved = await asyncio.wait_for(future, timeout=timeout_seconds)
            feedback = self._feedback.get(key, "")

            if approved:
                plan.overall_status = PlanStatus.APPROVED
                logger.info("plan_approved", plan_id=plan.plan_id)
            else:
                plan.overall_status = PlanStatus.REJECTED
                logger.info(
                    "plan_rejected",
                    plan_id=plan.plan_id,
                    feedback=feedback[:100],
                )

            return approved, feedback

        except asyncio.TimeoutError:
            logger.warning(
                "approval_timeout",
                user_id=user_id,
                plan_id=plan.plan_id,
                timeout=timeout_seconds,
            )
            plan.overall_status = PlanStatus.CANCELLED
            return False, "Approval timed out"

        finally:
            self._pending.pop(key, None)
            self._feedback.pop(key, None)

    def resolve_approval(
        self,
        user_id: str,
        plan_id: str,
        approved: bool,
        feedback: str = "",
    ) -> bool:
        """Resolve a pending plan approval.

        Returns True if a pending approval was found and resolved.
        """
        key = (user_id, plan_id)
        future = self._pending.get(key)
        if future and not future.done():
            self._feedback[key] = feedback
            future.set_result(approved)
            return True
        logger.warning(
            "approval_not_found",
            user_id=user_id,
            plan_id=plan_id,
        )
        return False

    # ── Per-step (per-agent) approval ───────────────────────────────

    async def request_step_approval(
        self,
        user_id: str,
        plan_id: str,
        step_number: int,
        timeout_seconds: float = 600.0,
    ) -> tuple[bool, str]:
        """Wait for user to approve/reject a specific step after sub-task review.

        Returns:
            Tuple of (approved: bool, feedback: str)
        """
        key = (user_id, plan_id, step_number)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._step_pending[key] = future
        self._step_feedback[key] = ""

        logger.info(
            "step_approval_requested",
            user_id=user_id,
            plan_id=plan_id,
            step_number=step_number,
        )

        try:
            approved = await asyncio.wait_for(future, timeout=timeout_seconds)
            feedback = self._step_feedback.get(key, "")

            if approved:
                logger.info(
                    "step_approved",
                    plan_id=plan_id,
                    step_number=step_number,
                )
            else:
                logger.info(
                    "step_rejected",
                    plan_id=plan_id,
                    step_number=step_number,
                    feedback=feedback[:100],
                )

            return approved, feedback

        except asyncio.TimeoutError:
            logger.warning(
                "step_approval_timeout",
                user_id=user_id,
                plan_id=plan_id,
                step_number=step_number,
                timeout=timeout_seconds,
            )
            return False, "Step approval timed out"

        finally:
            self._step_pending.pop(key, None)
            self._step_feedback.pop(key, None)

    def resolve_step_approval(
        self,
        user_id: str,
        plan_id: str,
        step_number: int,
        approved: bool,
        feedback: str = "",
    ) -> bool:
        """Resolve a pending step approval.

        Returns True if a pending step approval was found and resolved.
        """
        key = (user_id, plan_id, step_number)
        future = self._step_pending.get(key)
        if future and not future.done():
            self._step_feedback[key] = feedback
            future.set_result(approved)
            return True
        logger.warning(
            "step_approval_not_found",
            user_id=user_id,
            plan_id=plan_id,
            step_number=step_number,
        )
        return False

    # ── Per-subtask input gate ──────────────────────────────────────

    async def request_subtask_input(
        self,
        user_id: str,
        plan_id: str,
        step_number: int,
        subtask_id: str,
        timeout_seconds: float = 600.0,
    ) -> dict[str, str]:
        """Wait for user input after a sub-task completes.

        Returns a dict: {"action": "continue"|"skip"|"answer", "answer": "..."}
        """
        key = (user_id, plan_id, step_number, subtask_id)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, str]] = loop.create_future()
        self._subtask_pending[key] = future

        logger.info(
            "subtask_input_requested",
            user_id=user_id,
            plan_id=plan_id,
            step_number=step_number,
            subtask_id=subtask_id,
        )

        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            logger.info(
                "subtask_input_received",
                plan_id=plan_id,
                step_number=step_number,
                subtask_id=subtask_id,
                action=result.get("action", "continue"),
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(
                "subtask_input_timeout",
                user_id=user_id,
                plan_id=plan_id,
                step_number=step_number,
                subtask_id=subtask_id,
            )
            return {"action": "continue", "answer": ""}

        finally:
            self._subtask_pending.pop(key, None)

    def resolve_subtask_input(
        self,
        user_id: str,
        plan_id: str,
        step_number: int,
        subtask_id: str,
        action: str = "continue",
        answer: str = "",
    ) -> bool:
        """Resolve a pending subtask input gate.

        Returns True if a pending gate was found and resolved.
        """
        key = (user_id, plan_id, step_number, subtask_id)
        future = self._subtask_pending.get(key)
        if future and not future.done():
            future.set_result({"action": action, "answer": answer})
            return True
        logger.warning(
            "subtask_input_not_found",
            user_id=user_id,
            plan_id=plan_id,
            step_number=step_number,
            subtask_id=subtask_id,
        )
        return False

    # ── Cancel — resolve all pending futures for a plan ─────────────

    def cancel_pending_for_plan(self, user_id: str, plan_id: str) -> int:
        """Cancel all pending approval/input gates for a plan.

        Resolves plan approval as rejected, step approvals as rejected,
        and subtask inputs as skip.  Returns the number of futures resolved.
        """
        resolved = 0

        # Plan-level approval
        plan_key = (user_id, plan_id)
        fut = self._pending.get(plan_key)
        if fut and not fut.done():
            self._feedback[plan_key] = "Cancelled by user"
            fut.set_result(False)
            resolved += 1

        # Step-level approvals
        step_keys = [
            k for k in self._step_pending if k[0] == user_id and k[1] == plan_id
        ]
        for key in step_keys:
            fut = self._step_pending.get(key)
            if fut and not fut.done():
                self._step_feedback[key] = "Cancelled by user"
                fut.set_result(False)
                resolved += 1

        # Subtask input gates
        subtask_keys = [
            k for k in self._subtask_pending if k[0] == user_id and k[1] == plan_id
        ]
        for key in subtask_keys:
            fut = self._subtask_pending.get(key)
            if fut and not fut.done():
                fut.set_result({"action": "cancel", "answer": ""})
                resolved += 1

        logger.info(
            "cancelled_pending_for_plan",
            user_id=user_id,
            plan_id=plan_id,
            resolved=resolved,
        )
        return resolved
