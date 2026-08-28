"""
Tool: Prophecy Simulator — run 3-path Monte Carlo future simulation.

Used by: Governance Sentinel, Negotiation Strategist agents.
"""

import logging
import random

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProphecyInput(BaseModel):
    dispute_id: str = Field(..., description="Dispute ID to simulate outcomes for")
    proposed_settlement_amount: float = Field(..., description="Proposed settlement amount (INR)")
    invoice_amount: float = Field(..., description="Original invoice amount (INR)")
    customer_id: str = Field(..., description="Customer ID")
    risk_score: float = Field(..., description="Risk score (0.0-1.0)")
    fraud_risk_score: float = Field(0.0, description="Fraud risk score (0.0-1.0)")
    simulations: int = Field(1000, description="Number of Monte Carlo iterations (100-10000)")


class ProphecySimulatorTool(BaseTool):
    """
    Run the Prophecy Engine — 3-path Monte Carlo simulation.

    Simulates 3 decision paths and their probabilistic outcomes:
    1. AUTO-EXECUTE: Accept the proposed settlement automatically
    2. MODIFIED: Negotiate to a different amount
    3. ESCALATE: Send to human reviewer

    Returns probability distribution, expected financial outcomes,
    relationship impact scores, and the recommended path.
    """

    name: str = "prophecy_simulator"
    description: str = (
        "Simulate future outcomes for 3 resolution paths using Monte Carlo analysis. "
        "Paths: AUTO-EXECUTE (accept settlement), MODIFIED (renegotiate), ESCALATE (human). "
        "Returns probability and expected financial outcome for each path. "
        "Run before making final resolution decision to select the optimal path."
    )
    args_schema: type[BaseModel] = ProphecyInput
    api_url: str = "http://localhost:8000"

    def _run(
        self,
        dispute_id: str,
        proposed_settlement_amount: float,
        invoice_amount: float,
        customer_id: str,
        risk_score: float,
        fraud_risk_score: float = 0.0,
        simulations: int = 1000,
    ) -> str:
        try:
            response = httpx.post(
                f"{self.api_url}/sentinel/prophecy",
                json={
                    "dispute_id": dispute_id,
                    "proposed_settlement_amount": proposed_settlement_amount,
                    "invoice_amount": invoice_amount,
                    "customer_id": customer_id,
                    "risk_score": risk_score,
                    "fraud_risk_score": fraud_risk_score,
                    "simulations": simulations,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                return self._format_prophecy(response.json)
            else:
                return self._local_simulation(
                    dispute_id, proposed_settlement_amount, invoice_amount,
                    risk_score, fraud_risk_score, simulations,
                )
        except httpx.ConnectError:
            return self._local_simulation(
                dispute_id, proposed_settlement_amount, invoice_amount,
                risk_score, fraud_risk_score, simulations,
            )
        except Exception as e:
            logger.error(f"ProphecySimulatorTool error: {e}")
            return f"Simulation error: {e!s}"

    def _format_prophecy(self, data: dict) -> str:
        paths = data.get("paths", [])
        result = (
            f"PROPHECY ENGINE — {data.get('simulations', 0):,} simulations\n"
            f"Dispute: {data.get('dispute_id')}\n"
            f"{'='*60}\n\n"
        )
        for path in paths:
            result += (
                f"PATH: {path.get('name')}\n"
                f"  Probability:          {path.get('probability_pct'):.1f}%\n"
                f"  Expected Financial:   ₹{path.get('expected_financial_outcome', 0):,.2f}\n"
                f"  Customer Retention:   {path.get('retention_probability_pct'):.1f}%\n"
                f"  Escalation Cost:      ₹{path.get('escalation_cost', 0):,.2f}\n"
                f"  Confidence Interval:  {path.get('ci_low', 0):.1f}% – {path.get('ci_high', 0):.1f}%\n\n"
            )
        result += f"RECOMMENDED PATH: {data.get('recommended_path')}\n"
        result += f"RATIONALE: {data.get('rationale')}\n"
        return result

    def _local_simulation(
        self,
        dispute_id: str,
        proposed: float,
        invoice: float,
        risk: float,
        fraud_risk: float,
        n: int,
    ) -> str:
        """Lightweight local Monte Carlo — runs when Prophecy Engine API is offline."""
        rng = random.Random(hash(dispute_id) % (2**31))

        # ── Path 1: Auto-Execute ──
        auto_outcomes = []
        for _ in range(n):
            outcome_var = rng.gauss(0, proposed * 0.1)
            fraud_hit = proposed * 2 if rng.random < fraud_risk * 0.3 else 0
            auto_outcomes.append(proposed + outcome_var + fraud_hit)
        auto_mean = sum(auto_outcomes) / n
        auto_prob = max(10, 80 - risk * 50 - fraud_risk * 30)

        # ── Path 2: Modified ──
        modified_amount = proposed * (0.6 + risk * 0.2)
        mod_outcomes = [modified_amount + rng.gauss(0, modified_amount * 0.08) for _ in range(n)]
        mod_mean = sum(mod_outcomes) / n
        mod_prob = max(20, 60 + risk * 10)

        # ── Path 3: Escalate ──
        escalation_cost = 5000 + invoice * 0.02
        esc_outcomes = [proposed * 0.7 + rng.gauss(0, proposed * 0.15) + escalation_cost for _ in range(n)]
        esc_mean = sum(esc_outcomes) / n
        esc_prob = 100 - auto_prob - mod_prob

        # Normalize probs
        total_prob = auto_prob + mod_prob + esc_prob
        auto_prob /= total_prob / 100
        mod_prob /= total_prob / 100
        esc_prob /= total_prob / 100

        # Recommendation
        if fraud_risk > 0.6:
            recommended = "PATH 3: ESCALATE — High fraud risk requires human verification"
        elif risk > 0.7:
            recommended = "PATH 2: MODIFIED — Renegotiate to reduce financial exposure"
        else:
            recommended = "PATH 2: MODIFIED — Balanced resolution preserves relationship"

        return (
            f"PROPHECY ENGINE — {n:,} local simulations\n"
            f"Dispute: {dispute_id} | Risk: {risk:.2f} | Fraud Risk: {fraud_risk:.2f}\n"
            f"{'='*60}\n\n"
            f"PATH 1: AUTO-EXECUTE (accept ₹{proposed:,.2f})\n"
            f"  Probability:          {auto_prob:.1f}%\n"
            f"  Expected Cost:        ₹{auto_mean:,.2f}\n"
            f"  Customer Retention:   {max(60, 95 - risk * 30):.1f}%\n"
            f"  Risk: High if fraud score elevated\n\n"
            f"PATH 2: MODIFIED (negotiate to ₹{modified_amount:,.2f})\n"
            f"  Probability:          {mod_prob:.1f}%\n"
            f"  Expected Cost:        ₹{mod_mean:,.2f}\n"
            f"  Customer Retention:   {max(50, 85 - risk * 20):.1f}%\n"
            f"  Risk: Customer may reject — 2nd negotiation round needed\n\n"
            f"PATH 3: ESCALATE TO HUMAN\n"
            f"  Probability:          {esc_prob:.1f}%\n"
            f"  Expected Cost:        ₹{esc_mean:,.2f} (incl. ₹{escalation_cost:,.2f} ops cost)\n"
            f"  Customer Retention:   {max(40, 75 - risk * 25):.1f}%\n"
            f"  Risk: Delay → customer dissatisfaction; benefit: full human oversight\n\n"
            f"RECOMMENDED PATH: {recommended}\n"
        )
