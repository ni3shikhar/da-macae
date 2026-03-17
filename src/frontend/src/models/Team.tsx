import { AgentType } from "./enums";

/** Agent definition within a team configuration. */
export interface AgentDefinition {
  id: string;
  name: string;
  description: string;
  agent_type: AgentType;
  model: string;
  system_prompt: string;
  tools: string[];
  mcp_tools: MCPToolConfig[];
  search_tools: SearchToolConfig[];
  code_interpreter: boolean;
  bing_search: boolean;
}

export interface MCPToolConfig {
  server_url: string;
  tool_names: string[];
}

export interface SearchToolConfig {
  index_name: string;
  description: string;
}

/** A pre-defined starting task for a team. */
export interface StartingTask {
  title: string;
  description: string;
  prompt: string;
}

/** A complete team configuration. */
export interface TeamConfiguration {
  id: string;
  user_id: string;
  name: string;
  description: string;
  agents: AgentDefinition[];
  starting_tasks: StartingTask[];
  planner_system_prompt: string;
  created_at: string;
  updated_at: string;
}
