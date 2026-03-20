# Deploy remediation stack on OpenShift

Two workloads in the **same namespace**, wired with **ClusterIP Services**:

| Component        | Service            | Port | Role |
|-----------------|--------------------|------|------|
| **agent-console** | `agent-console`    | 8080 | Nginx: static UI + reverse-proxy `/api/remediation` → API |
| **remediation-api** | `remediation-api` | 8787 | FastAPI + SSE + in-cluster Kubernetes client |

Browsers use a **single OpenShift Route** to **agent-console** only. The UI calls **relative** `/api/remediation/...`, so nginx forwards to `http://remediation-api:8787` (in-cluster DNS). **No CORS** is required for that path.

## Prerequisites

- `oc` / `kubectl` and permission to create **ClusterRole** + **ClusterRoleBinding** (cluster admin or equivalent).
- **Podman** or **Docker** to build images (or use OpenShift Builds).

## RBAC scope (important)

The remediation workflow lists pods **cluster-wide** (`list_pod_for_all_namespaces`). The bundled **ClusterRole** grants:

- `pods`: get, list, watch (all namespaces)
- `pods/log`: get
- `deployments`: get, list, patch, update (all namespaces)

This is **broad**. To reduce blast radius you would need **code changes** to list only allowed namespaces and a **Role** per namespace instead of a ClusterRole.

## Build images (from repository root)

```bash
cd /path/to/basic-mcp

podman build -f deploy/openshift/Dockerfile.remediation-api -t remediation-api:latest .
podman build -f deploy/openshift/Dockerfile.agent-console -t agent-console:latest .
```

Push to a registry your cluster can pull (example internal registry after `oc registry login`):

```bash
export REGISTRY=$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null || true)
# or quay.io/yourorg/...
```

Update image references in:

- [31-deployment-remediation-api.yaml](31-deployment-remediation-api.yaml)
- [41-deployment-agent-console.yaml](41-deployment-agent-console.yaml)

## Install

1. Create project (or apply namespace manifest):

   ```bash
   oc new-project remediation-app
   # or: oc apply -f deploy/openshift/00-namespace.yaml
   ```

2. Apply manifests (order is alphabetical):

   ```bash
   oc apply -f deploy/openshift/
   ```

   If you already created the project with `oc new-project`, you can skip or ignore `00-namespace.yaml`.

3. Point Deployments at your images, e.g.:

   ```bash
   oc set image deployment/remediation-api api=image-registry.openshift-image-registry.svc:5000/remediation-app/remediation-api:latest -n remediation-app
   oc set image deployment/agent-console nginx=image-registry.openshift-image-registry.svc:5000/remediation-app/agent-console:latest -n remediation-app
   ```

## Verify

```bash
# API from another pod in the namespace
oc run curl --rm -it --restart=Never --image=curlimages/curl -- \
  curl -sS http://remediation-api.remediation-app.svc:8787/api/remediation/health

# Route URL (UI)
oc get route agent-console -n remediation-app -o jsonpath='{.spec.host}{"\n"}'
```

Open the Route in a browser → **Auto Remediate** → confirm SSE log streaming (nginx: `proxy_buffering off`, long `proxy_read_timeout`).

## Optional: LLM env suggestions

Create a **Secret** (or use **SealedSecrets** / External Secrets) and mount env on `remediation-api`:

- `GRANITE_API_BASE` / `OPENAI_BASE_URL`
- `GRANITE_API_TOKEN` / `OPENAI_API_KEY`
- `LLM_MODEL` (optional)

## Dual-Route topology (not recommended)

If the UI is built with `VITE_REMEDIATION_API=https://...` pointing at a **second** Route for the API, set on **remediation-api**:

```yaml
env:
  - name: REMEDIATION_CORS_ORIGINS
    value: "https://<agent-console-route-host>"
```

## Troubleshooting

| Symptom | Check |
|--------|--------|
| 502 / SSE cuts off | nginx `proxy_read_timeout`, API pod logs, Route idle timeout |
| API `Forbidden` on pods | ClusterRoleBinding + ServiceAccount on `remediation-api` Deployment |
| Image pull errors | ImageStream pull secrets / `imagePullPolicy` / registry path |
| Permission denied in container | OpenShift SCC; images use non-root UIDs (8080 nginx, 1001 API) |

## Files

- [Dockerfile.remediation-api](Dockerfile.remediation-api) — UBI9 Python, copies `openshift_tool_handlers.py`, `remediation_workflow.py`, `remediation-api/`
- [Dockerfile.agent-console](Dockerfile.agent-console) — Node build + nginx alpine
- [nginx.conf](nginx.conf) — SPA `try_files`, `/api/remediation` proxy + SSE-friendly settings
