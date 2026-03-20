import type { RefObject } from "react";

type Line = { id: string; level: string; message: string; timestamp: string };

const levelStyle: Record<string, string> = {
  stdout: "border-l-slate-400 bg-white",
  stderr: "border-l-amber-500 bg-amber-50/40",
  info: "border-l-rh-border bg-rh-surface/50",
  error: "border-l-rose-600 bg-rose-50/60",
};

type Props = {
  logs: Line[];
  logEndRef: RefObject<HTMLDivElement | null>;
};

export function RemediationLogPanel({ logs, logEndRef }: Props) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <h2 className="text-lg font-semibold text-rh-ink">Live agent output</h2>
      <p className="mt-1 text-sm text-rh-muted">
        Raw stdout / stderr from the CLI. Timestamps from the API.
      </p>
      <div className="mt-4 max-h-[420px] overflow-y-auto rounded-xl border border-rh-border/60 bg-rh-surface/30 p-2 font-mono text-xs">
        {logs.length === 0 ? (
          <p className="px-3 py-8 text-center text-rh-muted">
            No output yet. Click Auto Remediate to start.
          </p>
        ) : (
          logs.map((line) => (
            <div
              key={line.id}
              className={`mb-1 border-l-4 px-2 py-1.5 ${levelStyle[line.level] ?? levelStyle.info}`}
            >
              <span className="text-rh-muted/90">{line.timestamp}</span>{" "}
              <span className="font-semibold text-rh-ink">[{line.level}]</span>{" "}
              <span className="whitespace-pre-wrap break-all text-rh-ink">
                {line.message}
              </span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </section>
  );
}
