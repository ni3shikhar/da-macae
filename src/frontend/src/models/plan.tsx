import { AzureServiceType, PlanStatus, StepStatus } from "./enums";

/** A single step in a migration execution plan. */
export interface PlanStep {
  id: string;
  step_number: number;
  agent: string;
  task: string;
  description: string;
  status: StepStatus;
  output: string;
  error: string;
  started_at: string | null;
  completed_at: string | null;
  dependencies: number[];
}

/** Magentic Plan — the executable plan with ordered steps. */
export interface MPlan {
  id: string;
  plan_id: string;
  task: string;
  steps: PlanStep[];
  status: PlanStatus;
  summary: string;
}

/** Top-level plan document. */
export interface Plan {
  id: string;
  plan_id: string;
  user_id: string;
  initial_goal: string;
  overall_status: PlanStatus;
  m_plan: MPlan | null;
  team_id: string;
  created_at: string;
  updated_at: string;
}

/** Configuration for a data-source connection used in pipeline generation. */
export interface ConnectionConfig {
  id: string;
  source_type: string;
  azure_service: AzureServiceType;
  connection_name: string;
  connection_params: Record<string, string>;
  linked_service_json: string | null;
  deployed: boolean;
  status: string; // pending | generated | deployed | error
  error: string;
  created_at: string;
}

/** Configuration for a generated migration pipeline. */
export interface PipelineConfig {
  id: string;
  pipeline_name: string;
  azure_service: AzureServiceType;
  source_connection_id: string;
  target_connection_id: string;
  tables: string[];
  pipeline_json: string | null;
  deployed: boolean;
  status: string;
}

/** Agent message from plan execution. */
export interface AgentMessage {
  id: string;
  plan_id: string;
  step_id: string;
  agent: string;
  content: string;
  timestamp: string;
}
