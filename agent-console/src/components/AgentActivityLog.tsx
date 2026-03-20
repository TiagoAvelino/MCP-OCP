import type { AgentLogEntry } from "../types/agent";

const rowStyles: Record<AgentLogEntry["level"], string> = {
  info: "border-l-rh-border bg-white",
  success: "border-l-emerald-500 bg-emerald-50/40",
  warning: "border-l-amber-500 bg-amber-50/50",
  error: "border-l-rose-600 bg-rose-50/60",
};

const badgeStyles: Record<AgentLogEntry["level"], string> = {
  info: "bg-slate-100 text-slate-700",
  success: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-900",
  error: "bg-rose-100 text-rose-900",
};

export function AgentActivityLog({ logs }: { logs: AgentLogEntry[] }) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <h2 className="text-lg font-semibold text-rh-ink">Agent activity log</h2>
      <p className="mt-1 text-sm text-rh-muted">
        Structured messages from the agent and platform integrations.
      </p>
      <div className="mt-6 max-h-[320px] space-y-2 overflow-y-auto rounded-xl border border-rh-border/60 bg-rh-surface/30 p-2">
        {logs.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-rh-muted">
            Log output will appear here during execution.
          </p>
        ) : (
          logs.map((entry) => (
            <article
              key={entry.id}
              className={`rounded-lg border-l-4 px-3 py-2.5 shadow-sm ${rowStyles[entry.level]}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${badgeStyles[entry.level]}`}
                >
                  {entry.level}
                </span>
                <time className="font-mono text-[11px] text-rh-muted">
                  {entry.timestamp}
                </time>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-rh-ink">
                {entry.message}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
