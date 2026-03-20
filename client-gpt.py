from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fastmcp import Client
from openai import OpenAI

from remediation_workflow import (
    FastMcpToolCaller,
    RemediationOptions,
    run_crashloop_remediation_async,
)

# Tool name constants
TOOL_VERIFY_STATUS = "verificar_status_sistema"
TOOL_LIST_NODES = "listar_nodes"
TOOL_UPGRADE = "iniciar_upgrade_openshift"
TOOL_LIST_PODS_ERROR = "listar_pods_em_erro_cluster"
TOOL_VER_LOGS = "ver_logs_pod"
TOOL_SET_ENV = "definir_env_deployment"

# Default LLM model when using Granite on OpenShift (override with --model)
DEFAULT_LLM_MODEL = "granite-8b"


def _read_api_key_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def _resolve_llm_base_url(cli_base: Optional[str]) -> Optional[str]:
    """
    Order: --api-base, OPENAI_BASE_URL, GRANITE_API_BASE.
    Trailing slash removed (OpenAI client appends /v1/...).
    """
    raw = cli_base or os.getenv("OPENAI_BASE_URL") or os.getenv("GRANITE_API_BASE")
    if not raw:
        return None
    return raw.rstrip("/")


def _resolve_llm_api_key(cli_key: Optional[str], key_file: Optional[str]) -> Optional[str]:
    """
    Order: --api-key-file (first line), --api-key, OPENAI_API_KEY, GRANITE_API_TOKEN.
    """
    if key_file:
        return _read_api_key_file(key_file)
    return cli_key or os.getenv("OPENAI_API_KEY") or os.getenv("GRANITE_API_TOKEN") or None


# -----------------------------
# Data structures
# -----------------------------
@dataclass
class Decision:
    tool_name: Optional[str]          # name of MCP tool to call; None => stop
    args: Dict[str, Any]              # args for the tool
    reason: str                       # short explanation
    stop: bool = False                # if True => stop loop


# -----------------------------
# Helpers: FastMCP result extraction
# -----------------------------
def extract_text(result: Any) -> str:
    """
    FastMCP tool results often come as an object with .content parts.
    We try to extract readable text safely.
    """
    if result is None:
        return ""

    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        txt = getattr(first, "text", None)
        if isinstance(txt, str):
            return txt

    # Fallback
    return str(result)


# -----------------------------
# Helpers: JSON parsing from LLM output
# -----------------------------
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

def parse_json_object(text: str) -> Dict[str, Any]:
    """
    Attempts to parse a JSON object from model output.
    Accepts:
      - pure JSON
      - JSON wrapped in ```json fences
      - text that contains a JSON object somewhere inside
    """
    if not isinstance(text, str):
        raise ValueError("LLM output is not a string")

    cleaned = _JSON_FENCE_RE.sub("", text.strip())

    # If it's already JSON, great:
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Otherwise: find the first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not find JSON object in: {text[:200]}...")

    snippet = cleaned[start:end + 1]
    obj = json.loads(snippet)
    if not isinstance(obj, dict):
        raise ValueError("Parsed JSON is not an object")
    return obj


# -----------------------------
# Tool catalog
# -----------------------------
def normalize_tools(tools: Any) -> List[Dict[str, Any]]:
    """
    Convert whatever fastmcp returns into a list of dicts containing at least:
      - name
      - description
      - inputSchema (if available)
    """
    out: List[Dict[str, Any]] = []

    if tools is None:
        return out

    # Sometimes it's already JSON-like
    if isinstance(tools, dict) and "tools" in tools and isinstance(tools["tools"], list):
        tools = tools["tools"]

    if isinstance(tools, list):
        for t in tools:
            if isinstance(t, dict):
                out.append({
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema"),
                })
            else:
                # object-like
                out.append({
                    "name": getattr(t, "name", None),
                    "description": getattr(t, "description", "") or "",
                    "inputSchema": getattr(t, "inputSchema", None),
                })

    # Drop tools without names
    return [t for t in out if t.get("name")]


# -----------------------------
# LLM decision function
# -----------------------------
def llm_decide_next_action(
    *,
    openai_client: OpenAI,
    model: str,
    objective: str,
    observed_state: Dict[str, str],
    tools_catalog: List[Dict[str, Any]],
    allowed_tools: List[str],
    write_tools: List[str],
) -> Decision:
    """
    Ask the LLM for the next action. The model must output a JSON object.

    We keep safety in OUR code:
      - allowlist of tools
      - write tools flagged
      - stop if invalid tool
    """
    # Keep the tool list compact: name + description only (schemas can be large)
    tools_brief = [
        {"name": t["name"], "description": t.get("description", "")}
        for t in tools_catalog
        if t.get("name") in allowed_tools
    ]

    developer_instructions = f"""
You are an operations coordinator for an OpenShift cluster.
Your job: choose the next SINGLE MCP tool call to help achieve the objective.

Objective:
- {objective}

You MUST follow these rules:
1) You may ONLY choose a tool from this allowlist:
{allowed_tools}

2) If you choose one of these write tools, you MUST still choose it, but mark it clearly:
write_tools = {write_tools}

3) If the observed state indicates the cluster is failing/degraded, set stop=true and tool_name=null.

4) Output MUST be a single JSON object with EXACT keys:
{{
  "tool_name": string|null,
  "args": object,
  "reason": string,
  "stop": boolean
}}

No markdown. No code fences. No extra text.
""".strip()

    user_input = {
        "observed_state": observed_state,
        "available_tools": tools_brief,
    }

    # Prepare the request payload
    messages = [
        {"role": "system", "content": developer_instructions},
        {"role": "user", "content": json.dumps(user_input)},
    ]
    
    request_payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }

    # Log what we're sending
    logger.info("=" * 80)
    logger.info("LLM API Request Details:")
    logger.info(f"Base URL: {openai_client.base_url}")
    logger.info(f"Model: {model}")
    logger.info(f"System message length: {len(developer_instructions)} chars")
    logger.info(f"User message: {json.dumps(user_input, indent=2)}")
    logger.info("=" * 80)
    
    # Show equivalent curl command
    # Note: OpenAI SDK automatically appends /v1/chat/completions to base_url
    api_url = f"{openai_client.base_url}/v1/chat/completions"
    auth_header = f'Authorization: Bearer {openai_client.api_key}' if openai_client.api_key else 'Authorization: Bearer <YOUR_TOKEN>'
    curl_command = f"""curl -X POST '{api_url}' \\
  -H "Content-Type: application/json" \\
  -H "{auth_header}" \\
  -d '{json.dumps(request_payload)}'"""
    
    logger.info("Equivalent curl command:")
    logger.info(curl_command)
    logger.info("=" * 80)

    # Use standard chat.completions API (widely supported by OpenAI-compatible providers)
    # Note: OpenAI SDK automatically appends /v1/chat/completions to base_url
    try:
        resp = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
    except Exception as e:
        # Log the full URL that was attempted
        full_url = f"{openai_client.base_url}/v1/chat/completions"
        logger.error(f"API call failed. Full error: {e}")
        logger.error(f"Request was sent to: {full_url}")
        logger.error(f"Base URL provided: {openai_client.base_url}")
        logger.error("Note: OpenAI SDK automatically appends /v1/chat/completions to base_url")
        raise RuntimeError(f"LLM API call failed: {type(e).__name__}: {e}") from e

    # Extract text from response
    if not resp.choices or not resp.choices[0].message:
        raise RuntimeError("LLM returned empty response")
    
    text = resp.choices[0].message.content
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("LLM returned empty content")

    obj = parse_json_object(text)

    tool_name = obj.get("tool_name", None)
    args = obj.get("args", {}) or {}
    reason = obj.get("reason", "")
    stop = bool(obj.get("stop", False))

    if tool_name is not None and not isinstance(tool_name, str):
        raise ValueError("tool_name must be string or null")
    if not isinstance(args, dict):
        raise ValueError("args must be an object")
    if not isinstance(reason, str):
        reason = str(reason)

    # Enforce allowlist here (hard safety gate)
    if tool_name is not None and tool_name not in allowed_tools:
        return Decision(
            tool_name=None,
            args={},
            reason=f"Model suggested non-allowed tool '{tool_name}'. Stopping for safety.",
            stop=True,
        )

    return Decision(tool_name=tool_name, args=args, reason=reason, stop=stop)


async def run_crashloop_remediation(
    client: Client,
    args: argparse.Namespace,
    openai_client: OpenAI,
) -> None:
    """CLI entry: delegates to shared remediation_workflow (MCP via stdio Client)."""
    opts = RemediationOptions(
        approve=args.approve,
        dry_run=args.dry_run,
        include_openshift_namespaces=args.include_openshift_namespaces,
        app_namespaces_only=not args.allow_system_namespaces,
        remediate_namespace=args.remediate_namespace,
        remediate_pod=args.remediate_pod,
        remediate_use_llm=args.remediate_use_llm,
        model=args.model,
    )
    caller = FastMcpToolCaller(client)
    await run_crashloop_remediation_async(
        caller,
        options=opts,
        openai_client=openai_client,
        emit=lambda m: print(m, flush=True),  # sync emit OK
    )


# -----------------------------
# Main agent loop
# -----------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP client with LLM coordination (OpenAI-compatible).")
    parser.add_argument("server_path", help="Path to your MCP server script (stdio). Example: ./mcp_openshift.py")
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        help="Model name (default: env LLM_MODEL or granite-8b)",
    )
    parser.add_argument("--objective", default="Assess cluster health and suggest safe next steps.", help="Goal for the coordinator.")
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--sleep", type=float, default=8.0, help="Seconds between iterations.")
    parser.add_argument("--approve", action="store_true", help="Allow write tools to run.")
    parser.add_argument(
        "--api-base",
        default=None,
        help="OpenAI-compatible API base URL. Env: OPENAI_BASE_URL or GRANITE_API_BASE.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token / API key. Env: OPENAI_API_KEY or GRANITE_API_TOKEN.",
    )
    parser.add_argument(
        "--api-key-file",
        default=None,
        help="Read token from file (first line only). Safer than pasting in shell history.",
    )
    parser.add_argument(
        "--workflow",
        choices=("coordinator", "remediate"),
        default="coordinator",
        help="coordinator: LLM-driven loop. remediate: list CrashLoop pods, read logs, patch env via MCP.",
    )
    parser.add_argument(
        "--include-openshift-namespaces",
        action="store_true",
        help="[remediate] Also consider pods in openshift-* (default: skip).",
    )
    parser.add_argument(
        "--allow-system-namespaces",
        action="store_true",
        help="[remediate] Allow default and kube-* (still skips openshift-* unless --include-openshift-namespaces).",
    )
    parser.add_argument(
        "--remediate-namespace",
        default=None,
        help="[remediate] Only pods in this namespace.",
    )
    parser.add_argument(
        "--remediate-pod",
        default=None,
        help="[remediate] Only this pod name (with namespace via --remediate-namespace or single match).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="[remediate] Plan only; do not call definir_env_deployment.",
    )
    parser.add_argument(
        "--remediate-use-llm",
        action="store_true",
        help="[remediate] If logs do not match regex, ask LLM for env_vars JSON.",
    )
    args = parser.parse_args()

    api_key = _resolve_llm_api_key(args.api_key, args.api_key_file)
    api_base = _resolve_llm_base_url(args.api_base)

    # Initialize OpenAI client with optional custom base URL and optional API key
    # Note: OpenAI SDK requires api_key parameter, but we can pass empty string for endpoints without auth
    if api_base:
        # If api_key is None, use empty string (endpoint may not require auth)
        oai = OpenAI(api_key=api_key or "", base_url=api_base)
    else:
        # If api_key is None, use empty string (endpoint may not require auth)
        oai = OpenAI(api_key=api_key or "")

    # Define which tools exist and which are write tools (you control this)
    READ_TOOLS = [TOOL_VERIFY_STATUS, TOOL_LIST_NODES]
    WRITE_TOOLS = [TOOL_UPGRADE]
    ALLOWED_TOOLS = READ_TOOLS + WRITE_TOOLS

    async with Client(args.server_path) as client:
        # FastMCP clients are async and used in an async context
        await client.ping()

        if args.workflow == "remediate":
            await run_crashloop_remediation(client, args, oai)
            return

        tools_raw = await client.list_tools()
        tools_catalog = normalize_tools(tools_raw)

        for step in range(1, args.max_steps + 1):
            print(f"\n=== Step {step}/{args.max_steps} ===")

            # 1) OBSERVE (call read tools to build state for the model)
            observed_state: Dict[str, str] = {}

            try:
                # Cluster overview
                res_cluster = await client.call_tool(TOOL_VERIFY_STATUS, {"componente": "cluster"})
                observed_state["cluster"] = extract_text(res_cluster)

                # Nodes overview
                res_nodes = await client.call_tool(TOOL_LIST_NODES, {})
                observed_state["nodes"] = extract_text(res_nodes)

                print("Observed (cluster):")
                print(observed_state["cluster"])
                print("\nObserved (nodes):")
                print(observed_state["nodes"])
            except Exception as e:
                print(f"Error during observation: {type(e).__name__}: {e}")
                observed_state["error"] = f"Observation failed: {e}"

            # 2) DECIDE (LLM chooses next single tool call)
            try:
                decision = llm_decide_next_action(
                    openai_client=oai,
                    model=args.model,
                    objective=args.objective,
                    observed_state=observed_state,
                    tools_catalog=tools_catalog,
                    allowed_tools=ALLOWED_TOOLS,
                    write_tools=WRITE_TOOLS,
                )
            except Exception as e:
                print(f"Error getting LLM decision: {type(e).__name__}: {e}")
                return

            print("\nLLM decision:")
            print(json.dumps(decision.__dict__, indent=2))

            if decision.stop or not decision.tool_name:
                print(f"\nStopping. Reason: {decision.reason}")
                return

            # 3) SAFETY GATE for write tools
            if decision.tool_name in WRITE_TOOLS and not args.approve:
                print("\nThis action is a WRITE operation and requires approval.")
                print("Re-run with --approve to execute it.")
                print(f"Proposed: {decision.tool_name} args={decision.args}")
                print(f"Reason: {decision.reason}")
                return

            # 4) ACT
            print(f"\nExecuting: {decision.tool_name} args={decision.args}")
            try:
                result = await client.call_tool(decision.tool_name, decision.args)
                print("Tool result:")
                print(extract_text(result))
            except Exception as e:
                print(f"Error executing tool: {type(e).__name__}: {e}")
                return

            await asyncio.sleep(args.sleep)


if __name__ == "__main__":
    asyncio.run(main())
