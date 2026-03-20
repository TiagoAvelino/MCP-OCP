export type AgentRunState = "idle" | "running" | "success" | "error";

export type AgentStepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed";

export interface AgentStep {
  id: string;
  label: string;
  status: AgentStepStatus;
  message?: string;
  timestamp?: string;
}

export interface AgentLogEntry {
  id: string;
  level: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: string;
}

export interface AgentRunResult {
  state: AgentRunState;
  steps: AgentStep[];
  logs: AgentLogEntry[];
  summary?: string;
  error?: string;
}

export interface StartRunResponse {
  id: string;
}
