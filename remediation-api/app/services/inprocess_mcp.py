"""
In-process MCP tool execution: same callables as server-gpt / FastMCP, no subprocess.

This satisfies "use MCP" at the **tool contract** level (names + args match MCP tools)
while avoiding stdio transport inside the API worker.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from typing import Any, Dict

from .repo_path import ensure_basic_mcp_on_path

logger = logging.getLogger(__name__)


class InProcessOpenShiftToolCaller:
    """Implements remediation_workflow.ToolCaller using openshift_tool_handlers."""

    def __init__(self) -> None:
        ensure_basic_mcp_on_path()
        from openshift_tool_handlers import MCP_TOOL_DISPATCH  # noqa: WPS433

        self._dispatch = MCP_TOOL_DISPATCH

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        fn = self._dispatch.get(name)
        if fn is None:
            raise KeyError(f"Unknown MCP tool: {name}")

        sig = inspect.signature(fn)
        params = sig.parameters
        filtered = {k: v for k, v in arguments.items() if k in params}

        if name == "definir_env_deployment" and isinstance(filtered.get("env_vars"), list):
            env_names = [
                x.get("name")
                for x in filtered["env_vars"]
                if isinstance(x, dict) and x.get("name")
            ]
            logger.info(
                "in-process MCP tool call: %s deployment=%s namespace=%s env_names=%s",
                name,
                filtered.get("deployment"),
                filtered.get("namespace"),
                env_names,
            )
        else:
            logger.info("in-process MCP tool call: %s (%s)", name, filtered)
        loop = asyncio.get_running_loop()
        try:
            out = await loop.run_in_executor(
                None,
                functools.partial(fn, **filtered),
            )
        except Exception:
            logger.exception("MCP tool %s failed", name)
            raise
        logger.debug("MCP tool %s done, result_len=%s", name, len(out) if isinstance(out, str) else "?")
        return out
