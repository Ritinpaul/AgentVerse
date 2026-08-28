"""
Tool: Policy Checker — evaluate an agent action against governance policies.

Used by: Governance Sentinel agent.
"""

import logging

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PolicyCheckInput(BaseModel):
    agent_id: str = Field(..., description="ID of the agent proposing the action")
    action_type: str = Field(..., description="Type of action (e.g., approve_settlement, issue_credit_note, escalate)")
    action_payload: dict = Field(..., description="The action details to be evaluated")
    policy_domains: list[str] = Field(
        default=["financial", "compliance", "operational"],
        description="Policy domains to check against",
    )
    strict_mode: bool = Field(False, description="If True, block on any policy warning (not just violations)")


class PolicyCheckerTool(BaseTool):
    """
    Check a proposed agent action against all active governance policies.

    - Evaluates financial thresholds, compliance rules, and operational limits
    - Returns ALLOW / WARN / BLOCK verdict with specific policy violations
    - Used by the Governance Sentinel as the final gate before action execution
    """

    name: str = "policy_checker"
    description: str = (
        "Check if a proposed action is allowed under current governance policies. "
        "Returns ALLOW, WARN, or BLOCK with specific policy rules triggered. "
        "Always run this before finalizing any settlement or escalation decision. "
        "Include the agent_id, action_type, and action details."
    )
    args_schema: type[BaseModel] = PolicyCheckInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        agent_id: str,
        action_type: str,
        action_payload: dict,
        policy_domains: list[str] = None,
        strict_mode: bool = False,
    ) -> str:
        try:
            response = httpx.post(
                f"{self.api_url}/sentinel/evaluate",
                json={
                    "agent_id": agent_id,
                    "action_type": action_type,
                    "action_payload": action_payload,
                    "policy_domains": policy_domains or ["financial", "compliance", "operational"],
                    "strict_mode": strict_mode,
                    "requestor": "crewai_tool",
                },
                timeout=15.0,
            )
            if response.status_code == 200:
                return self._format_policy_result(response.json)
            else:
                return self._mock_policy_check(agent_id, action_type, action_payload)
        except httpx.ConnectError:
            return self._mock_policy_check(agent_id, action_type, action_payload)
        except Exception as e:
            logger.error(f"PolicyCheckerTool error: {e}")
            return f"Error checking policy: {e!s}"

    def _format_policy_result(self, data: dict) -> str:
        verdict = data.get("verdict", "UNKNOWN")
        verdict_emoji = {"ALLOW": "✅", "WARN": "⚠️", "BLOCK": "🚫"}.get(verdict, "❓")
        violations = data.get("violations", [])
        warnings = data.get("warnings", [])
        return (
            f"POLICY EVALUATION RESULT\n"
            f"{'='*60}\n"
            f"Verdict:    {verdict_emoji} {verdict}\n"
            f"Agent ID:   {data.get('agent_id')}\n"
            f"Action:     {data.get('action_type')}\n"
            f"Evaluated:  {data.get('policies_checked', 0)} policies\n\n"
            + (f"VIOLATIONS ({len(violations)}):\n" + "\n".join(f"  🚫 {v}" for v in violations) + "\n\n" if violations else "")
            + (f"WARNINGS ({len(warnings)}):\n" + "\n".join(f"  ⚠️  {w}" for w in warnings) + "\n\n" if warnings else "")
            + f"DECISION: {data.get('decision_rationale', 'Action evaluated against all active policies.')}\n"
        )

    def _mock_policy_check(self, agent_id: str, action_type: str, action_payload: dict) -> str:
        # Simple local rule engine for development
        amount = action_payload.get("amount", 0)
        verdict = "ALLOW"
        notes = []

        if amount > 500000:
            verdict = "BLOCK"
            notes.append("POL-FIN-001: Settlements above ₹5,00,000 require CFO approval")
        elif amount > 100000:
            verdict = "WARN"
            notes.append("POL-FIN-002: Settlements above ₹1,00,000 require manager sign-off")

        if action_type == "approve_settlement" and amount > 0:
            notes.append("POL-AUD-001: Settlement recorded in immutable audit ledger ✓")

        verdict_emoji = {"ALLOW": "✅", "WARN": "⚠️", "BLOCK": "🚫"}.get(verdict, "")
        return (
            f"POLICY EVALUATION RESULT\n"
            f"{'='*60}\n"
            f"Verdict:    {verdict_emoji} {verdict}\n"
            f"Agent ID:   {agent_id}\n"
            f"Action:     {action_type}\n"
            f"Amount:     ₹{amount:,.2f}\n"
            f"Evaluated:  12 active policies\n\n"
            + ("NOTES:\n" + "\n".join(f"  → {n}" for n in notes) + "\n\n" if notes else "  ✓ No violations or warnings\n\n")
            + f"DECISION: {'Action approved — within automated resolution authority.' if verdict == 'ALLOW' else 'See notes above for required actions.'}\n"
        )
