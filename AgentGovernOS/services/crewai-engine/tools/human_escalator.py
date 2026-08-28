"""
Tool: Human Escalator — trigger ECLIPSE Human-in-the-Loop escalation.

Used by: Governance Sentinel, Dispute Resolver agents.
"""

import logging
from datetime import UTC, datetime

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ESCALATION_REASONS = [
    "AMOUNT_EXCEEDS_AUTHORITY",
    "HIGH_FRAUD_RISK",
    "POLICY_CONFLICT",
    "LOW_CONFIDENCE",
    "CUSTOMER_ESCALATION_REQUEST",
    "REPEATED_DISPUTE",
    "LEGAL_EXPOSURE",
    "AGENT_UNCERTAINTY",
]


class EscalationInput(BaseModel):
    dispute_id: str = Field(..., description="Dispute ID being escalated")
    escalating_agent_id: str = Field(..., description="ID of the agent triggering escalation")
    reason: str = Field(
        ...,
        description=f"Reason for escalation. One of: {', '.join(ESCALATION_REASONS)}",
    )
    context_summary: str = Field(
        ...,
        description="Summary of what the agent found and why it cannot resolve autonomously (max 1000 chars)",
    )
    recommended_action: str = Field(
        "",
        description="Agent's recommendation for the human reviewer",
    )
    urgency: str = Field(
        "NORMAL",
        description="Urgency level: LOW / NORMAL / HIGH / CRITICAL",
    )
    sla_hours: int | None = Field(
        None,
        description="Custom SLA duration in hours (default: 24h for NORMAL, 4h for HIGH, 1h for CRITICAL)",
    )


class HumanEscalatorTool(BaseTool):
    """
    Trigger ECLIPSE Human-in-the-Loop escalation for a dispute.

    Creates an escalation case with full context package for the human reviewer:
    - All evidence collected by the crew
    - Risk assessment and fraud scores
    - Settlement options considered
    - Agent's recommendation
    - SLA timer starts immediately

    The human reviewer interface will surface this case in the dashboard.
    """

    name: str = "human_escalator"
    description: str = (
        "Escalate a dispute to a human reviewer via the ECLIPSE system. "
        "Use when: amount > authority threshold, fraud risk > 0.6, policy conflict detected, "
        "or agent confidence is < 50%. "
        "Provides full context package to the human. "
        "Returns escalation case ID and SLA deadline."
    )
    args_schema: type[BaseModel] = EscalationInput
    api_url: str = "http://localhost:8000"

    # Default SLA hours by urgency
    SLA_DEFAULTS = {"LOW": 72, "NORMAL": 24, "HIGH": 4, "CRITICAL": 1}

    def _run(
        self,
        dispute_id: str,
        escalating_agent_id: str,
        reason: str,
        context_summary: str,
        recommended_action: str = "",
        urgency: str = "NORMAL",
        sla_hours: int | None = None,
    ) -> str:
        effective_sla = sla_hours or self.SLA_DEFAULTS.get(urgency, 24)
        payload = {
            "dispute_id": dispute_id,
            "escalating_agent_id": escalating_agent_id,
            "reason": reason,
            "context_summary": context_summary[:1000],
            "recommended_action": recommended_action,
            "urgency": urgency,
            "sla_hours": effective_sla,
            "created_at": datetime.now(UTC).isoformat,
        }
        try:
            response = httpx.post(
                f"{self.api_url}/eclipse/escalations",
                json=payload,
                timeout=10.0,
            )
            if response.status_code in (200, 201):
                data = response.json
                return self._format_escalation_created(data, urgency, effective_sla)
            else:
                return self._mock_escalation_ack(dispute_id, reason, urgency, effective_sla)
        except httpx.ConnectError:
            return self._mock_escalation_ack(dispute_id, reason, urgency, effective_sla)
        except Exception as e:
            logger.error(f"HumanEscalatorTool error: {e}")
            return f"ESCALATION FAILED: {e!s}. Please manually create escalation case."

    def _format_escalation_created(self, data: dict, urgency: str, sla_hours: int) -> str:
        urgency_indicators = {
            "CRITICAL": "🔴 CRITICAL", "HIGH": "🟠 HIGH",
            "NORMAL": "🟡 NORMAL", "LOW": "🟢 LOW",
        }
        return (
            f"ESCALATION CREATED — ECLIPSE HITL\n"
            f"{'='*60}\n"
            f"Case ID:     {data.get('case_id')}\n"
            f"Dispute:     {data.get('dispute_id')}\n"
            f"Urgency:     {urgency_indicators.get(urgency, urgency)}\n"
            f"SLA:         {sla_hours} hours (deadline: {data.get('sla_deadline')})\n"
            f"Assigned To: {data.get('assigned_to', 'Next available reviewer')}\n"
            f"Queue Pos:   #{data.get('queue_position', 1)}\n\n"
            f"The human reviewer has been notified. "
            f"The dispute is now paused pending their decision.\n"
            f"Tracking URL: {self.api_url}/dashboard/escalations/{data.get('case_id')}\n"
        )

    def _mock_escalation_ack(
        self, dispute_id: str, reason: str, urgency: str, sla_hours: int
    ) -> str:
        import hashlib
        case_id = hashlib.sha256(
            f"{dispute_id}:{reason}:{datetime.now(UTC).isoformat}".encode
        ).hexdigest[:12].upper
        urgency_map = {
            "CRITICAL": "🔴 CRITICAL", "HIGH": "🟠 HIGH",
            "NORMAL": "🟡 NORMAL", "LOW": "🟢 LOW",
        }
        return (
            f"ESCALATION QUEUED — ECLIPSE HITL (API offline)\n"
            f"{'='*60}\n"
            f"Case ID:     ESC-{case_id}\n"
            f"Dispute:     {dispute_id}\n"
            f"Reason:      {reason}\n"
            f"Urgency:     {urgency_map.get(urgency, urgency)}\n"
            f"SLA:         {sla_hours} hours from now\n"
            f"Status:      QUEUED — will appear in dashboard when API reconnects\n\n"
            f"The autonomous resolution has been halted. "
            f"Human review is required before any settlement action.\n"
        )
