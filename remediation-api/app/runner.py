"""
Runs `uv run python client-gpt.py server-gpt.py --workflow remediate --approve`
and maps stdout/stderr lines to stream events + heuristic step updates.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from .services.remediation_runner import execute_remediation_in_process
from .session import RemediationSession

_STEP_HINTS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"listar_pods|Raw listing|problem status filter", re.I), "listing_pods"),
    (re.compile(r"Selected pod|Inferred Deployment", re.I), "select_target"),
    (re.compile(r"Pod logs|--- Pod logs|--- End logs", re.I), "reading_logs"),
    (re.compile(r"Planned env patch|regex|LLM env", re.I), "identifying_root_cause"),
    (re.compile(r"definir_env|Remediation result|Env vars set on Deployment", re.I), "applying_env"),
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _log(session: RemediationSession, level: str, message: str) -> None:
    await session.append_event(
        {"type": "log", "level": level, "message": message, "timestamp": _ts()}
    )


async def _maybe_step_from_line(session: RemediationSession, line: str) -> None:
    for pattern, step_id in _STEP_HINTS:
        if pattern.search(line):
            await session.append_event(
                {
                    "type": "step",
                    "step": step_id,
                    "status": "in_progress",
                    "message": line[:240],
                    "timestamp": _ts(),
                }
            )
            break


def _use_subprocess() -> bool:
    return os.environ.get("REMEDIATION_USE_SUBPROCESS", "").lower() in ("1", "true", "yes")


async def run_remediation_in_process_session(session: RemediationSession) -> None:
    """Production path: shared remediation_workflow + openshift_tool_handlers in-process."""
    await session.append_event({"type": "status", "state": "running", "timestamp": _ts()})
    await session.append_event(
        {
            "type": "step",
            "step": "listing_pods",
            "status": "in_progress",
            "message": "Starting in-process remediation (MCP tool handlers)…",
            "timestamp": _ts(),
        }
    )
    await _log(session, "info", "Executor: in-process (no uv run)")

    async def emit(msg: str) -> None:
        await _log(session, "info", msg)
        await _maybe_step_from_line(session, msg)

    try:
        result = await execute_remediation_in_process(
            approve=True,
            dry_run=False,
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
                "timestamp": _ts(),
            }
        )
        session.mark_done(False, -1)
        await session.append_event({"type": "status", "state": "error", "timestamp": _ts()})
        return

    success = result.success
    exit_code = 0 if success else 1
    summary = result.summary

    await session.append_event(
        {
            "type": "step",
            "step": "completed",
            "status": "completed" if success else "failed",
            "message": summary[:500],
            "timestamp": _ts(),
        }
    )
    await session.append_event(
        {
            "type": "result",
            "success": success,
            "exitCode": exit_code,
            "summary": summary,
            "timestamp": _ts(),
        }
    )
    session.mark_done(success, exit_code)
    await session.append_event(
        {"type": "status", "state": "success" if success else "error", "timestamp": _ts()}
    )


async def run_remediation_subprocess(session: RemediationSession) -> None:
    project_root = os.environ.get(
        "REMEDIATION_PROJECT_ROOT",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    )

    await session.append_event({"type": "status", "state": "running", "timestamp": _ts()})
    await session.append_event(
        {
            "type": "step",
            "step": "listing_pods",
            "status": "in_progress",
            "message": "Starting remediation CLI…",
            "timestamp": _ts(),
        }
    )

    cmd = [
        "uv",
        "run",
        "python",
        "client-gpt.py",
        "server-gpt.py",
        "--workflow",
        "remediate",
        "--approve",
    ]

    await _log(session, "info", f"$ cd {project_root} && {' '.join(cmd)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
    except Exception as e:
        await _log(session, "error", f"Failed to spawn process: {e}")
        await session.append_event(
            {
                "type": "result",
                "success": False,
                "exitCode": -1,
                "summary": str(e),
                "timestamp": _ts(),
            }
        )
        session.mark_done(False, -1)
        await session.append_event({"type": "status", "state": "error", "timestamp": _ts()})
        return

    async def pump(stream: asyncio.StreamReader, level: str) -> None:
        while True:
            line_b = await stream.readline()
            if not line_b:
                break
            text = line_b.decode(errors="replace").rstrip("\n\r")
            await _log(session, level, text)
            await _maybe_step_from_line(session, text)

    await asyncio.gather(
        pump(proc.stdout, "stdout"),
        pump(proc.stderr, "stderr"),
    )
    exit_code = await proc.wait()

    success = exit_code == 0
    summary = (
        "Remediation finished successfully."
        if success
        else f"Remediation exited with code {exit_code}. Check logs above."
    )

    await session.append_event(
        {
            "type": "step",
            "step": "completed",
            "status": "completed" if success else "failed",
            "message": summary,
            "timestamp": _ts(),
        }
    )
    await session.append_event(
        {
            "type": "result",
            "success": success,
            "exitCode": exit_code,
            "summary": summary,
            "timestamp": _ts(),
        }
    )
    session.mark_done(success, exit_code)
    await session.append_event(
        {"type": "status", "state": "success" if success else "error", "timestamp": _ts()}
    )


async def run_remediation_job(session: RemediationSession) -> None:
    """Default: in-process. Set REMEDIATION_USE_SUBPROCESS=1 for legacy uv-run CLI."""
    if _use_subprocess():
        await run_remediation_subprocess(session)
    else:
        await run_remediation_in_process_session(session)
