import type { AgentStep, AgentStepStatus } from "../types/agent";

const dotStyles: Record<AgentStepStatus, string> = {
  pending: "bg-slate-200 ring-slate-200/80",
  in_progress: "bg-rh-red ring-red-200 shadow-[0_0_0_4px_rgba(238,0,0,0.12)]",
  completed: "bg-emerald-500 ring-emerald-200",
  failed: "bg-rose-600 ring-rose-200",
};

const labelStyles: Record<AgentStepStatus, string> = {
  pending: "text-rh-muted",
  in_progress: "text-rh-ink font-semibold",
  completed: "text-rh-ink",
  failed: "text-rose-900 font-semibold",
};

export function StepTimeline({ steps }: { steps: AgentStep[] }) {
  if (steps.length === 0) {
    return (
      <div className="rounded-2xl border border-rh-border/60 bg-rh-surface/40 px-6 py-10 text-center text-sm text-rh-muted">
        No steps yet. Start a troubleshooting run to populate the timeline.
      </div>
    );
  }

  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <h2 className="text-lg font-semibold text-rh-ink">Progress timeline</h2>
      <p className="mt-1 text-sm text-rh-muted">
        Stages advance as the agent completes each phase.
      </p>
      <ol className="relative mt-8 space-y-0">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          return (
            <li key={step.id} className="relative flex gap-4 pb-8 last:pb-0">
              {!isLast && (
                <span
                  className="absolute left-[11px] top-6 h-[calc(100%-12px)] w-px bg-rh-border"
                  aria-hidden
                />
              )}
              <div className="relative z-10 flex shrink-0 flex-col items-center">
                <span
                  className={`size-6 rounded-full ring-2 ${dotStyles[step.status]}`}
                  aria-hidden
                />
              </div>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className={`text-sm ${labelStyles[step.status]}`}>{step.label}</p>
                {step.message && (
                  <p className="mt-1 text-xs text-rh-muted">{step.message}</p>
                )}
                {step.timestamp && (
                  <p className="mt-1 font-mono text-[11px] text-rh-muted/90">
                    {step.timestamp}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
