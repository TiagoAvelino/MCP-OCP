"""Ensure the monorepo root (basic-mcp) is on sys.path for openshift_* imports."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_basic_mcp_on_path() -> Path:
    """
    Resolution order:
      1) REMEDIATION_PROJECT_ROOT env (absolute path to basic-mcp repo root)
      2) remediation-api/../.. (this file: app/services -> repo root)
    """
    env = os.environ.get("REMEDIATION_PROJECT_ROOT")
    if env:
        root = Path(env).resolve()
    else:
        # remediation-api/app/services/repo_path.py -> basic-mcp/
        root = Path(__file__).resolve().parents[3]

    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root
