import { AgentActivityLog } from "../components/AgentActivityLog";
import { ConsoleHeader } from "../components/ConsoleHeader";
import { ExecutionStatusPanel } from "../components/ExecutionStatusPanel";
import { FinalSummaryCard } from "../components/FinalSummaryCard";
import { PrimaryAction } from "../components/PrimaryAction";
import { RemediationAction } from "../components/RemediationAction";
import { RemediationLogPanel } from "../components/RemediationLogPanel";
import { RemediationStatusBar } from "../components/RemediationStatusBar";
import { RemediationSummary } from "../components/RemediationSummary";
import { RemediationTimeline } from "../components/RemediationTimeline";
import { StepTimeline } from "../components/StepTimeline";
import { useAgentRun } from "../hooks/useAgentRun";
import { useRemediationStream } from "../hooks/useRemediationStream";
import { USE_MOCK } from "../services/agentApi";

export function AgentConsolePage() {
  const demo = useAgentRun();
  const remediation = useRemediationStream();

  return (
    <div className="min-h-screen bg-rh-surface text-rh-ink">
      <ConsoleHeader />

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-10 md:px-10 md:py-12">
        <RemediationAction
          onStart={() => void remediation.start()}
          disabled={remediation.isRunning}
          isStarting={remediation.isRunning}
        />

        <RemediationStatusBar
          state={remediation.runState}
          sessionId={remediation.sessionId}
          errorMessage={remediation.errorMessage}
        />

        <div className="grid gap-8 lg:grid-cols-2">
          <RemediationTimeline steps={remediation.steps} />
          <RemediationLogPanel
            logs={remediation.logs}
            logEndRef={remediation.logEndRef}
          />
        </div>

        <RemediationSummary
          result={remediation.result}
          runState={remediation.runState}
        />

        <div className="flex justify-end">
          <button
            type="button"
            onClick={remediation.reset}
            className="rounded-lg border border-rh-border bg-white px-4 py-2 text-sm font-medium text-rh-ink shadow-sm transition hover:bg-rh-surface"
          >
            Clear remediation view
          </button>
        </div>

        <details className="group rounded-2xl border border-dashed border-rh-border/80 bg-white/50 p-4">
          <summary className="cursor-pointer text-sm font-medium text-rh-muted group-open:text-rh-ink">
            Mock agent demo (polling simulation)
          </summary>
          <div className="mt-8 space-y-8 border-t border-rh-border/60 pt-8">
            <PrimaryAction
              onRun={demo.startRun}
              disabled={demo.isRunning}
              isStarting={demo.isStarting}
            />
            <ExecutionStatusPanel
              result={demo.result}
              runId={demo.runId}
              isStarting={demo.isStarting}
            />
            <div className="grid gap-8 lg:grid-cols-2">
              <StepTimeline steps={demo.result.steps} />
              <AgentActivityLog logs={demo.result.logs} />
            </div>
            <FinalSummaryCard result={demo.result} />
            <button
              type="button"
              onClick={demo.reset}
              className="rounded-lg border border-rh-border bg-white px-4 py-2 text-sm font-medium text-rh-ink shadow-sm"
            >
              Clear demo session
            </button>
          </div>
        </details>

        <footer className="flex flex-col gap-4 border-t border-rh-border/80 pt-8 text-sm text-rh-muted md:flex-row md:items-center md:justify-between">
          <div>
            <p>
              Demo backend:{" "}
              <span className="font-medium text-rh-ink">
                {USE_MOCK ? "Mock" : "Live API"}
              </span>
              {" · "}
              Remediation API:{" "}
              <code className="rounded bg-white px-1 font-mono text-xs">
                uvicorn on :8787
              </code>{" "}
              (proxied from Vite as{" "}
              <code className="rounded bg-white px-1 font-mono text-xs">
                /api/remediation
              </code>
              )
            </p>
            <p className="mt-1 text-xs">
              <code className="rounded bg-white px-1 py-0.5 font-mono text-[11px]">
                VITE_REMEDIATION_API
              </code>{" "}
              overrides proxy (e.g. production origin).
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
