const API_PREFIX =
  import.meta.env.VITE_REMEDIATION_API?.replace(/\/$/, "") ?? "";

export function remediationUrl(path: string): string {
  if (API_PREFIX) {
    return `${API_PREFIX}${path}`;
  }
  return path;
}

export async function startRemediation(): Promise<{ sessionId: string }> {
  const res = await fetch(remediationUrl("/api/remediation/start"), {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (res.status === 409) {
    throw new Error(
      "A remediation is already running. Wait for it to finish or refresh status.",
    );
  }
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Start failed: ${res.status}`);
  }
  return res.json() as Promise<{ sessionId: string }>;
}

export async function fetchRemediationStatus(): Promise<{
  idle: boolean;
  activeSessionId: string | null;
}> {
  const res = await fetch(remediationUrl("/api/remediation/status"));
  if (!res.ok) throw new Error("Status request failed");
  return res.json();
}

export function openRemediationStream(
  sessionId: string,
  onEvent: (data: unknown) => void,
  onError: () => void,
): EventSource {
  const url = remediationUrl(`/api/remediation/stream/${sessionId}`);
  const es = new EventSource(url);
  es.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data));
    } catch {
      onEvent({
        type: "log",
        level: "error",
        message: `Invalid SSE payload: ${ev.data}`,
        timestamp: new Date().toISOString(),
      });
    }
  };
  es.onerror = () => {
    onError();
    es.close();
  };
  return es;
}
