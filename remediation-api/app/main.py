"""
FastAPI remediation API — SSE stream for live logs from client-gpt remediate workflow.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .runner import run_remediation_subprocess
from .session import RemediationSession

app = FastAPI(title="Remediation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
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
                await run_remediation_subprocess(session)
            finally:
                async with _run_lock:
                    if _active_session_id == session.id:
                        _active_session_id = None

        asyncio.create_task(_job())

    return {"sessionId": session.id}


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
