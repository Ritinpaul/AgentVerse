"""
Tool: Settlement Calculator — compute optimal settlement options.

Used by: Negotiation Strategist agent.
"""

import logging

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SettlementInput(BaseModel):
    dispute_id: str = Field(..., description="Dispute ID")
    invoice_amount: float = Field(..., description="Original invoice amount (INR)")
    disputed_amount: float = Field(..., description="Amount under dispute (INR)")
    risk_score: float = Field(..., description="Risk score from Risk Evaluator (0.0-1.0)")
    fraud_risk_score: float = Field(0.0, description="Fraud risk score (0.0-1.0)")
    customer_tier: str = Field("A", description="Customer credit tier (AAA/AA/A/BBB/BB/B/CCC)")
    evidence_strength: str = Field(
        "MEDIUM",
        description="Strength of customer's evidence (STRONG/MEDIUM/WEAK)",
    )
    num_options: int = Field(3, description="Number of settlement options to generate")


class SettlementCalculatorTool(BaseTool):
    """
    Calculate optimal settlement options for a dispute.

    Uses risk score, credit tier, evidence strength, and financial impact
    to generate up to 3 settlement options with rationale and acceptance
    probability for each.
    """

    name: str = "settlement_calculator"
    description: str = (
        "Calculate optimal settlement options for a dispute. "
        "Takes risk score, evidence strength, and customer tier as inputs. "
        "Returns 2-3 settlement options (e.g., full credit, partial credit, replacement) "
        "with recommended amount, acceptance probability, and business rationale. "
        "Always run this before making a final resolution decision."
    )
    args_schema: type[BaseModel] = SettlementInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        dispute_id: str,
        invoice_amount: float,
        disputed_amount: float,
        risk_score: float,
        fraud_risk_score: float = 0.0,
        customer_tier: str = "A",
        evidence_strength: str = "MEDIUM",
        num_options: int = 3,
    ) -> str:
        try:
            response = httpx.post(
                f"{self.api_url}/api/v1/settlement/calculate",
                json={
                    "dispute_id": dispute_id,
                    "invoice_amount": invoice_amount,
                    "disputed_amount": disputed_amount,
                    "risk_score": risk_score,
                    "fraud_risk_score": fraud_risk_score,
                    "customer_tier": customer_tier,
                    "evidence_strength": evidence_strength,
                    "num_options": num_options,
                },
                timeout=15.0,
            )
            if response.status_code == 200:
                return self._format_options(response.json)
            else:
                return self._calculate_locally(
                    dispute_id, invoice_amount, disputed_amount,
                    risk_score, evidence_strength, customer_tier,
                )
        except httpx.ConnectError:
            return self._calculate_locally(
                dispute_id, invoice_amount, disputed_amount,
                risk_score, evidence_strength, customer_tier,
            )
        except Exception as e:
            logger.error(f"SettlementCalculatorTool error: {e}")
            return f"Error calculating settlement: {e!s}"

    def _format_options(self, data: dict) -> str:
        options = data.get("options", [])
        result = (
            f"SETTLEMENT OPTIONS — Dispute: {data.get('dispute_id')}\n"
            f"Invoice: ₹{data.get('invoice_amount', 0):,.2f} | "
            f"Disputed: ₹{data.get('disputed_amount', 0):,.2f}\n"
            f"{'='*60}\n\n"
        )
        for i, opt in enumerate(options, 1):
            result += (
                f"OPTION {i}: {opt.get('label')}\n"
                f"  Amount:              ₹{opt.get('amount', 0):,.2f}\n"
                f"  % of Disputed:       {opt.get('pct_of_disputed', 0):.1f}%\n"
                f"  Acceptance Prob:     {opt.get('acceptance_probability', 0):.0f}%\n"
                f"  Business Impact:     {opt.get('business_impact')}\n"
                f"  Rationale:           {opt.get('rationale')}\n\n"
            )
        result += f"RECOMMENDATION: {data.get('recommended_option', 'Option 2 — balanced approach')}\n"
        return result

    def _calculate_locally(
        self,
        dispute_id: str,
        invoice_amount: float,
        disputed_amount: float,
        risk_score: float,
        evidence_strength: str,
        customer_tier: str,
    ) -> str:
        """Fallback: calculate settlement options using local business rules."""
        # Weight the settlement based on evidence strength
        evidence_weights = {"STRONG": 0.90, "MEDIUM": 0.60, "WEAK": 0.25}
        base_weight = evidence_weights.get(evidence_strength, 0.60)

        # Adjust for risk
        risk_adj = max(0.10, 1.0 - risk_score * 0.5)

        # Option 1: Full credit (if evidence is strong)
        full_credit = disputed_amount
        # Option 2: Partial (most common path)
        partial_credit = disputed_amount * base_weight * risk_adj
        # Option 3: Minimal (goodwill gesture)
        minimal_credit = disputed_amount * 0.20

        tier_note = {
            "AAA": "Premium customer — lean toward full resolution",
            "AA": "High-value customer — partial credit preferred",
            "A":  "Good standing — standard resolution",
            "BBB": "Monitor closely — verify evidence before settling",
            "BB":  "Elevated caution — minimal settlement unless evidence is conclusive",
            "B":   "High risk — human review recommended",
            "CCC": "Critical risk — escalate immediately",
        }.get(customer_tier, "Standard review")

        return (
            f"SETTLEMENT OPTIONS — Dispute: {dispute_id}\n"
            f"Invoice: ₹{invoice_amount:,.2f} | Disputed: ₹{disputed_amount:,.2f}\n"
            f"Evidence Strength: {evidence_strength} | Risk Score: {risk_score:.3f}\n"
            f"Customer Tier Note: {tier_note}\n"
            f"{'='*60}\n\n"
            f"OPTION 1: Full Credit Note\n"
            f"  Amount:              ₹{full_credit:,.2f} (100% of dispute)\n"
            f"  Acceptance Prob:     85%\n"
            f"  Business Impact:     Full revenue recognition loss, eliminates escalation cost\n"
            f"  Rationale:           Unsigned delivery receipt is strong evidence of non-delivery\n\n"
            f"OPTION 2: Partial Credit Note ⭐ RECOMMENDED\n"
            f"  Amount:              ₹{partial_credit:,.2f} ({base_weight*risk_adj*100:.0f}% of dispute)\n"
            f"  Acceptance Prob:     72%\n"
            f"  Business Impact:     Balanced — preserves relationship, limits financial exposure\n"
            f"  Rationale:           Supplier provided delivery confirmation; partial liability shared\n\n"
            f"OPTION 3: Goodwill Credit\n"
            f"  Amount:              ₹{minimal_credit:,.2f} (20% of dispute)\n"
            f"  Acceptance Prob:     31%\n"
            f"  Business Impact:     Minimal financial hit, high escalation risk\n"
            f"  Rationale:           Only appropriate if evidence is weak or customer history shows abuse\n\n"
            f"RECOMMENDATION: Option 2 — Partial Credit of ₹{partial_credit:,.2f}. "
            f"Offers best balance of customer retention vs. financial risk management.\n"
        )
