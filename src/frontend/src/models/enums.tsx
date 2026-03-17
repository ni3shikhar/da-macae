/** Agent types available in the system. */
export enum AgentType {
  FOUNDRY = "foundry",
  PROXY = "proxy",
  REASONING = "reasoning",
  RAI = "rai",
}

/** Lifecycle status of a plan. */
export enum PlanStatus {
  CREATED = "created",
  PLANNING = "planning",
  CLARIFYING = "clarifying",
  AWAITING_APPROVAL = "awaiting_approval",
  APPROVED = "approved",
  REJECTED = "rejected",
  EXECUTING = "executing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

/** Lifecycle status of a plan step. */
export enum StepStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

/** Target Azure data service for pipeline generation. */
export enum AzureServiceType {
  ADF = "adf",
  SYNAPSE = "synapse",
  FABRIC = "fabric",
}

/** WebSocket message types. */
export enum WSMessageType {
  PLAN_UPDATE = "plan_update",
  AGENT_RESPONSE = "agent_response",
  STREAMING_CONTENT = "streaming_content",
  HUMAN_CLARIFICATION_REQUEST = "human_clarification_request",
  PLAN_COMPLETE = "plan_complete",
  ERROR = "error",
  USER_CLARIFICATION_RESPONSE = "user_clarification_response",
  PLAN_APPROVAL = "plan_approval",
  STEP_STATUS = "step_status",
  TOOL_PROGRESS = "tool_progress",
  AGENT_SUBTASKS = "agent_subtasks",
  SUBTASK_UPDATE = "subtask_update",
  STEP_APPROVAL_REQUEST = "step_approval_request",
  SUBTASK_INPUT_REQUEST = "subtask_input_request",
}
