"""
agentgovern-sdk — The Universal Governance SDK Core
====================================================
This is the base package that all framework connectors build on.
It provides the GovernanceEnvelope (the standard event format) and the
GovCore evaluator that sends events to the AgentGovern Governance API.

Install:
    pip install agentgovern-sdk

Environment Variables:
    AGENTGOVERN_SERVER   — URL of governance server (default: http://localhost:8000)
    AGENTGOVERN_API_KEY  — Your API key
    AGENTGOVERN_AGENT_CODE — Default agent code for this process
    AGENTGOVERN_FAIL_OPEN — "true" (allow on server error) or "false" (block on error)
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger("agentgovern.sdk")

# ── Constants ──────────────────────────────────────────────────────────────
DEFAULT_SERVER = "http://localhost:8000"
DEFAULT_TIMEOUT = 5.0
SDK_VERSION = "0.1.0"


# ── Data Models ───────────────────────────────────────────────────────────

@dataclass
class GovernanceEnvelope:
    """
    The Universal Event Envelope — the standard format every connector
    sends to the AgentGovern Governance API before any agent action.
    """
    agent_code: str
    action_requested: str
    agent_source: str = "unknown"           # "openai" | "anthropic" | "crewai" | "custom"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4))
    context: dict = field(default_factory=dict)
    calling_system: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_code": self.agent_code,
            "agent_source": self.agent_source,
            "action_requested": self.action_requested,
            "context": self.context,
            "session_id": self.session_id,
            "calling_system": self.calling_system,
            "timestamp": self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime),
            "sdk_version": SDK_VERSION,
        }


@dataclass
class GovernanceVerdict:
    """The governance decision returned for an event envelope."""
    verdict: str                            # "APPROVED" | "BLOCKED" | "ESCALATED"
    approved: bool
    risk_score: str = "UNKNOWN"
    policy_matched: Optional[str] = None
    audit_id: Optional[str] = None
    requires_human_review: bool = False
    reason: str = ""
    mode: str = "online"                    # "online" | "offline"

    @classmethod
    def approved_offline(cls) -> "GovernanceVerdict":
        """Returned when server is unreachable and fail_open=True."""
        return cls(
            verdict="APPROVED",
            approved=True,
            risk_score="UNKNOWN",
            reason="Governance server unreachable — fail-open mode, action allowed.",
            mode="offline",
        )

    @classmethod
    def blocked_offline(cls) -> "GovernanceVerdict":
        """Returned when server is unreachable and fail_open=False."""
        return cls(
            verdict="BLOCKED",
            approved=False,
            risk_score="UNKNOWN",
            reason="Governance server unreachable — fail-safe mode, action denied.",
            mode="offline",
        )


# ── Core Evaluator ────────────────────────────────────────────────────────

class GovCore:
    """
    The thin evaluation engine at the heart of every connector.
    Sends a GovernanceEnvelope to the server and returns a GovernanceVerdict.

    Usage::

        core = GovCore
        envelope = GovernanceEnvelope(
            agent_code="FI-ANALYST-001",
            action_requested="wire_transfer",
            context={"amount": 45000, "currency": "USD"},
        )
        verdict = core.evaluate(envelope)
        if not verdict.approved:
            raise PermissionError(f"Governance blocked action: {verdict.reason}")
    """

    def __init__(
        self,
        server: Optional[str] = None,
        api_key: Optional[str] = None,
        fail_open: Optional[bool] = None,
    ):
        self.server = (server or os.environ.get("AGENTGOVERN_SERVER", DEFAULT_SERVER)).rstrip("/")
        self.api_key = api_key or os.environ.get("AGENTGOVERN_API_KEY", "")
        raw_fail_open = os.environ.get("AGENTGOVERN_FAIL_OPEN", "true")
        self.fail_open = fail_open if fail_open is not None else (raw_fail_open.lower != "false")

    def evaluate(self, envelope: GovernanceEnvelope) -> GovernanceVerdict:
        """Send the envelope to the governance server and return the verdict."""
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["X-API-Key"] = self.api_key

                resp = client.post(
                    f"{self.server}/governance/evaluate",
                    json=envelope.to_dict,
                    headers=headers,
                )
                resp.raise_for_status
                data = resp.json

                return GovernanceVerdict(
                    verdict=data.get("verdict", "BLOCKED"),
                    approved=data.get("verdict") == "APPROVED",
                    risk_score=data.get("risk_score", "UNKNOWN"),
                    policy_matched=data.get("policy_matched"),
                    audit_id=data.get("audit_id"),
                    requires_human_review=data.get("requires_human_review", False),
                    reason=data.get("reason", ""),
                    mode="online",
                )

        except Exception as exc:
            logger.warning("[AgentGovern SDK] Server unreachable: %s", exc)
            if self.fail_open:
                logger.warning("[AgentGovern SDK] FAIL-OPEN: action allowed without governance.")
                return GovernanceVerdict.approved_offline
            return GovernanceVerdict.blocked_offline

    def is_reachable(self) -> bool:
        """Quick health check — returns True if governance server is up."""
        try:
            with httpx.Client(timeout=2.0) as client:
                return client.get(f"{self.server}/health").status_code == 200
        except Exception:
            return False


# ── Module-level singleton (optional convenience) ─────────────────────────

_default_core: Optional[GovCore] = None


def get_default_core -> GovCore:
    """Return (or create) the process-level GovCore singleton."""
    global _default_core
    if _default_core is None:
        _default_core = GovCore
    return _default_core


def evaluate(
    agent_code: str,
    action: str,
    agent_source: str = "custom",
    context: Optional[dict] = None,
    calling_system: str = "",
) -> GovernanceVerdict:
    """
    Module-level convenience function. Uses environment variables for configuration.

    Example::

        import agentgovern_sdk as gov
        verdict = gov.evaluate("MY-AGENT-001", "delete_user", context={"user_id": 42})
        if not verdict.approved:
            raise PermissionError(verdict.reason)
    """
    envelope = GovernanceEnvelope(
        agent_code=agent_code,
        action_requested=action,
        agent_source=agent_source,
        context=context or {},
        calling_system=calling_system,
    )
    return get_default_core.evaluate(envelope)
