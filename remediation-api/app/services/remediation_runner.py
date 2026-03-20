"""
Runs remediation_workflow inside the API process (no uv run / no subprocess).
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

from .inprocess_mcp import InProcessOpenShiftToolCaller
from .repo_path import ensure_basic_mcp_on_path


def _build_openai_client() -> OpenAI:
    api_base = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("GRANITE_API_BASE")
        or ""
    ).rstrip("/")
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("GRANITE_API_TOKEN")
        or ""
    )
    if api_base:
        return OpenAI(api_key=api_key, base_url=api_base)
    return OpenAI(api_key=api_key)


async def execute_remediation_in_process(
    *,
    approve: bool,
    dry_run: bool = False,
    include_openshift_namespaces: bool = False,
    allow_system_namespaces: bool = False,
    remediate_namespace: Optional[str] = None,
    remediate_pod: Optional[str] = None,
    remediate_use_llm: bool = False,
    model: Optional[str] = None,
    emit: Callable[[str], None] = print,
):
    """
    Import shared workflow after path setup (kubernetes client loads from pod or KUBECONFIG).
    """
    ensure_basic_mcp_on_path()
    from remediation_workflow import (  # noqa: WPS433
        RemediationOptions,
        run_crashloop_remediation_async,
    )

    logger.info(
        "execute_remediation_in_process approve=%s dry_run=%s openshift=%s allow_system_ns=%s",
        approve,
        dry_run,
        include_openshift_namespaces,
        allow_system_namespaces,
    )

    opts = RemediationOptions(
        approve=approve,
        dry_run=dry_run,
        include_openshift_namespaces=include_openshift_namespaces,
        app_namespaces_only=not allow_system_namespaces,
        remediate_namespace=remediate_namespace,
        remediate_pod=remediate_pod,
        remediate_use_llm=remediate_use_llm,
        model=model or os.environ.get("LLM_MODEL", "granite-8b"),
    )

    caller = InProcessOpenShiftToolCaller()
    oai = _build_openai_client()

    return await run_crashloop_remediation_async(
        caller,
        options=opts,
        openai_client=oai,
        emit=emit,
    )
