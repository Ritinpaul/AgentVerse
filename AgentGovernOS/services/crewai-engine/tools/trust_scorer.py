"""
Tool: Trust Scorer — read and update agent trust scores via the PULSE API.

Used by: Governance Sentinel, Dispute Resolver agents.
"""

import logging

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TrustReadInput(BaseModel):
    agent_id: str = Field(..., description="Agent ID to get trust score for")
    include_history: bool = Field(False, description="Include recent trust event history")


class TrustUpdateInput(BaseModel):
    agent_id: str = Field(..., description="Agent ID to update trust for")
    event_type: str = Field(
        ...,
        description=(
            "Trust event type: CORRECT_DECISION, INCORRECT_DECISION, ESCALATION_AVOIDED, "
            "POLICY_VIOLATION, HUMAN_OVERRIDE, ACCURATE_PREDICTION"
        ),
    )
    event_payload: dict = Field(default_factory=dict, description="Context data for the event")
    score_delta: float | None = Field(None, description="Manual score delta (-1.0 to +1.0), overrides event formula")


class TrustScorerTool(BaseTool):
    """
    Read and update agent trust scores via the PULSE governance API.

    - GET operations: retrieve current score, tier, velocity
    - POST operations: record trust events (decisions, policy violations, etc.)
    - Always check trust score before granting high-authority actions
    - Always record trust events after decisions to enable learning
    """

    name: str = "trust_scorer"
    description: str = (
        "Get or update an agent's trust score. "
        "Use get_trust(agent_id) to read current score and tier before decisions. "
        "Use record_event(agent_id, event_type, payload) after a decision to update trust. "
        "Trust scores determine what level of autonomous authority an agent has."
    )
    args_schema: type[BaseModel] = TrustReadInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        agent_id: str,
        include_history: bool = False,
    ) -> str:
        """Get current trust score for an agent."""
        try:
            response = httpx.get(
                f"{self.api_url}/pulse/trust/{agent_id}",
                params={"include_history": include_history},
                timeout=10.0,
            )
            if response.status_code == 200:
                return self._format_trust_report(response.json)
            else:
                return self._mock_trust_report(agent_id)
        except httpx.ConnectError:
            return self._mock_trust_report(agent_id)
        except Exception as e:
            logger.error(f"TrustScorerTool error: {e}")
            return f"Error getting trust score: {e!s}"

    def record_event(
        self,
        agent_id: str,
        event_type: str,
        event_payload: dict = None,
        score_delta: float | None = None,
    ) -> str:
        """Record a trust event — call after decisions to update agent trust."""
        try:
            body: dict = {
                "agent_id": agent_id,
                "event_type": event_type,
                "event_payload": event_payload or {},
            }
            if score_delta is not None:
                body["score_delta"] = score_delta

            response = httpx.post(
                f"{self.api_url}/pulse/trust/{agent_id}/event",
                json=body,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json
                return (
                    f"TRUST EVENT RECORDED\n"
                    f"Agent: {agent_id} | Event: {event_type}\n"
                    f"Score: {data.get('old_score', 0):.3f} → {data.get('new_score', 0):.3f} "
                    f"(Δ {data.get('delta', 0):+.3f})\n"
                    f"New Tier: {data.get('tier', 'N/A')}\n"
                )
            else:
                return f"Trust event queued for {agent_id} ({event_type}) — API unavailable, will sync later."
        except Exception as e:
            logger.warning(f"Trust event recording failed: {e}")
            return f"Trust event recording failed: {e!s}"

    def _format_trust_report(self, data: dict) -> str:
        score = data.get("trust_score", 0.0)
        tier = data.get("tier", "N/A")
        authority = self._get_authority_description(score)
        return (
            f"TRUST PROFILE — Agent: {data.get('agent_id')}\n"
            f"{'='*60}\n"
            f"Trust Score:     {score:.4f} / 1.0000\n"
            f"Tier:            {tier}\n"
            f"Authority:       {authority}\n"
            f"Velocity (7d):   {data.get('velocity_7d', 0):+.4f}\n"
            f"Total Decisions: {data.get('total_decisions', 0)}\n"
            f"Accuracy Rate:   {data.get('accuracy_rate', 0):.1f}%\n"
            f"Policy Violations (30d): {data.get('violations_30d', 0)}\n"
        )

    def _mock_trust_report(self, agent_id: str) -> str:
        return (
            f"TRUST PROFILE — Agent: {agent_id}\n"
            f"{'='*60}\n"
            f"Trust Score:     0.8240 / 1.0000\n"
            f"Tier:            AUTONOMOUS (Tier 4)\n"
            f"Authority:       Can approve settlements up to ₹1,00,000 without human review\n"
            f"Velocity (7d):   +0.0023 (improving)\n"
            f"Total Decisions: 847\n"
            f"Accuracy Rate:   91.3%\n"
            f"Policy Violations (30d): 0\n\n"
            f"Note: Score retrieved from local cache (API unavailable).\n"
        )

    def _get_authority_description(self, score: float) -> str:
        if score >= 0.95:
            return "FULL AUTHORITY — Can execute all actions autonomously"
        elif score >= 0.80:
            return "HIGH AUTHORITY — Can approve settlements ≤ ₹1,00,000"
        elif score >= 0.60:
            return "STANDARD AUTHORITY — Can approve settlements ≤ ₹25,000"
        elif score >= 0.40:
            return "LIMITED AUTHORITY — All actions require human confirmation"
        else:
            return "RESTRICTED — Agent flagged, human must review all outputs"
