import {
  REMEDIATION_STEP_LABELS,
  type RemediationStepStatus,
} from "../types/remediation";

const ORDER = [
  "listing_pods",
  "select_target",
  "reading_logs",
  "identifying_root_cause",
  "applying_env",
  "completed",
];

const dot: Record<RemediationStepStatus | "pending", string> = {
  pending: "bg-slate-200 ring-slate-200/80",
  in_progress: "bg-rh-red ring-red-200 shadow-[0_0_0_4px_rgba(238,0,0,0.12)]",
  completed: "bg-emerald-500 ring-emerald-200",
  failed: "bg-rose-600 ring-rose-200",
};

type Props = {
  steps: Record<string, RemediationStepStatus>;
};

export function RemediationTimeline({ steps }: Props) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <h2 className="text-lg font-semibold text-rh-ink">Remediation timeline</h2>
      <p className="mt-1 text-sm text-rh-muted">
        Steps inferred from agent output (heuristic).
      </p>
      <ol className="relative mt-6 space-y-0">
        {ORDER.map((id, index) => {
          const raw = steps[id] ?? "pending";
          const st = raw in dot ? raw : "pending";
          const isLast = index === ORDER.length - 1;
          const label = REMEDIATION_STEP_LABELS[id] ?? id;
          return (
            <li key={id} className="relative flex gap-4 pb-6 last:pb-0">
              {!isLast && (
                <span
                  className="absolute left-[11px] top-6 h-[calc(100%-12px)] w-px bg-rh-border"
                  aria-hidden
                />
              )}
              <div className="relative z-10 flex shrink-0 flex-col items-center">
                <span
                  className={`size-6 rounded-full ring-2 ${dot[st as keyof typeof dot]}`}
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
