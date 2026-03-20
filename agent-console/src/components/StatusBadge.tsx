import type { AgentRunState } from "../types/agent";

const styles: Record<AgentRunState, string> = {
  idle:
    "bg-slate-100 text-slate-600 ring-1 ring-slate-200/80",
  running:
    "bg-red-50 text-rh-red-muted ring-1 ring-red-200/60",
  success:
    "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/70",
  error:
    "bg-rose-50 text-rose-900 ring-1 ring-rose-200/80",
};

const labels: Record<AgentRunState, string> = {
  idle: "Idle",
  running: "Running",
  success: "Success",
  error: "Error",
};

export function StatusBadge({ state }: { state: AgentRunState }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${styles[state]}`}
    >
      {state === "running" && (
        <span
          className="size-1.5 animate-pulse rounded-full bg-rh-red"
          aria-hidden
        />
      )}
      {labels[state]}
    </span>
  );
}
