"""
Dispute Resolution Crew — Core 5-agent crew that runs per dispute.

Hierarchy: Sentinel (manager) → Evidence → Risk → Negotiation → Resolver
Process: Hierarchical — Sentinel oversees all task execution.
"""

from agents.core_crew import (
    create_dispute_resolver,
    create_evidence_collector,
    create_governance_sentinel,
    create_negotiation_strategist,
    create_risk_evaluator,
)
from crewai import Crew, Process, Task


class DisputeResolutionCrew:
    """The Core Crew: 5 agents that process a dispute case end-to-end."""

    def __init__(self):
        self.evidence_collector = create_evidence_collector
        self.risk_evaluator = create_risk_evaluator
        self.negotiation_strategist = create_negotiation_strategist
        self.dispute_resolver = create_dispute_resolver
        self.governance_sentinel = create_governance_sentinel

    def build_crew(self, dispute: dict) -> Crew:
        """Build a crew instance with tasks tailored to the dispute."""
        tasks = self._create_tasks(dispute)

        return Crew(
            agents=[
                self.evidence_collector,
                self.risk_evaluator,
                self.negotiation_strategist,
                self.dispute_resolver,
                self.governance_sentinel,
            ],
            tasks=tasks,
            process=Process.hierarchical,
            manager_agent=self.governance_sentinel,
            memory=True,
            embedder={
                "provider": "ollama",
                "config": {"model": "nomic-embed-text"},
            },
            verbose=True,
            full_output=True,
            output_log_file="logs/dispute_crew.log",
        )

    def _create_tasks(self, dispute: dict) -> list[Task]:
        """Build the sequential task chain for dispute resolution."""
        dispute_desc = dispute.get("description", "Unknown dispute")
        customer_id = dispute.get("customer_id", "Unknown")
        amount = dispute.get("amount", 0)

        t1 = Task(
            description=(
                f"Collect all evidence for dispute: {dispute_desc}\n"
                f"Customer: {customer_id}\n"
                f"Amount: ₹{amount:,.2f}\n\n"
                "Gather: invoices, POs, delivery receipts, contracts, comms logs.\n"
                "Verify document authenticity. Build evidence timeline.\n"
                "Flag any missing or suspicious documents."
            ),
            agent=self.evidence_collector,
            expected_output="Complete evidence package with document list, timeline, and verification status",
        )

        t2 = Task(
            description=(
                f"Assess financial risk for customer {customer_id}.\n"
                f"Dispute amount: ₹{amount:,.2f}\n\n"
                "Evaluate: credit score, payment history, fraud indicators, industry risk.\n"
                "Compute risk score (0.0 to 1.0). List all red flags found."
            ),
            agent=self.risk_evaluator,
            expected_output="Risk assessment: score (0-1), red flags list, credit evaluation",
            context=[t1],
        )

        t3 = Task(
            description=(
                "Propose optimal settlement strategy based on evidence and risk.\n\n"
                "Provide 3 options:\n"
                "  Option A (Conservative): Minimize company exposure\n"
                "  Option B (Balanced): Fair to both parties\n"
                "  Option C (Aggressive): Maximize customer retention\n\n"
                "Include financial impact, customer relationship impact, and precedent risk."
            ),
            agent=self.negotiation_strategist,
            expected_output="3 settlement options with financial impact analysis",
            context=[t1, t2],
        )

        t4 = Task(
            description=(
                "Make the FINAL resolution decision.\n\n"
                f"Your authority limit: check your trust tier.\n"
                f"Dispute amount: ₹{amount:,.2f}\n\n"
                "Based on evidence, risk assessment, and settlement options:\n"
                "  1. Select best settlement option (A/B/C) with justification\n"
                "  2. If amount exceeds your authority → ESCALATE to human\n"
                "  3. If confidence < 0.70 → ESCALATE to human\n"
                "  4. Document ALL reasoning for the audit trail\n\n"
                "Output: {decision, confidence, reasoning, escalation_needed}"
            ),
            agent=self.dispute_resolver,
            expected_output="Final decision JSON: {decision, confidence, reasoning, escalation_needed}",
            context=[t1, t2, t3],
        )

        return [t1, t2, t3, t4]

    async def resolve(self, dispute: dict) -> dict:
        """Execute the full dispute resolution pipeline."""
        crew = self.build_crew(dispute)
        result = crew.kickoff(inputs=dispute)
        return {
            "raw": str(result),
            "tasks_output": [str(t.output) for t in result.tasks_output] if hasattr(result, "tasks_output") else [],
            "token_usage": result.token_usage if hasattr(result, "token_usage") else {},
        }
