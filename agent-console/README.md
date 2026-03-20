# AI Agent Operations Console

Minimal, enterprise-style React UI for an OpenShift troubleshooting agent.

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS (subtle Red Hat–inspired palette in `tailwind.config.js`)

## Run locally

**Remediation API + UI**

Terminal 1 — FastAPI streamer (repo root’s sibling `remediation-api`):

```bash
cd ../remediation-api   # from agent-console: ../remediation-api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Terminal 2 — Vite:

```bash
cd agent-console
npm install
npm run dev
```

Open http://localhost:5173 — use **Auto Remediate** (proxies to `:8787`). See `../docs/REMEDIATION_FRONTEND.md`.

**Demo only (mock polling)**

```bash
cd agent-console
npm install
npm run dev
```

Open http://localhost:5173 — expand “Mock agent demo”.

## Backend integration

| Variable | Purpose |
|----------|---------|
| `VITE_USE_MOCK` | Default mock on. Set to `false` for live API. |
| `VITE_API_BASE` | Origin for mock agent API (optional). |
| `VITE_REMEDIATION_API` | Origin for remediation API. Empty = use Vite proxy `/api/remediation` → `8787`. |

Expected contract:

- **Remediation:** `POST /api/remediation/execute` (JSON body with `approved`, optional `dry_run`, …) → `{ sessionId }`, then SSE `GET /api/remediation/stream/:sessionId`.
- **Mock agent:** `POST /api/agent/run` → `{ "id": string }`
- `GET /api/agent/status/:id` → `AgentRunResult` (see `src/types/agent.ts`)

Vite proxies `/api` to `http://localhost:8080` in dev (`vite.config.ts`). Point `target` at your server or remove proxy and use `VITE_API_BASE`.

## Mock demo

With mock mode, each poll advances the workflow. To simulate a verification failure once:

```js
window.__agentFailNext = true;
```

Then click **Run AI Troubleshooting** and wait until the verify step.

## Structure

```
src/
  types/agent.ts          # Shared types
  services/agentApi.ts    # startAgentRun / getAgentStatus (+ mock)
  hooks/useAgentRun.ts     # Polling orchestration
  components/              # Header, actions, timeline, log, summary
  pages/AgentConsolePage.tsx
```
