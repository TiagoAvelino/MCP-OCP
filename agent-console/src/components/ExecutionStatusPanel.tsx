import type { AgentRunResult, AgentStep } from "../types/agent";
import { StatusBadge } from "./StatusBadge";

function currentStepLabel(steps: AgentStep[]): string {
  const active = steps.find((s) => s.status === "in_progress");
  if (active) return active.label;
  const lastDone = [...steps].reverse().find((s) => s.status === "completed");
  if (lastDone) return lastDone.label;
  return "—";
}

type Props = {
  result: AgentRunResult;
  runId: string | null;
  isStarting: boolean;
};

export function ExecutionStatusPanel({ result, runId, isStarting }: Props) {
  const { state, steps, error } = result;

  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-rh-ink">Execution status</h2>
            <StatusBadge state={state} />
          </div>
          {runId && (
            <p className="font-mono text-xs text-rh-muted">
              Run ID: <span className="text-rh-ink">{runId}</span>
            </p>
          )}
          <div className="rounded-xl bg-rh-surface px-4 py-3 ring-1 ring-rh-border/60">
            <p className="text-xs font-medium uppercase tracking-wide text-rh-muted">
              Current step
            </p>
            <p className="mt-1 text-base font-semibold text-rh-ink">
              {isStarting && steps.length === 0
                ? "Initializing workflow…"
                : currentStepLabel(steps)}
            </p>
          </div>
          {state === "error" && error && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-3 text-sm text-rose-900"
            >
              <p className="font-semibold">Run failed</p>
              <p className="mt-1 text-rose-800/90">{error}</p>
            </div>
          )}
        </div>
        <div className="w-full max-w-xs rounded-xl border border-dashed border-rh-border/80 bg-rh-surface/50 p-4 text-xs text-rh-muted md:shrink-0">
          <p className="font-medium text-rh-ink">Live updates</p>
          <p className="mt-2 leading-relaxed">
            Status is polled from{" "}
            <code className="rounded bg-white px-1 py-0.5 font-mono text-[11px] text-rh-ink">
              GET /api/agent/status/:id
            </code>
            . Replace with SSE or WebSocket when your API supports streaming.
          </p>
        </div>
      </div>
    </section>
  );
}
