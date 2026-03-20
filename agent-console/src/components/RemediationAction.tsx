type Props = {
  onStart: () => void;
  disabled: boolean;
  isStarting: boolean;
};

export function RemediationAction({ onStart, disabled, isStarting }: Props) {
  return (
    <section className="rounded-2xl border border-rh-border/70 bg-rh-card p-6 shadow-card md:p-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-rh-ink">Live remediation</h2>
          <p className="mt-1 text-sm text-rh-muted">
            Runs{" "}
            <code className="rounded bg-rh-surface px-1.5 py-0.5 font-mono text-xs">
              client-gpt.py --workflow remediate --approve
            </code>{" "}
            on the API server. Logs stream via SSE.
          </p>
        </div>
        <button
          type="button"
          onClick={onStart}
          disabled={disabled}
          className="inline-flex min-h-[44px] min-w-[200px] items-center justify-center gap-2 rounded-xl bg-rh-red px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-rh-red-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rh-red disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isStarting || disabled ? (
            <>
              <span
                className="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                aria-hidden
              />
              Running…
            </>
          ) : (
            "Auto Remediate"
          )}
        </button>
      </div>
    </section>
  );
}
