import type { AgentRunResult } from "../types/agent";

export function FinalSummaryCard({ result }: { result: AgentRunResult }) {
  const { state, summary } = result;

  if (state !== "success" || !summary) {
    return null;
  }

  return (
    <section
      className="rounded-2xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50/90 to-white p-6 shadow-card-lg ring-1 ring-emerald-100 md:p-8"
      aria-live="polite"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800/80">
            Final summary
          </p>
          <h2 className="mt-1 text-xl font-semibold text-rh-ink">Run completed</h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-rh-ink/90">
            {summary}
          </p>
        </div>
        <div className="shrink-0 rounded-xl bg-white/80 px-4 py-3 text-xs text-rh-muted shadow-sm ring-1 ring-emerald-100">
          <p className="font-medium text-emerald-900">Outcome</p>
          <ul className="mt-2 space-y-1">
            <li>• Issue identified</li>
            <li>• Corrective action applied</li>
            <li>• Verification passed</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
