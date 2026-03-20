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
  level: "info" | "stderr" | "stdout" | "error" | "step_delimiter";
  message: string;
  timestamp: string;
}

/** Order used by timeline + finalization when the run ends */
export const REMEDIATION_STEP_ORDER = [
  "listing_pods",
  "select_target",
  "reading_logs",
  "identifying_root_cause",
  "applying_env",
  "completed",
] as const;

export type RemediationStepId = (typeof REMEDIATION_STEP_ORDER)[number];

export const REMEDIATION_STEP_LABELS: Record<string, string> = {
  listing_pods: "Listing pods (problem filter)",
  select_target: "Selecting target pod",
  reading_logs: "Reading pod logs",
  identifying_root_cause: "Identifying root cause",
  applying_env: "Applying environment variables",
  completed: "Completed",
};

export type RemediationStepMap = Record<
  string,
  RemediationStepStatus | "pending"
>;

/**
 * Backend only emits step…in_progress heuristics, so when the final `result`
 * arrives we normalize: success → all completed; failure → completed up to
 * last active step, then failed.
 */
export function finalizeRemediationSteps(
  prev: RemediationStepMap,
  success: boolean,
): RemediationStepMap {
  const next: RemediationStepMap = { ...prev };
  if (success) {
    for (const id of REMEDIATION_STEP_ORDER) {
      next[id] = "completed";
    }
    return next;
  }

  let lastActive = -1;
  for (let i = 0; i < REMEDIATION_STEP_ORDER.length; i++) {
    const id = REMEDIATION_STEP_ORDER[i];
    const st = next[id] ?? "pending";
    if (st === "in_progress" || st === "completed" || st === "failed") {
      lastActive = i;
    }
  }

  if (lastActive === -1) {
    next.completed = "failed";
    return next;
  }

  for (let i = 0; i < REMEDIATION_STEP_ORDER.length; i++) {
    const id = REMEDIATION_STEP_ORDER[i];
    if (i < lastActive) {
      next[id] = "completed";
    } else if (i === lastActive) {
      next[id] = "failed";
    } else if (id === "completed") {
      next[id] = "failed";
    } else {
      next[id] = "pending";
    }
  }
  return next;
}
