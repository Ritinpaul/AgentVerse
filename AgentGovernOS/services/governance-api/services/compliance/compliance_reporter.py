"""
Compliance Reporter

Aggregates data from AgentGovernOS databases (decisions, agents, policies)
and renders evidence packages into Markdown templates (e.g., EU AI Act, ISO 42001).
"""

import os
from datetime import UTC, datetime
from typing import Any

import jinja2
from models import Agent, Decision, Policy
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

class ComplianceReporter:
    def __init__(self):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

    async def gather_metrics(self, db: AsyncSession, scope: str = "global") -> dict[str, Any]:
        """
        Gathers broad metrics from the database for the compliance reports.
        """
        # Count total decisions
        res_decisions = await db.execute(select(func.count(Decision.id)))
        total_decisions = res_decisions.scalar_one

        # Count total escalations
        # In a real implementation this might look at EscalationCase, but here we count decision_type="escalation"
        # or checking total_escalations on agents.
        res_esc = await db.execute(select(func.sum(Agent.total_escalations)))
        total_escalations = res_esc.scalar_one or 0
        
        # High-risk agents (Tier 1 & Tier 2)
        res_hr = await db.execute(select(Agent).where(Agent.tier.in_(["T1", "T2"])))
        hr_agents = res_hr.scalars.all

        # Active policies
        res_pol = await db.execute(select(func.count(Policy.id)).where(Policy.is_active == True))
        active_policies = res_pol.scalar_one

        # Violations (extracting from decision policy_violations JSON array length > 0)
        # Simplified to a dummy count for this demo
        total_violations = 0
        
        return {
            "generated_at": datetime.now(UTC).isoformat,
            "scope": scope,
            "total_decisions": total_decisions,
            "total_escalations": total_escalations,
            "active_policies": active_policies,
            "total_violations": total_violations,
            "has_high_risk": len(hr_agents) > 0,
            "high_risk_agents": [{"did": a.did, "role": a.role} for a in hr_agents],
            "violations": [],
            "integrity_pct": 100.0 # From audit_ledger verify_chain in full implementation
        }

    async def generate_report(self, framework: str, db: AsyncSession, scope: str = "global") -> str:
        """
        Generates a markdown report for the given framework.
        Supported frameworks: 'eu_ai_act', 'iso_42001'
        """
        metrics = await self.gather_metrics(db, scope)
        
        template_name = f"{framework}.md.j2"
        try:
            template = self.env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise ValueError(f"Compliance framework template '{framework}' not found.")
            
        return template.render(**metrics)
