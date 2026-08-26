"""
AgentOS Python SDK — MCP Client.

Bridge 5 (AgentOS → AgentGovernOS):
Every tool call is intercepted and checked against the AgentGovernOS
SENTINEL policy engine before being forwarded to the Network Plane proxy.

The policy check is kept under 3 seconds to avoid blocking agent execution.
Set GOVERN_FAILOPEN=true (default) to allow calls if GovernOS is unreachable.
"""

import httpx
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

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
GOVERN_FAILOPEN = os.getenv("GOVERN_FAILOPEN", "true").lower() == "true"

import hashlib, json, time

def _govern_headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h

def _payload_hash(tool_name: str, args: dict) -> str:
    s = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()


class MCPClient:
    """
    Client for interacting with MCP tools via the Network Plane proxy.

    Bridge 5: Every call_tool() invocation is intercepted by AgentGovernOS
    SENTINEL before being forwarded to the Network Plane.
    """

    def __init__(self, agent_id: str = None, network_plane_url: str = None):
        self.agent_id = agent_id or os.getenv("AGENTOS_AGENT_ID")
        self.network_plane_url = (
            network_plane_url
            or os.getenv("AGENTOS_NETWORK_PLANE_URL")
            or os.getenv("NETWORK_PLANE_URL", "http://127.0.0.1:8013")
        )
        self.http = httpx.Client(base_url=self.network_plane_url)

    def _check_policy(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Bridge 5: Check tool call against AgentGovernOS SENTINEL.
        Raises PermissionError if the call is blocked.
        """
        if not self.agent_id:
            return  # Cannot perform policy check without agent_id — skip

        payload_hash = _payload_hash(tool_name, arguments)
        body = {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "tool_args": arguments,
            "org_id": os.getenv("NUUVIXX_ORG_ID", "default"),
            "payload_hash": payload_hash,
            "timestamp_ms": int(time.time() * 1000),
        }

        try:
            r = httpx.post(
                f"{AGENTGOVERN_URL}/sentinel/evaluate-tool",
                json=body,
                headers=_govern_headers(),
                timeout=3.0,
            )
            if r.status_code == 200:
                result = r.json()
                if not result.get("allowed", True):
                    reason = result.get("reason", "policy_denied")
                    logger.warning(
                        f"[MCPClient] Tool '{tool_name}' BLOCKED by GovernOS: {reason} "
                        f"| agent={self.agent_id} hash={payload_hash[:12]}..."
                    )
                    raise PermissionError(
                        f"Tool '{tool_name}' is blocked by AgentGovernOS policy: {reason}"
                    )
                logger.debug(
                    f"[MCPClient] Tool '{tool_name}' ALLOWED | "
                    f"hash={payload_hash[:12]}..."
                )
                return

        except PermissionError:
            raise  # Re-raise policy blocks — never swallow these
        except httpx.TimeoutException:
            logger.warning(f"[MCPClient] GovernOS policy check timed out for '{tool_name}'")
        except httpx.RequestError as e:
            logger.warning(f"[MCPClient] GovernOS unreachable: {e}")
        except Exception as e:
            logger.warning(f"[MCPClient] Policy check error: {e}")

        # Fail-open or fail-closed
        if not GOVERN_FAILOPEN:
            raise PermissionError(
                f"Tool '{tool_name}' blocked: AgentGovernOS unreachable and GOVERN_FAILOPEN=false."
            )

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Invokes an MCP tool via the Network Plane proxy.

        Bridge 5: Performs a GovernOS policy check before forwarding the call.
        The full tool_name sent to GovernOS is "{server_name}:{tool_name}".
        """
        if not self.agent_id:
            raise ValueError("AGENTOS_AGENT_ID not set. Cannot invoke tools.")

        full_tool_name = f"{server_name}:{tool_name}"

        # ── Bridge 5: GovernOS policy gate ────────────────────────────────────
        self._check_policy(full_tool_name, arguments)

        # ── Forward to Network Plane ───────────────────────────────────────────
        payload = {
            "agent_id": self.agent_id,
            "server_name": server_name,
            "tool_name": tool_name,
            "arguments": arguments,
        }

        resp = self.http.post("/proxy/call", json=payload)
        resp.raise_for_status()

        # Parse JSON-RPC response
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP Tool Error: {data['error']}")

        return data.get("result")
