/**
 * SSE event protocol: backend emits JSON in each SSE `data:` line.
 */
export type RemediationRunState = "idle" | "running" | "success" | "error";

export type RemediationStepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed";

export type StreamEvent =
  | { type: "status"; state: RemediationRunState; timestamp: string }
  | {
      type: "step";
      step: string;
      status: RemediationStepStatus;
      message?: string;
      timestamp: string;
    }
  | {
      type: "log";
      level: "info" | "stderr" | "stdout" | "error";
      message: string;
      timestamp: string;
    }
  | {
      type: "result";
      success: boolean;
      exitCode: number;
      summary: string;
      timestamp: string;
    };

export interface RemediationLogLine {
  id: string;
  level: "info" | "stderr" | "stdout" | "error";
  message: string;
  timestamp: string;
}

export const REMEDIATION_STEP_LABELS: Record<string, string> = {
  listing_pods: "Listing pods (problem filter)",
  select_target: "Selecting target pod",
  reading_logs: "Reading pod logs",
  identifying_root_cause: "Identifying root cause",
  applying_env: "Applying environment variables",
  completed: "Completed",
};
