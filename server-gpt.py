"""
FastMCP server — registers tools implemented in openshift_tool_handlers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from mcp.server.fastmcp import FastMCP

import openshift_tool_handlers as h

mcp = FastMCP("DemoOpenShift")


@mcp.tool()
def verificar_status_sistema(componente: str) -> str:
    """Checks basic status for a component. Useful before updates."""
    return h.verificar_status_sistema(componente)


@mcp.tool()
def listar_nodes() -> str:
    """Lists cluster nodes with basic info (name, ready, kubelet version)."""
    return h.listar_nodes()


@mcp.tool()
def listar_pods(namespace: str) -> str:
    """Lists pods in a given namespace with basic info."""
    return h.listar_pods(namespace)


@mcp.tool()
def listar_pods_em_erro_cluster() -> str:
    """Lists pods across all namespaces in problematic states."""
    return h.listar_pods_em_erro_cluster()


@mcp.tool()
def iniciar_upgrade_openshift(version: str, image: Optional[str] = None) -> str:
    """Starts an OpenShift cluster upgrade via ClusterVersion."""
    return h.iniciar_upgrade_openshift(version, image)


@mcp.tool()
def ver_logs_pod(
    pod: str,
    namespace: str,
    container: Optional[str] = None,
    tail_lines: Optional[int] = 100,
    timestamps: bool = False,
) -> str:
    """Retrieves the logs of a pod in the cluster."""
    return h.ver_logs_pod(pod, namespace, container, tail_lines, timestamps)


@mcp.tool()
def definir_env_deployment(
    deployment: str,
    namespace: str,
    env_vars: List[Dict[str, str]],
) -> str:
    """Sets environment variables on a Deployment (merged with existing)."""
    return h.definir_env_deployment(deployment, namespace, env_vars)


@mcp.resource("docs://mcpreadme")
def obter_mcpreadme() -> str:
    """Returns the full docs/mcpreadme.md content for MCP clients."""
    MCPREADME_PATH = Path(__file__).parent / "docs" / "mcpreadme.md"
    return MCPREADME_PATH.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
