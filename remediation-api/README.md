# Remediation API

FastAPI service that runs:

```bash
uv run python client-gpt.py server-gpt.py --workflow remediate --approve
```

from the **parent** `basic-mcp` directory and streams structured events over **Server-Sent Events (SSE)**.

## Why SSE?

- One-way server → browser log streaming (no bidirectional chat needed).
- Built into browsers (`EventSource`), simple `text/event-stream` on the server.
- Automatic reconnect is optional later; fewer moving parts than WebSockets.

## Run locally

From repo root:

```bash
cd remediation-api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Or:

```bash
cd remediation-api
uv run python -m app.main
```

## Environment

| Variable | Description |
|----------|-------------|
| `REMEDIATION_PROJECT_ROOT` | Absolute path to `basic-mcp` (parent of `client-gpt.py`). Default: parent of `remediation-api`. |
| `REMEDIATION_API_PORT` | Only used by `python -m app.main` (default `8787`). |

The child process inherits your environment (`KUBECONFIG`, `PATH`, etc.), so the MCP server can reach the cluster the same way as your shell.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/remediation/health` | Liveness |
| `GET` | `/api/remediation/status` | `{ idle, activeSessionId }` |
| `POST` | `/api/remediation/start` | Start run; returns `{ sessionId }` or **409** if already running |
| `GET` | `/api/remediation/stream/{sessionId}` | SSE: JSON events (see frontend `StreamEvent` type) |

## Event protocol (SSE `data:` JSON)

```json
{ "type": "status", "state": "running", "timestamp": "..." }
{ "type": "log", "level": "stdout", "message": "...", "timestamp": "..." }
{ "type": "step", "step": "listing_pods", "status": "in_progress", "timestamp": "..." }
{ "type": "result", "success": true, "exitCode": 0, "summary": "...", "timestamp": "..." }
```

## Concurrency

Only **one** remediation run at a time (global lock). A second `POST /start` returns **409**.
