"""
AgentGovern Client SDK — embed governance into any AI agent in 3 lines.

Usage::

    from agentgovern import GovernanceClient

    gov = GovernanceClient(passport_token="<jwt>", edge_gateway="http://edge:8001")

    # Before any action:
    if not gov.authorize(action="write", resource="invoice-db", amount=15000):
        raise PermissionError("Governance denied this action")

    # After completion:
    gov.report(decision_id=..., outcome="success", confidence=0.91)

    # Regular heartbeat (call in a background thread):
    gov.heartbeat(host_id="worker-node-01", agent_version="1.2.0")

Design principles:
  - Synchronous by default (works in any agent framework)
  - Async available for high-throughput scenarios
  - Falls back gracefully when edge gateway is unreachable
  - Zero external dependencies beyond httpx + PyJWT
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Default fail-open behavior: if governance is unreachable, allow + warn
FAIL_OPEN = True
HEARTBEAT_INTERVAL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 5.0


@dataclass
class AuthorizationResult:
    authorized: bool
    verdict: str          # "allow" | "deny" | "escalate"
    reason: str
    decision_id: str
    agent_tier: str = ""
    latency_ms: float = 0.0
    mode: str = "online"


@dataclass
class ReportResult:
    accepted: bool
    message: str = ""


class GovernanceClient:
    """
    Drop-in governance client for any Python AI agent.

    Thread-safe. Maintains a background heartbeat thread.
    Uses the edge gateway when available; falls back to control plane directly.
    """

    def __init__(
        self,
        passport_token: str,
        edge_gateway_url: str = "http://localhost:8001",
        control_plane_url: str = "http://localhost:8000",
        environment: str = "cloud",
        fail_open: bool = FAIL_OPEN,
        enable_heartbeat: bool = True,
    ):
        self.passport_token = passport_token
        self.edge_gateway_url = edge_gateway_url.rstrip("/")
        self.control_plane_url = control_plane_url.rstrip("/")
        self.environment = environment
        self.fail_open = fail_open
        self._last_decision_id: str = ""
        self._heartbeat_thread: Optional[threading.Thread] = None

        if enable_heartbeat:
            self._start_heartbeat_thread

    # ──────────────────────────────────────────────
    # Core API: 3 functions
    # ──────────────────────────────────────────────

    def authorize(
        self,
        action: str,
        resource: str,
        amount: float = 0.0,
        context: dict = None,
    ) -> AuthorizationResult:
        """
        Request authorization for an action BEFORE executing it.

        Args:
            action    : Action type — "read" | "write" | "execute" | "escalate"
            resource  : What the agent wants to act on (table name, API endpoint, etc.)
            amount    : Financial amount if relevant (default 0.0)
            context   : Additional context for policy evaluation

        Returns:
            AuthorizationResult with authorized=True/False and verdict details

        If governance is unreachable:
            fail_open=True  → returns authorized=True with mode="offline" (warns)
            fail_open=False → returns authorized=False (safe-by-default)
        """
        payload = {
            "passport_token": self.passport_token,
            "action_type": action,
            "resource": resource,
            "amount": amount,
            "environment": self.environment,
            "context": context or {},
        }

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.post(f"{self.edge_gateway_url}/authorize", json=payload)
                resp.raise_for_status
                data = resp.json
                result = AuthorizationResult(
                    authorized=data.get("authorized", False),
                    verdict=data.get("verdict", "deny"),
                    reason=data.get("reason", ""),
                    decision_id=data.get("decision_id", ""),
                    agent_tier=data.get("agent_tier", ""),
                    latency_ms=data.get("latency_ms", 0.0),
                    mode=data.get("mode", "online"),
                )
                self._last_decision_id = result.decision_id
                self._log_result(action, resource, result)
                return result

        except Exception as e:
            logger.warning(f"[SDK] Authorization request failed: {e}")
            if self.fail_open:
                logger.warning("[SDK] FAIL-OPEN: allowing action (governance unreachable)")
                return AuthorizationResult(
                    authorized=True,
                    verdict="allow",
                    reason="Governance unreachable — fail-open mode",
                    decision_id="offline",
                    mode="offline",
                )
            return AuthorizationResult(
                authorized=False,
                verdict="deny",
                reason=f"Governance unreachable and fail-open=False: {e}",
                decision_id="offline",
                mode="offline",
            )

    def report(
        self,
        outcome: str,
        confidence: float,
        decision_id: str = "",
        metadata: dict = None,
    ) -> ReportResult:
        """
        Report task outcome back to the governance system.
        This triggers PULSE trust score updates and GENESIS gene extraction.

        Args:
            outcome    : "success" | "failure" | "escalated" | "human_override"
            confidence : Agent's self-reported confidence score (0.0 - 1.0)
            decision_id: The ID from the preceding authorize call
            metadata   : Additional outcome data (tool_calls, reasoning_trace, etc.)
        """
        payload = {
            "decision_id": decision_id or self._last_decision_id,
            "outcome": outcome,
            "confidence_score": confidence,
            "metadata": metadata or {},
        }

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.post(
                    f"{self.control_plane_url}/pulse/report-outcome",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.passport_token}"},
                )
                resp.raise_for_status
                return ReportResult(accepted=True, message=resp.json.get("message", ""))
        except Exception as e:
            logger.warning(f"[SDK] Outcome report failed: {e}")
            return ReportResult(accepted=False, message=str(e))

    def heartbeat(
        self,
        host_id: str,
        agent_version: str = "1.0.0",
        metadata: dict = None,
    ) -> bool:
        """
        Send a heartbeat to the edge gateway. Call every 30 seconds.
        Returns True if gateway acknowledged.
        """
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    f"{self.edge_gateway_url}/heartbeat",
                    json={
                        "agent_id": self._extract_agent_id,
                        "passport_token": self.passport_token,
                        "host_id": host_id,
                        "agent_version": agent_version,
                        "metadata": metadata or {},
                    },
                )
                return resp.status_code == 200
        except Exception:
            return False

    # ──────────────────────────────────────────────
    # Convenience properties
    # ──────────────────────────────────────────────

    @property
    def last_decision_id(self) -> str:
        return self._last_decision_id

    # ──────────────────────────────────────────────
    # Background heartbeat thread
    # ──────────────────────────────────────────────

    def _start_heartbeat_thread(self) -> None:
        def _run:
            while True:
                try:
                    self.heartbeat(host_id="auto-heartbeat")
                except Exception:
                    pass
                time.sleep(HEARTBEAT_INTERVAL_SECONDS)

        self._heartbeat_thread = threading.Thread(target=_run, daemon=True)
        self._heartbeat_thread.start

    def _extract_agent_id(self) -> str:
        """Extract agent_id from passport without verifying (read-only)."""
        try:
            import jwt
            decoded = jwt.decode(self.passport_token, options={"verify_signature": False})
            return decoded.get("sub", "unknown")
        except Exception:
            return "unknown"

    def _log_result(self, action: str, resource: str, result: AuthorizationResult) -> None:
        level = logging.INFO if result.authorized else logging.WARNING
        logger.log(
            level,
            f"[SDK] {result.verdict.upper} action={action} resource={resource} "
            f"tier={result.agent_tier} latency={result.latency_ms}ms mode={result.mode}"
        )
