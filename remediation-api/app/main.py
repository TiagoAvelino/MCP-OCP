"""
FastAPI remediation API — SSE stream for live logs from client-gpt remediate workflow.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .runner import run_remediation_job
from .session import RemediationSession


def _cors_allow_origins() -> List[str]:
    """Local dev defaults + optional REMEDIATION_CORS_ORIGINS (comma-separated) for dual-Route setups."""
    origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    extra = os.environ.get("REMEDIATION_CORS_ORIGINS", "")
    for part in extra.split(","):
        o = part.strip()
        if o and o not in origins:
            origins.append(o)
    return origins


app = FastAPI(title="Remediation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id -> session
_sessions: Dict[str, RemediationSession] = {}
_run_lock = asyncio.Lock()
_active_session_id: Optional[str] = None


@app.get("/api/remediation/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/remediation/status")
async def status() -> dict:
    return {
        "idle": _active_session_id is None,
        "activeSessionId": _active_session_id,
    }


@app.post("/api/remediation/start")
async def start_remediation() -> dict:
    global _active_session_id

    async with _run_lock:
        if _active_session_id is not None:
            raise HTTPException(
                status_code=409,
                detail="A remediation run is already in progress. Wait for it to finish or open the stream.",
            )

        session = RemediationSession.new()
        _sessions[session.id] = session
        _active_session_id = session.id

        async def _job() -> None:
            global _active_session_id
            try:
                await run_remediation_job(session)
            finally:
                async with _run_lock:
                    if _active_session_id == session.id:
                        _active_session_id = None

        asyncio.create_task(_job())

    return {"sessionId": session.id}


class RemediationExecuteRequest(BaseModel):
    """
    POST body for explicit execute (production-style contract).
    Require approved=true for mutating runs, or dry_run=true for plan-only.
    """

    approved: bool = Field(
        ...,
        description="Frontend confirmation; must be true to patch the cluster (unless dry_run).",
    )
    dry_run: bool = Field(False, description="If true, list/logs/plan only — no definir_env_deployment.")
    include_openshift_namespaces: bool = False
    allow_system_namespaces: bool = Field(
        False,
        description="If true, allow default and kube-* when auto-selecting pods (openshift-* still needs include_openshift_namespaces).",
    )
    namespace: Optional[str] = Field(None, description="Limit to this namespace")
    pod: Optional[str] = Field(None, description="Target pod name (with namespace)")
    use_llm: bool = Field(False, description="If true, may call LLM when regex finds no env hints")
    model: Optional[str] = Field(None, description="LLM model id (defaults from LLM_MODEL env)")


@app.post("/api/remediation/execute")
async def remediation_execute(body: RemediationExecuteRequest) -> dict:
    """
    Starts the same SSE session flow as /start, but only after explicit approval in the body.
    The worker runs remediation in-process (MCP tool handlers), not uv run.
    """
    global _active_session_id

    if not body.approved and not body.dry_run:
        raise HTTPException(
            status_code=422,
            detail="Set approved=true to allow cluster writes, or dry_run=true for plan-only.",
        )

    async with _run_lock:
        if _active_session_id is not None:
            raise HTTPException(
                status_code=409,
                detail="A remediation run is already in progress.",
            )

        session = RemediationSession.new()
        _sessions[session.id] = session
        _active_session_id = session.id

        async def _job() -> None:
            global _active_session_id
            try:
                await _run_execute_payload(session, body)
            finally:
                async with _run_lock:
                    if _active_session_id == session.id:
                        _active_session_id = None

        asyncio.create_task(_job())

    return {"sessionId": session.id, "message": "Remediation started; subscribe to stream for logs."}


async def _run_execute_payload(session: RemediationSession, body: RemediationExecuteRequest) -> None:
    from datetime import datetime, timezone

    from .runner import _log, _maybe_step_from_line, _ts
    from .services.remediation_runner import execute_remediation_in_process

    await session.append_event({"type": "status", "state": "running", "timestamp": _ts()})
    await session.append_event(
        {
            "type": "step",
            "step": "listing_pods",
            "status": "in_progress",
            "message": "POST /execute — in-process remediation",
            "timestamp": _ts(),
        }
    )

    async def emit(msg: str) -> None:
        await _log(session, "info", msg)
        await _maybe_step_from_line(session, msg)

    try:
        result = await execute_remediation_in_process(
            approve=body.approved,
            dry_run=body.dry_run,
            include_openshift_namespaces=body.include_openshift_namespaces,
            allow_system_namespaces=body.allow_system_namespaces,
            remediate_namespace=body.namespace,
            remediate_pod=body.pod,
            remediate_use_llm=body.use_llm,
            model=body.model,
            emit=emit,
        )
    except Exception as e:
        await _log(session, "error", f"{type(e).__name__}: {e}")
        await session.append_event(
            {
                "type": "result",
                "success": False,
                "exitCode": -1,
                "summary": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        session.mark_done(False, -1)
        await session.append_event(
            {"type": "status", "state": "error", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        return

    success = result.success
    exit_code = 0 if success else 1
    summary = result.summary
    ts = datetime.now(timezone.utc).isoformat()

    await session.append_event(
        {
            "type": "step",
            "step": "completed",
            "status": "completed" if success else "failed",
            "message": summary[:500],
            "timestamp": ts,
        }
    )
    await session.append_event(
        {
            "type": "result",
            "success": success,
            "exitCode": exit_code,
            "summary": summary,
            "timestamp": ts,
        }
    )
    session.mark_done(success, exit_code)
    await session.append_event(
        {"type": "status", "state": "success" if success else "error", "timestamp": ts}
    )


async def _sse_generator(session_id: str) -> AsyncGenerator[str, None]:
    session = _sessions.get(session_id)
    if session is None:
        yield f"data: {json.dumps({'type': 'log', 'level': 'error', 'message': 'Unknown session', 'timestamp': ''})}\n\n"
        return

    idx = 0
    while True:
        chunk, total = await session.snapshot_events(idx)
        idx = total
        for ev in chunk:
            yield f"data: {json.dumps(ev)}\n\n"
        if session.completed and not chunk:
            break
        await asyncio.sleep(0.08)


@app.get("/api/remediation/stream/{session_id}")
async def stream(session_id: str) -> StreamingResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        _sse_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(__import__("os").environ.get("REMEDIATION_API_PORT", "8787")),
        reload=False,
    )


if __name__ == "__main__":
    main()
