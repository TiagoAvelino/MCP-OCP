export function ConsoleHeader() {
  return (
    <header className="border-b border-rh-border/80 bg-white/90 backdrop-blur-sm">
      <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-rh-red/90">
              OpenShift
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-rh-ink md:text-3xl">
              AI Agent Operations Console
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-rh-muted">
              Diagnose and remediate application issues on OpenShift with a guided
              agent workflow. Monitor each stage from discovery through verification.
            </p>
          </div>
          <div className="hidden h-10 w-px bg-rh-border md:block" aria-hidden />
          <div className="text-xs text-rh-muted md:text-right">
            <p className="font-medium text-rh-ink">Internal use</p>
            <p className="mt-0.5">Platform engineering</p>
          </div>
        </div>
      </div>
    </header>
  );
}
