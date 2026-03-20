import { useCallback, useEffect, useRef, useState } from "react";
import { getAgentStatus, startAgentRun } from "../services/agentApi";
import type { AgentRunResult, AgentRunState } from "../types/agent";

const POLL_MS = 900;

const emptyResult = (state: AgentRunState = "idle"): AgentRunResult => ({
  state,
  steps: [],
  logs: [],
});

export function useAgentRun() {
  const [result, setResult] = useState<AgentRunResult>(() => emptyResult());
  const [runId, setRunId] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(async (id: string) => {
    try {
      const next = await getAgentStatus(id);
      setResult(next);
      if (next.state === "success" || next.state === "error") {
        stopPolling();
      }
    } catch (e) {
      stopPolling();
      setResult({
        state: "error",
        steps: [],
        logs: [
          {
            id: crypto.randomUUID(),
            level: "error",
            message: e instanceof Error ? e.message : "Status poll failed",
            timestamp: new Date().toISOString(),
          },
        ],
        error: e instanceof Error ? e.message : "Unknown error",
      });
    }
  }, [stopPolling]);

  const startRun = useCallback(async () => {
    if (isStarting || result.state === "running") return;
    stopPolling();
    setIsStarting(true);
    setResult(emptyResult("running"));
    try {
      const { id } = await startAgentRun();
      setRunId(id);
      await pollOnce(id);
      pollRef.current = setInterval(() => {
        void pollOnce(id);
      }, POLL_MS);
    } catch (e) {
      setResult({
        state: "error",
        steps: [],
        logs: [
          {
            id: crypto.randomUUID(),
            level: "error",
            message: e instanceof Error ? e.message : "Failed to start run",
            timestamp: new Date().toISOString(),
          },
        ],
        error: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setIsStarting(false);
    }
  }, [isStarting, pollOnce, result.state, stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setRunId(null);
    setResult(emptyResult());
  }, [stopPolling]);

  return {
    result,
    runId,
    isStarting,
    startRun,
    reset,
    isRunning: result.state === "running" || isStarting,
  };
}
