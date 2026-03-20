import {
  REMEDIATION_STEP_LABELS,
  REMEDIATION_STEP_ORDER,
  type RemediationRunState,
  type RemediationStepStatus,
} from "../types/remediation";

const dot: Record<RemediationStepStatus | "pending", string> = {
  pending: "bg-slate-200 ring-slate-200/80",
  in_progress:
    "bg-amber-400 ring-amber-200 shadow-[0_0_0_4px_rgba(251,191,36,0.2)]",
  completed: "bg-emerald-500 ring-emerald-200/80",
  failed: "bg-rose-600 ring-rose-200",
};

function connectorClass(
  steps: Record<string, RemediationStepStatus | "pending" | undefined>,
  currentId: string,
  nextId: string,
  runState: RemediationRunState,
): string {
  const a = steps[currentId] ?? "pending";
  const b = steps[nextId] ?? "pending";
  if (a === "failed" || b === "failed") return "bg-rose-300";
  if (a === "completed" && b === "completed") {
    return runState === "success"
      ? "bg-emerald-300"
      : "bg-emerald-200/90";
  }
  if (a === "completed" && b === "in_progress") return "bg-emerald-200/70";
  return "bg-rh-border";
}

type Props = {
  steps: Record<string, RemediationStepStatus | "pending">;
  runState: RemediationRunState;
};

export function RemediationTimeline({ steps, runState }: Props) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <h2 className="text-lg font-semibold text-rh-ink">Remediation timeline</h2>
      <p className="mt-1 text-sm text-rh-muted">
        Steps inferred from agent output (heuristic). Green = done, amber = in
        progress, red = failed.
      </p>
      <ol className="relative mt-6 space-y-0">
        {REMEDIATION_STEP_ORDER.map((id, index) => {
          const raw = steps[id] ?? "pending";
          const st = raw in dot ? raw : "pending";
          const isLast = index === REMEDIATION_STEP_ORDER.length - 1;
          const label = REMEDIATION_STEP_LABELS[id] ?? id;
          const nextId = !isLast ? REMEDIATION_STEP_ORDER[index + 1] : null;
          return (
            <li key={id} className="relative flex gap-4 pb-6 last:pb-0">
              {!isLast && nextId && (
                <span
                  className={`absolute left-[11px] top-6 h-[calc(100%-12px)] w-px ${connectorClass(steps, id, nextId, runState)}`}
                  aria-hidden
                />
              )}
              <div className="relative z-10 flex shrink-0 flex-col items-center">
                <span
                  className={`size-6 rounded-full ring-2 ${dot[st]}`}
                  aria-hidden
                />
              </div>
              <div className="min-w-0 pt-0.5">
                <p className="text-sm font-medium text-rh-ink">{label}</p>
                <p className="text-xs uppercase tracking-wide text-rh-muted">
                  {st.replace("_", " ")}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
