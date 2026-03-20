# Production backend: MCP + remediation (no `uv run`)

## Goals

- **HTTP API** (FastAPI) receives an explicit **approval** from the frontend.
- **Orchestration** runs **inside the API process** (no subprocess, no `uv run`).
- **Tool execution** uses the **same MCP tool contract** (names + JSON args) as `server-gpt.py`, implemented by shared Python callables.
- **Optional**: keep a **stdio MCP server** (`server-gpt.py`) for Cursor / external MCP clients.

## Architecture (layers)

```
┌─────────────────────────────────────────────────────────────┐
│  HTTP: FastAPI routes (CORS, auth, request validation)       │
│  POST /api/remediation/execute { approved, dry_run, ... }   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Orchestration: remediation_workflow.run_crashloop_*         │
│  (select pod, logs, infer env, safety gates)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ ToolCaller.call_tool(name, args)
┌───────────────────────────▼─────────────────────────────────┐
│  Tool layer                                                  │
│  • In-process: openshift_tool_handlers.MCP_TOOL_DISPATCH    │
│  • Or stdio MCP: FastMcpToolCaller → fastmcp.Client           │
└─────────────────────────────────────────────────────────────┘
```

### Why this satisfies “use MCP”

- **MCP tool surface** (`listar_pods_em_erro_cluster`, `ver_logs_pod`, `definir_env_deployment`, …) is the **contract** between orchestration and the cluster.
- `server-gpt.py` **registers** those tools with FastMCP for **stdio** clients.
- The API uses **`InProcessOpenShiftToolCaller`**, which dispatches the **same names/args** to the **same functions** — no second copy of business logic.

### Alternative: MCP over HTTP (sidecar)

For strict JSON-RPC MCP over the network, run a **dedicated MCP server** with **streamable HTTP** (or SSE) in another deployment, and implement `ToolCaller` with an HTTP MCP client. The API process then does not import `kubernetes` directly; it only speaks MCP. Trade-off: extra service + auth between API and MCP.

## Repository layout (this project)

| Path | Role |
|------|------|
| `openshift_tool_handlers.py` | K8s/OpenShift operations + `MCP_TOOL_DISPATCH` |
| `server-gpt.py` | FastMCP stdio server; thin wrappers over handlers |
| `remediation_workflow.py` | CrashLoop remediation orchestration + `ToolCaller` protocol |
| `client-gpt.py` | CLI: stdio MCP via `FastMcpToolCaller` |
| `remediation-api/app/` | FastAPI + SSE; in-process runner |

## Configuration

| Variable | Purpose |
|----------|---------|
| `REMEDIATION_PROJECT_ROOT` | Absolute path to **basic-mcp** repo root (for imports if layout changes) |
| `REMEDIATION_USE_SUBPROCESS` | Set `1` to restore legacy `uv run python client-gpt.py …` |
| `KUBECONFIG` / in-cluster SA | Same as today for `kubernetes` client |

## FastAPI usage

1. `POST /api/remediation/execute` with JSON body (see OpenAPI / `RemediationExecuteRequest`).
2. Response includes `sessionId`.
3. `GET /api/remediation/stream/{sessionId}` for SSE log events.

Example body (mutating):

```json
{
  "approved": true,
  "dry_run": false,
  "include_openshift_namespaces": false,
  "namespace": "app-project",
  "pod": null,
  "use_llm": false
}
```

Plan-only:

```json
{ "approved": false, "dry_run": true }
```

## Production deployment notes

- Run **one active remediation** at a time (current lock), or move to a **task queue** (Celery, RQ, Arq) + worker replicas for scale-out.
- **Kube RBAC**: bind a ServiceAccount with least privilege (list pods cluster-wide, get logs, patch deployments in allowed namespaces).
- **Secrets**: mount LLM tokens via Kubernetes secrets, not env in images.
- **Observability**: structured logging around each `call_tool` (name, duration, namespace).
