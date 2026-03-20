/**
 * Agent API layer — swap `USE_MOCK` or implement real fetch against your backend.
 *
 * Expected backend:
 *   POST /api/agent/run          → { id: string }
 *   GET  /api/agent/status/:id   → AgentRunResult
 *
 * Vite proxy (vite.config.ts) forwards /api → http://localhost:8080 when you add a server.
 */

import type { AgentLogEntry, AgentRunResult, StartRunResponse } from "../types/agent";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/** Set to false when your backend implements the contract above. */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

function nowIso(): string {
  return new Date().toISOString();
}

const STEP_BLUEPRINT: { id: string; label: string }[] = [
  { id: "pods", label: "Listing pods" },
  { id: "logs", label: "Inspecting logs" },
  { id: "root", label: "Detecting the root cause" },
  { id: "remediate", label: "Applying a corrective environment variable" },
  { id: "verify", label: "Verifying the fix" },
  { id: "report", label: "Reporting final status" },
];

const MOCK_LOG_MESSAGES: Record<string, { level: AgentLogEntry["level"]; message: string }> = {
  pods: { level: "info", message: "Enumerating pods in namespace openshift-demo-app (label app=payments-api)." },
  logs: { level: "info", message: "Tailing last 200 lines from pod payments-api-7d4f8b9c-xk2lm." },
  root: { level: "warning", message: "Detected missing DATABASE_SSL_MODE; connection pool exhausted under load." },
  remediate: { level: "info", message: "Patching Deployment env: DATABASE_SSL_MODE=require (dry-run validated)." },
  verify: { level: "success", message: "Health check /ready returned 200; error rate dropped below threshold." },
  report: { level: "success", message: "Runbook entry created; stakeholders notified via operations channel." },
};

type MockRun = {
  phase: number;
  logs: AgentRunResult["logs"];
  failedAt?: string;
};

const mockRuns = new Map<string, MockRun>();

function buildSteps(phase: number, failedAt?: string): AgentRunResult["steps"] {
  return STEP_BLUEPRINT.map((s, i) => {
    if (failedAt === s.id) {
      return {
        ...s,
        status: "failed" as const,
        message: "Step failed — see activity log for details.",
        timestamp: nowIso(),
      };
    }
    if (i < phase) {
      return { ...s, status: "completed" as const, timestamp: nowIso() };
    }
    if (i === phase) {
      return {
        ...s,
        status: "in_progress" as const,
        message: "In progress…",
        timestamp: nowIso(),
      };
    }
    return { ...s, status: "pending" as const };
  });
}

function mockStartRun(): StartRunResponse {
  const id = crypto.randomUUID();
  mockRuns.set(id, { phase: 0, logs: [] });
  return { id };
}

function mockGetStatus(id: string): AgentRunResult {
  const run = mockRuns.get(id);
  if (!run) {
    return {
      state: "error",
      steps: STEP_BLUEPRINT.map((s) => ({ ...s, status: "pending" })),
      logs: [
        {
          id: crypto.randomUUID(),
          level: "error",
          message: `Unknown run id: ${id}`,
          timestamp: nowIso(),
        },
      ],
      error: "Run not found",
    };
  }

  const { phase, logs, failedAt } = run;

  if (failedAt) {
    return {
      state: "error",
      steps: buildSteps(phase, failedAt),
      logs,
      error: "Remediation could not be verified. Rollback recommended.",
    };
  }

  if (phase >= STEP_BLUEPRINT.length) {
    return {
      state: "success",
      steps: STEP_BLUEPRINT.map((s) => ({ ...s, status: "completed" as const, timestamp: nowIso() })),
      logs,
      summary:
        "Issue: missing DATABASE_SSL_MODE caused TLS handshake failures under load. " +
        "Action: env var applied on Deployment; rollout completed. Verification: /ready OK, SLO restored.",
    };
  }

  const current = STEP_BLUEPRINT[phase];
  const stepKey = current.id;
  const logTemplate = MOCK_LOG_MESSAGES[stepKey];
  if (logTemplate) {
    const exists = logs.some((l) => l.message === logTemplate.message);
    if (!exists) {
      logs.push({
        id: crypto.randomUUID(),
        level: logTemplate.level,
        message: logTemplate.message,
        timestamp: nowIso(),
      });
    }
  }

  const result: AgentRunResult = {
    state: "running",
    steps: buildSteps(phase),
    logs: [...logs],
  };

  run.phase += 1;
  return result;
}

/** Optional: simulate failure on step "verify" for demos — call from devtools: window.__agentFailNext = true */
declare global {
  interface Window {
    __agentFailNext?: boolean;
  }
}

function mockAdvanceWithOptionalFailure(id: string): AgentRunResult {
  const run = mockRuns.get(id);
  if (!run) return mockGetStatus(id);
  if (typeof window !== "undefined" && window.__agentFailNext && run.phase === 4) {
    window.__agentFailNext = false;
    run.failedAt = "verify";
    run.logs.push({
      id: crypto.randomUUID(),
      level: "error",
      message: "Verification failed: readiness probe still failing after 3 attempts.",
      timestamp: nowIso(),
    });
  }
  return mockGetStatus(id);
}

export async function startAgentRun(): Promise<StartRunResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    return mockStartRun();
  }
  const res = await fetch(`${API_BASE}/api/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`startAgentRun failed: ${res.status}`);
  return res.json() as Promise<StartRunResponse>;
}

export async function getAgentStatus(id: string): Promise<AgentRunResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 350));
    return mockAdvanceWithOptionalFailure(id);
  }
  const res = await fetch(`${API_BASE}/api/agent/status/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`getAgentStatus failed: ${res.status}`);
  return res.json() as Promise<AgentRunResult>;
}
