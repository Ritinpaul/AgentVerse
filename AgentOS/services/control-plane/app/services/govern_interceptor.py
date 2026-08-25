"""
AgentOS — AgentGovernOS Policy Interceptor.

Bridge 5 (AgentOS → AgentGovernOS):
Every MCP tool call from a running agent is checked against the
AgentGovernOS SENTINEL policy engine before execution.

This is the enforcement point for:
  - Tool-use restrictions (e.g. no filesystem access in production)
  - PII data leakage prevention
  - Budget/cost governance (no expensive tools without approval)
  - OWASP ASI-compliant policy enforcement

Integration point:
  - Called by MCPClient.call_tool() in the AgentOS Python SDK
  - Called by AgentOS Control Plane before dispatching tool calls
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

try:
    for _parent in Path(__file__).resolve().parents:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(dotenv_path=_env, override=False)
            break
except Exception:
    pass

logger = logging.getLogger(__name__)

AGENTGOVERN_URL = os.getenv("AGENTGOVERN_URL", "http://127.0.0.1:8025")
NUUVIXX_API_KEY = os.getenv("NUUVIXX_API_KEY", "")

# Fail-open: if True, allow tool calls when GovernOS is unreachable (dev mode)
# Set to False in production for fail-closed security
GOVERN_FAILOPEN = os.getenv("GOVERN_FAILOPEN", "true").lower() == "true"


def _govern_headers() -> dict:
    """Service-to-service headers for AgentGovernOS API calls."""
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


def _compute_payload_hash(tool_name: str, tool_args: dict) -> str:
    """SHA-256 hash of the tool call payload for provenance logging."""
    payload_str = json.dumps({"tool": tool_name, "args": tool_args}, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()


def check_tool_policy(
    agent_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    org_id: str | None = None,
    timeout: float = 3.0,
) -> dict:
    """
    Synchronous policy check for a tool call against AgentGovernOS SENTINEL.

    Args:
        agent_id:  The AgentOS agent ID (e.g. "agent-abc123")
        tool_name: MCP tool name (e.g. "filesystem:read_file")
        tool_args: Tool arguments dict
        org_id:    Enterprise org ID for org-scoped policies
        timeout:   HTTP timeout in seconds (kept short to not block tool calls)

    Returns:
        dict with keys: allowed (bool), reason (str), policy_id (str | None)

    Raises:
        PermissionError: if tool is explicitly blocked and fail-closed
    """
    payload_hash = _compute_payload_hash(tool_name, tool_args)
    org = org_id or os.getenv("NUUVIXX_ORG_ID", "default")

    request_body = {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "org_id": org,
        "payload_hash": payload_hash,
        "timestamp_ms": int(time.time() * 1000),
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                f"{AGENTGOVERN_URL}/sentinel/evaluate-tool",
                json=request_body,
                headers=_govern_headers(),
            )

            if r.status_code == 200:
                result = r.json()
                allowed = result.get("allowed", True)
                reason  = result.get("reason", "policy_evaluation_complete")

                if not allowed:
                    logger.warning(
                        f"[GovernInterceptor] BLOCKED tool '{tool_name}' "
                        f"for agent '{agent_id}': {reason} | hash={payload_hash[:12]}..."
                    )
                else:
                    logger.debug(
                        f"[GovernInterceptor] ALLOWED tool '{tool_name}' "
                        f"for agent '{agent_id}' | hash={payload_hash[:12]}..."
                    )

                return {
                    "allowed": allowed,
                    "reason": reason,
                    "policy_id": result.get("policy_id"),
                    "payload_hash": payload_hash,
                }

            # Non-200 from GovernOS — log and fall through to fail-open/closed logic
            logger.warning(
                f"[GovernInterceptor] GovernOS returned {r.status_code} for tool '{tool_name}' — "
                f"{'allowing (fail-open)' if GOVERN_FAILOPEN else 'blocking (fail-closed)'}"
            )

    except httpx.TimeoutException:
        logger.warning(
            f"[GovernInterceptor] Policy check timed out for tool '{tool_name}' — "
            f"{'allowing (fail-open)' if GOVERN_FAILOPEN else 'blocking (fail-closed)'}"
        )
    except httpx.RequestError as e:
        logger.warning(
            f"[GovernInterceptor] Cannot reach AgentGovernOS at {AGENTGOVERN_URL}: {e} — "
            f"{'allowing (fail-open)' if GOVERN_FAILOPEN else 'blocking (fail-closed)'}"
        )

    # ── Fail-open / Fail-closed ───────────────────────────────────────────────
    if GOVERN_FAILOPEN:
        return {
            "allowed": True,
            "reason": "governance_unreachable_failopen",
            "policy_id": None,
            "payload_hash": payload_hash,
        }
    else:
        raise PermissionError(
            f"Tool '{tool_name}' blocked: AgentGovernOS unreachable and GOVERN_FAILOPEN=false. "
            f"Start AgentGovernOS at {AGENTGOVERN_URL} or set GOVERN_FAILOPEN=true for dev mode."
        )


async def check_tool_policy_async(
    agent_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    org_id: str | None = None,
    timeout: float = 3.0,
) -> dict:
    """
    Async variant of check_tool_policy for use in async contexts (FastAPI routers, etc.)
    """
    payload_hash = _compute_payload_hash(tool_name, tool_args)
    org = org_id or os.getenv("NUUVIXX_ORG_ID", "default")

    request_body = {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "org_id": org,
        "payload_hash": payload_hash,
        "timestamp_ms": int(time.time() * 1000),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{AGENTGOVERN_URL}/sentinel/evaluate-tool",
                json=request_body,
                headers=_govern_headers(),
            )
            if r.status_code == 200:
                result = r.json()
                return {
                    "allowed": result.get("allowed", True),
                    "reason": result.get("reason", "ok"),
                    "policy_id": result.get("policy_id"),
                    "payload_hash": payload_hash,
                }
    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.warning(f"[GovernInterceptor][async] GovernOS unreachable: {e}")

    if GOVERN_FAILOPEN:
        return {"allowed": True, "reason": "governance_unreachable_failopen", "policy_id": None, "payload_hash": payload_hash}
    raise PermissionError(f"Tool '{tool_name}' blocked: AgentGovernOS unreachable and fail-closed mode is active.")
