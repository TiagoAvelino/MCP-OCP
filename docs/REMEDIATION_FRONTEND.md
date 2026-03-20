# Frontend ↔ Remediation API

## Local dev (two terminals)

**Terminal 1 — API**

```bash
cd remediation-api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8787
```

**Terminal 2 — UI**

```bash
cd agent-console
npm install
npm run dev
```

Open http://localhost:5173 — click **Auto Remediate**. Vite proxies `/api/remediation/*` → `http://127.0.0.1:8787`.

## Production / custom API URL

Set in the frontend env:

```bash
VITE_REMEDIATION_API=https://your-api.example.com
```

(Use the origin only; paths `/api/remediation/...` are appended.)

## Flow

1. `POST /api/remediation/start` → `sessionId`
2. `EventSource` → `GET /api/remediation/stream/{sessionId}`
3. UI appends `log` events, updates `status` / `step`, shows `result` at end

Ensure CORS on the API allows your UI origin (edit `remediation-api/app/main.py`).
