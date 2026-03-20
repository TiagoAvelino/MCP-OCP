type Props = {
  result: { success: boolean; exitCode: number; summary: string } | null;
  runState: "idle" | "running" | "success" | "error";
};

export function RemediationSummary({ result, runState }: Props) {
  if (!result && runState !== "success" && runState !== "error") {
    return null;
  }

  const ok = result?.success ?? false;

  return (
    <section
      className={`rounded-2xl border p-6 shadow-card md:p-8 ${
        ok
          ? "border-emerald-200/80 bg-gradient-to-br from-emerald-50/90 to-white ring-1 ring-emerald-100"
          : "border-rose-200/80 bg-gradient-to-br from-rose-50/80 to-white ring-1 ring-rose-100"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-rh-muted">
        Final result
      </p>
      <h2 className="mt-1 text-xl font-semibold text-rh-ink">
        {ok ? "Success" : "Failed or incomplete"}
      </h2>
      {result && (
        <>
          <p className="mt-2 text-sm leading-relaxed text-rh-ink/90">
            {result.summary}
          </p>
          <p className="mt-3 font-mono text-xs text-rh-muted">
            Exit code: <span className="text-rh-ink">{result.exitCode}</span>
          </p>
        </>
      )}
    </section>
  );
}
