# MCP Client Usage Guide

## How to Run the MCP Client

The client (`client-gpt.py`) connects to your MCP server (`server-gpt.py`) and uses your custom LLM endpoint to coordinate operations.

### Prerequisites

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Set your API key** (optional - only if your endpoint requires authentication):
   - Environment variable: `export OPENAI_API_KEY=your-api-key-here`
   - Or for Granite on OpenShift: `export GRANITE_API_TOKEN=...` and `export GRANITE_API_BASE=...`
   - Command-line: `--api-key your-api-key-here` or `--api-key-file ./granite.token` (file contains one line: the JWT)
   - If your endpoint doesn't require auth, you can skip this

### Running the Client with Granite 8b (OpenShift route + SA token)

Use your inference **route** as the OpenAI-compatible base URL and the **service account JWT** as the bearer token. **Do not commit the token**; use env vars or a gitignored file.

```bash
export GRANITE_API_BASE="https://granite-8b-app-project.apps.cluster-x2gqr.x2gqr.sandbox1293.opentlc.com"
export GRANITE_API_TOKEN="YOUR_JWT_HERE"
export LLM_MODEL="granite-8b"   # optional; default is granite-8b if unset

uv run python client-gpt.py server-gpt.py
```

Or with explicit flags:

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base "https://granite-8b-app-project.apps.cluster-x2gqr.x2gqr.sandbox1293.opentlc.com" \
  --api-key-file ./granite.token \
  --model granite-8b
```

If chat calls return **404**, your server may expect the base URL to include `/v1`:

```bash
export GRANITE_API_BASE="https://granite-8b-app-project.apps.cluster-x2gqr.x2gqr.sandbox1293.opentlc.com/v1"
```

See `docs/granite-client.env.example` for a template (no real secrets).

### CrashLoop auto-remediation workflow (`--workflow remediate`)

Uses MCP tools only (no LLM required unless `--remediate-use-llm`):

1. `listar_pods_em_erro_cluster` → keep pods with **CrashLoop** in status  
2. **Application namespaces only** by default: skips **`default`**, **`kube-*`**, and **`openshift-*`** (unless `--include-openshift-namespaces`). Use **`--allow-system-namespaces`** to allow `default` / `kube-*` when auto-picking a pod, or pin **`--remediate-namespace`**.  
3. If several CrashLoop pods exist in scope, **non-openshift** namespaces sort first (then `openshift-*`).  
4. The MCP server lists pods with **API pagination** so large clusters don’t miss namespaces.  
5. `ver_logs_pod` on the first selected pod  
6. Parses logs for `environment variable NAME is not set` (and similar) → builds `env_vars`  
7. Infers **Deployment** name from the pod name (`name-rs-hash-suffix` → `name`)  
8. Calls `definir_env_deployment` **only** with **`--approve`** (or use **`--dry-run`** to preview)

```bash
export GRANITE_API_BASE="https://..."
export GRANITE_API_TOKEN="..."

# Preview
uv run python client-gpt.py server-gpt.py --workflow remediate --dry-run

# Apply env fix (writes to the cluster)
uv run python client-gpt.py server-gpt.py --workflow remediate --approve
```

Optional:

- `--remediate-namespace app-project --remediate-pod my-pod-xxx` — target one pod  
- `--allow-system-namespaces` — allow auto-select in `default` / `kube-*` (still skips `openshift-*` unless `--include-openshift-namespaces`)  
- `--remediate-use-llm` — if regex finds nothing, ask the LLM for `{"env_vars":[...]}` JSON  

Add more default env values in `remediation_workflow.py` → `_DEFAULT_ENV_FOR_MISSING`.

### Running the Client

**Basic usage:**

```bash
uv run python client-gpt.py server-gpt.py
```

**With your custom LLM endpoint (no API key needed):**

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --model llama-32-3b-instruct
```

**With API key (if your endpoint requires authentication):**

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --api-key YOUR_API_KEY \
  --model llama-32-3b-instruct
```

**Using environment variables (API key optional):**

```bash
export OPENAI_BASE_URL=https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com
# Only if your endpoint requires auth:
# export OPENAI_API_KEY=YOUR_API_KEY
uv run python client-gpt.py server-gpt.py --model llama-32-3b-instruct
```

### Command-Line Options

- `server_path`: Path to your MCP server script (required)
- `--model`: Model name (default: `llama-32-3b-instruct`)
- `--api-base`: Custom API base URL (or use `OPENAI_BASE_URL` env var)
- `--api-key`: API key (optional - only if endpoint requires auth, or use `OPENAI_API_KEY` env var)
- `--objective`: Goal for the coordinator (default: "Assess cluster health and suggest safe next steps.")
- `--max-steps`: Maximum number of steps (default: 15)
- `--sleep`: Seconds between iterations (default: 8.0)
- `--approve`: Allow write operations (required for upgrades)

### Example: Full Command

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --model llama-32-3b-instruct \
  --objective "Check cluster status and list all nodes" \
  --max-steps 5 \
  --sleep 3.0
```

## How to Test the Client

### 1. Test MCP Server Connection

First, verify your MCP server works independently:

```bash
# Test server directly (if it has a test mode)
uv run python server-gpt.py
```

Or use MCP Inspector:

```bash
mcp dev server-gpt.py
```

### 2. Test Client with Minimal Steps

Run with just 1-2 steps to verify connection:

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --model llama-32-3b-instruct \
  --max-steps 2 \
  --sleep 2.0
```

### 3. Test Read-Only Operations

Test without `--approve` flag (only read operations):

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --model llama-32-3b-instruct \
  --objective "List cluster status and nodes" \
  --max-steps 3
```

### 4. Test Write Operations

Test with `--approve` flag (allows upgrades):

```bash
uv run python client-gpt.py server-gpt.py \
  --api-base https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com \
  --model llama-32-3b-instruct \
  --objective "Check if cluster needs upgrade" \
  --max-steps 5 \
  --approve
```

### 5. Debug Mode

If you encounter issues, check:

1. **API endpoint is accessible:**

   ```bash
   curl https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com/health
   ```

2. **API key is valid:**

   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://llama-32-3b-instruct-my-first-model.apps.ocp.h5wrd.sandbox5236.opentlc.com/v1/models
   ```

3. **MCP server path is correct:**
   ```bash
   ls -la server-gpt.py  # Verify file exists
   ```

### Expected Output

When running successfully, you should see:

```
=== Step 1/15 ===
Observed (cluster):
Current version: 4.12.0
...

Observed (nodes):
- node1 | Ready=True | kubelet=1.28.0
...

LLM decision:
{
  "tool_name": "verificar_status_sistema",
  "args": {...},
  "reason": "...",
  "stop": false
}

Executing: verificar_status_sistema args={...}
Tool result:
...
```

### Troubleshooting

**Error: "Missing API key"**

- This error should no longer appear - API key is now optional
- Only provide `--api-key` or `OPENAI_API_KEY` if your endpoint requires authentication

**Error: "LLM API call failed"**

- Verify your API endpoint URL is correct
- Check if the endpoint supports OpenAI-compatible API format
- Verify your API key is valid

**Error: "Connection refused" or "Failed to connect"**

- Check if the MCP server path is correct
- Verify the server script is executable
- Check network connectivity to your LLM endpoint

**Error: "Tool not found"**

- Verify tool names in `client-gpt.py` match those in `server-gpt.py`
- Check the tool constants: `TOOL_VERIFY_STATUS`, `TOOL_LIST_NODES`, `TOOL_UPGRADE`
