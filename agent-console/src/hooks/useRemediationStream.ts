import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchRemediationStatus,
  openRemediationStream,
  startRemediation,
} from "../services/remediationApi";
import type { RemediationRunState, StreamEvent } from "../types/remediation";

type StepMap = Record<string, "pending" | "in_progress" | "completed" | "failed">;

function reduceStepMap(prev: StepMap, ev: StreamEvent): StepMap {
  if (ev.type !== "step") return prev;
  return { ...prev, [ev.step]: ev.status };
}

export function useRemediationStream() {
  const [runState, setRunState] = useState<RemediationRunState>("idle");
  const [logs, setLogs] = useState<
    { id: string; level: string; message: string; timestamp: string }[]
  >([]);
  const [steps, setSteps] = useState<StepMap>({});
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<{
    success: boolean;
    exitCode: number;
    summary: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const finishedRef = useRef(false);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  const stopStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => () => stopStream(), [stopStream]);

  const appendLog = useCallback(
    (level: string, message: string, timestamp: string) => {
      setLogs((L) => [
        ...L,
        { id: crypto.randomUUID(), level, message, timestamp },
      ]);
    },
    [],
  );

  const handleEvent = useCallback(
    (raw: unknown) => {
      const ev = raw as StreamEvent;
      if (!ev || typeof ev !== "object" || !("type" in ev)) return;
      switch (ev.type) {
        case "status":
          setRunState(ev.state);
          break;
        case "log":
          appendLog(ev.level, ev.message, ev.timestamp);
          break;
        case "step":
          setSteps((s) => reduceStepMap(s, ev));
          break;
        case "result":
          setResult({
            success: ev.success,
            exitCode: ev.exitCode,
            summary: ev.summary,
          });
          finishedRef.current = true;
          if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
          }
          break;
        default:
          break;
      }
    },
    [appendLog],
  );

  const start = useCallback(async () => {
    if (runState === "running") return;
    stopStream();
    finishedRef.current = false;
    setErrorMessage(null);
    setResult(null);
    setLogs([]);
    setSteps({});
    setRunState("running");
    setSessionId(null);

    try {
      const { sessionId: sid } = await startRemediation();
      setSessionId(sid);
      const es = openRemediationStream(
        sid,
        handleEvent,
        () => {
          if (!finishedRef.current) {
            setRunState((r) => (r === "running" ? "error" : r));
            appendLog(
              "error",
              "SSE connection closed before completion",
              new Date().toISOString(),
            );
          }
          stopStream();
        },
      );
      esRef.current = es;
    } catch (e) {
      setRunState("error");
      setErrorMessage(e instanceof Error ? e.message : String(e));
      appendLog(
        "error",
        e instanceof Error ? e.message : String(e),
        new Date().toISOString(),
      );
    }
  }, [appendLog, handleEvent, runState, stopStream]);

  const reset = useCallback(() => {
    stopStream();
    finishedRef.current = false;
    setRunState("idle");
    setLogs([]);
    setSteps({});
    setSessionId(null);
    setResult(null);
    setErrorMessage(null);
  }, [stopStream]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    void fetchRemediationStatus().catch(() => {});
  }, []);

  return {
    runState,
    logs,
    steps,
    sessionId,
    result,
    errorMessage,
    isRunning: runState === "running",
    start,
    reset,
    logEndRef,
  };
}
