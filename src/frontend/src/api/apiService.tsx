/** API service layer — typed wrappers around backend endpoints. */

import { get, post } from "./apiClient";
import type { Plan, AgentMessage, TeamConfiguration } from "../models";

// ── Plans ──────────────────────────────────────────────────────────

export async function getPlans(userId: string): Promise<Plan[]> {
  return get<Plan[]>(`/plans?user_id=${encodeURIComponent(userId)}`);
}

export async function getPlan(planId: string, userId: string): Promise<Plan> {
  return get<Plan>(
    `/plan?plan_id=${encodeURIComponent(planId)}&user_id=${encodeURIComponent(userId)}`
  );
}

export async function processRequest(
  userId: string,
  message: string,
  teamId: string
): Promise<{ status: string; message: string }> {
  return post("/process_request", {
    user_id: userId,
    message,
    team_id: teamId,
  });
}

// ── Cancel Plan ────────────────────────────────────────────────────

export async function cancelPlan(
  planId: string,
  userId: string,
  reason: string = ""
): Promise<{ status: string; plan_id: string }> {
  return post("/cancel_plan", {
    plan_id: planId,
    user_id: userId,
    reason,
  });
}

// ── Plan Approval ──────────────────────────────────────────────────

export async function approvePlan(
  planId: string,
  userId: string,
  approved: boolean,
  feedback: string = ""
): Promise<{ status: string }> {
  return post("/plan_approval", {
    plan_id: planId,
    user_id: userId,
    approved,
    feedback,
  });
}

// ── Step (Agent) Approval ──────────────────────────────────────────

export async function approveStep(
  planId: string,
  userId: string,
  stepNumber: number,
  approved: boolean,
  feedback: string = ""
): Promise<{ status: string }> {
  return post("/step_approval", {
    plan_id: planId,
    user_id: userId,
    step_number: stepNumber,
    approved,
    feedback,
  });
}

// ── Clarification ──────────────────────────────────────────────────

export async function sendClarification(
  planId: string,
  userId: string,
  response: string
): Promise<{ status: string }> {
  return post("/user_clarification", {
    plan_id: planId,
    user_id: userId,
    response,
  });
}

// ── User Messages ──────────────────────────────────────────────────

export async function sendUserMessage(
  planId: string,
  userId: string,
  message: string
): Promise<{ status: string }> {
  return post("/user_message", {
    plan_id: planId,
    user_id: userId,
    response: message,
  });
}

// ── Sub-task Response ──────────────────────────────────────────────

export async function sendSubtaskResponse(
  planId: string,
  userId: string,
  stepNumber: number,
  subtaskId: string,
  action: "continue" | "skip" | "answer" | "auto_approve_all",
  answer: string = ""
): Promise<{ status: string }> {
  return post("/subtask_response", {
    plan_id: planId,
    user_id: userId,
    step_number: stepNumber,
    subtask_id: subtaskId,
    action,
    answer,
  });
}

// ── LLM Provider ───────────────────────────────────────────────────

export interface LlmProviderInfo {
  active: string;
  available: string[];
}

export async function getLlmProvider(): Promise<LlmProviderInfo> {
  return get<LlmProviderInfo>("/llm_provider");
}

export async function setLlmProvider(
  provider: string
): Promise<{ status: string; active: string }> {
  return post("/llm_provider", { provider });
}

// ── Teams ──────────────────────────────────────────────────────────

export async function getTeamConfigs(
  userId: string
): Promise<TeamConfiguration[]> {
  return get<TeamConfiguration[]>(
    `/team_configs?user_id=${encodeURIComponent(userId)}`
  );
}

export async function getTeamConfig(
  teamId: string,
  userId: string
): Promise<TeamConfiguration> {
  return get<TeamConfiguration>(
    `/team_config?team_id=${encodeURIComponent(teamId)}&user_id=${encodeURIComponent(userId)}`
  );
}

export async function selectTeam(
  userId: string,
  teamId: string
): Promise<{ status: string }> {
  return post("/select_team", { user_id: userId, team_id: teamId });
}

// ── Agent Messages ─────────────────────────────────────────────────

export async function getAgentMessages(
  planId: string
): Promise<AgentMessage[]> {
  return get<AgentMessage[]>(
    `/agent_messages?plan_id=${encodeURIComponent(planId)}`
  );
}
