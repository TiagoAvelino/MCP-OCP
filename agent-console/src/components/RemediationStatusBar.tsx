import type { RemediationRunState } from "../types/remediation";
import { StatusBadge } from "./StatusBadge";

const map: Record<
  RemediationRunState,
  "idle" | "running" | "success" | "error"
> = {
  idle: "idle",
  running: "running",
  success: "success",
  error: "error",
};

type Props = {
  state: RemediationRunState;
  sessionId: string | null;
  errorMessage: string | null;
};

export function RemediationStatusBar({
  state,
  sessionId,
  errorMessage,
}: Props) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold text-rh-ink">Remediation status</h2>
        <StatusBadge state={map[state]} />
      </div>
      {sessionId && (
        <p className="mt-3 font-mono text-xs text-rh-muted">
          Session: <span className="text-rh-ink">{sessionId}</span>
        </p>
      )}
      {errorMessage && (
        <p
          className="mt-3 rounded-lg border border-rose-200 bg-rose-50/80 px-3 py-2 text-sm text-rose-900"
          role="alert"
        >
          {errorMessage}
        </p>
      )}
    </section>
  );
}
