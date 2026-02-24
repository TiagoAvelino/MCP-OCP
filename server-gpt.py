from __future__ import annotations

from typing import Any, Dict, Optional, List

from mcp.server.fastmcp import FastMCP

from kubernetes import client, config
from kubernetes.client import ApiException

# Constants
OPENSHIFT_GROUP = "config.openshift.io"
OPENSHIFT_VERSION = "v1"
CLUSTERVERSION_PLURAL = "clusterversions"
CLUSTERVERSION_NAME = "version"

mcp = FastMCP("DemoOpenShift")

# Cache for auth loading
_auth_loaded = False


# -----------------------------
# Kubernetes/OpenShift API setup
# -----------------------------
def _load_kube_auth() -> None:
    """
    Tries in-cluster auth first (ServiceAccount), then falls back to local kubeconfig.
    Caches the result to avoid repeated loading.
    """
    global _auth_loaded
    if _auth_loaded:
        return
    
    try:
        config.load_incluster_config()
    except Exception:
        # Uses default kubeconfig resolution (~/.kube/config) or KUBECONFIG env var
        config.load_kube_config()
    finally:
        _auth_loaded = True


def _core_v1() -> client.CoreV1Api:
    _load_kube_auth()
    return client.CoreV1Api()


def _custom() -> client.CustomObjectsApi:
    _load_kube_auth()
    return client.CustomObjectsApi()


# -----------------------------
# OpenShift helpers
# -----------------------------
def _get_cluster_version_obj() -> Dict[str, Any]:
    """
    OpenShift ClusterVersion is cluster-scoped.
    """
    return _custom().get_cluster_custom_object(
        group=OPENSHIFT_GROUP,
        version=OPENSHIFT_VERSION,
        plural=CLUSTERVERSION_PLURAL,
        name=CLUSTERVERSION_NAME,
    )


def _summarize_clusterversion(cv: Dict[str, Any]) -> str:
    status = cv.get("status", {})
    desired = cv.get("spec", {}).get("desiredUpdate", {}) or {}
    history = status.get("history", []) or []
    conds = {c.get("type"): c for c in (status.get("conditions") or [])}

    current = status.get("desired", {}).get("version") or status.get("version")
    desired_ver = desired.get("version")
    progressing = conds.get("Progressing", {}).get("status")
    available = conds.get("Available", {}).get("status")
    failing = conds.get("Failing", {}).get("status")

    # last history entry usually has useful info
    last_hist = history[0] if history else {}
    state = last_hist.get("state")
    started = last_hist.get("startedTime")
    completed = last_hist.get("completionTime")
    msg = conds.get("Progressing", {}).get("message") or conds.get("Failing", {}).get("message") or ""

    lines = [
        f"Current version: {current or 'unknown'}",
        f"Desired version: {desired_ver or current or 'unknown'}",
        f"Available: {available} | Progressing: {progressing} | Failing: {failing}",
        f"Last update state: {state or 'unknown'}",
    ]
    if started:
        lines.append(f"Started: {started}")
    if completed:
        lines.append(f"Completed: {completed}")
    if msg:
        lines.append(f"Message: {msg}")

    return "\n".join(lines)


# -----------------------------
# MCP tools
# -----------------------------
@mcp.tool()
def verificar_status_sistema(componente: str) -> str:
    """
    Checks basic status for a component. Useful before updates.
    Args:
        componente: 'cluster' | 'api' | 'nos'
    """
    c = componente.lower().strip()

    if c == "cluster":
        try:
            cv = _get_cluster_version_obj()
            return _summarize_clusterversion(cv)
        except ApiException as e:
            return f"Failed to read ClusterVersion: {e.status} {e.reason} - {e.body}"
        except Exception as e:
            return f"Failed to read ClusterVersion: {type(e).__name__}: {e}"

    if c == "api":
        # Quick ping: list namespaces (cheap)
        try:
            v1 = _core_v1()
            v1.list_namespace(limit=1)
            return "API: Online (basic request succeeded)."
        except Exception as e:
            return f"API: Unreachable or unauthorized: {type(e).__name__}: {e}"

    if c in ("nos", "nodes"):
        try:
            v1 = _core_v1()
            nodes = v1.list_node()
            ready = 0
            for n in nodes.items:
                for cond in n.status.conditions or []:
                    if cond.type == "Ready" and cond.status == "True":
                        ready += 1
                        break
            return f"Nodes: {ready}/{len(nodes.items)} Ready."
        except Exception as e:
            return f"Nodes: Failed to list: {type(e).__name__}: {e}"

    return f"Componente '{componente}' desconhecido."


@mcp.tool()
def listar_nodes() -> str:
    """
    Lists cluster nodes with basic info (name, ready, kubelet version).
    """
    try:
        v1 = _core_v1()
        nodes = v1.list_node().items
        out: List[str] = []
        for n in nodes:
            name = n.metadata.name
            kubelet = n.status.node_info.kubelet_version if n.status and n.status.node_info else "unknown"
            ready = "Unknown"
            for cond in (n.status.conditions or []):
                if cond.type == "Ready":
                    ready = cond.status
                    break
            out.append(f"- {name} | Ready={ready} | kubelet={kubelet}")
        return "\n".join(out) if out else "No nodes returned."
    except ApiException as e:
        return f"Failed to list nodes: {e.status} {e.reason} - {e.body}"
    except Exception as e:
        return f"Failed to list nodes: {type(e).__name__}: {e}"


@mcp.tool()
def iniciar_upgrade_openshift(version: str, image: Optional[str] = None) -> str:
    """
    Starts an OpenShift cluster upgrade by setting ClusterVersion.spec.desiredUpdate.
    Args:
        version: target version (example: '4.14.25')
        image: optional release image pullspec (advanced; usually omit)
    Notes:
        Requires RBAC permission to patch clusterversions.config.openshift.io 'version'.
    """
    body: Dict[str, Any] = {"spec": {"desiredUpdate": {"version": version}}}
    if image:
        body["spec"]["desiredUpdate"]["image"] = image

    try:
        _custom().patch_cluster_custom_object(
            group=OPENSHIFT_GROUP,
            version=OPENSHIFT_VERSION,
            plural=CLUSTERVERSION_PLURAL,
            name=CLUSTERVERSION_NAME,
            body=body,
        )
        cv = _get_cluster_version_obj()
        return "Upgrade request submitted.\n\n" + _summarize_clusterversion(cv)
    except ApiException as e:
        return f"Failed to patch ClusterVersion: {e.status} {e.reason} - {e.body}"
    except Exception as e:
        return f"Failed to patch ClusterVersion: {type(e).__name__}: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
