"""
Compliance Report Generator — auto-generates regulatory compliance reports.

Takes the ANCESTOR decision ledger and produces structured compliance
reports aligned to specific regulatory frameworks:

  - SOX (Sarbanes-Oxley): Financial controls audit trail
  - EU AI Act Article 14: Human oversight and transparency
  - GDPR Article 22: Automated decision-making accountability
  - Internal Audit: Custom enterprise compliance checks

Reports are generated on-demand or scheduled via Celery.
They aggregate data from:
  - ANCESTOR decision chain (decisions + hash verification)
  - PULSE trust events (trust score trajectory)
  - SENTINEL policy enforcement logs (violations, blocks, escalations)
  - GENESIS agent registry (agent roster, DNA integrity)
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


FRAMEWORK_TEMPLATES = {
    "sox": {
        "name": "SOX Compliance Report",
        "description": "Sarbanes-Oxley financial controls audit",
        "sections": [
            "decision_trail_integrity",
            "financial_authorization_summary",
            "policy_enforcement_log",
            "escalation_review",
            "approval_chain_verification",
        ],
    },
    "eu_ai_act": {
        "name": "EU AI Act Article 14 — Human Oversight Report",
        "description": "Demonstrating human oversight of autonomous AI decisions",
        "sections": [
            "human_override_summary",
            "escalation_effectiveness",
            "transparency_metrics",
            "risk_classification",
            "explainability_audit",
        ],
    },
    "gdpr": {
        "name": "GDPR Article 22 — Automated Decision-Making Report",
        "description": "Right to explanation and meaningful information about automated logic",
        "sections": [
            "automated_decision_inventory",
            "reasoning_trace_availability",
            "human_intervention_rate",
            "data_retention_compliance",
        ],
    },
    "internal": {
        "name": "Internal Governance Audit Report",
        "description": "Enterprise-specific AI governance health check",
        "sections": [
            "agent_fleet_health",
            "trust_score_distribution",
            "policy_violation_summary",
            "cache_efficiency",
            "dna_integrity_audit",
        ],
    },
}


@dataclass
class ComplianceMetric:
    """A single metric within a compliance report section."""
    name: str
    value: any
    status: str = "pass"       # pass | warn | fail
    threshold: any = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "status": self.status,
            "threshold": self.threshold,
            "description": self.description,
        }


@dataclass
class ComplianceSection:
    """A section of a compliance report."""
    id: str
    title: str
    metrics: list[ComplianceMetric] = field(default_factory=list)
    finding: str = ""     # Overall finding for this section
    risk_level: str = "low"  # low | medium | high | critical

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "metrics": [m.to_dict for m in self.metrics],
            "finding": self.finding,
            "risk_level": self.risk_level,
            "pass_count": sum(1 for m in self.metrics if m.status == "pass"),
            "fail_count": sum(1 for m in self.metrics if m.status == "fail"),
        }


@dataclass
class ComplianceReport:
    """A complete compliance report."""
    framework: str
    framework_name: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    period_start: datetime | None = None
    period_end: datetime | None = None
    sections: list[ComplianceSection] = field(default_factory=list)
    overall_status: str = "pass"
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "framework": self.framework,
            "framework_name": self.framework_name,
            "generated_at": self.generated_at.isoformat,
            "period": {
                "start": self.period_start.isoformat if self.period_start else None,
                "end": self.period_end.isoformat if self.period_end else None,
            },
            "overall_status": self.overall_status,
            "summary": self.summary,
            "sections": [s.to_dict for s in self.sections],
            "recommendations": self.recommendations,
            "score": self.compliance_score,
        }

    @property
    def compliance_score(self) -> float:
        """Overall compliance score: 0.0–100.0."""
        if not self.sections:
            return 100.0
        total = sum(len(s.metrics) for s in self.sections)
        passing = sum(s.to_dict["pass_count"] for s in self.sections)
        return round((passing / total * 100) if total > 0 else 100.0, 1)


class ComplianceReportGenerator:
    """
    Generates compliance reports from governance data.

    In production, this reads from PostgreSQL (ANCESTOR, PULSE, SENTINEL tables).
    For testing, it accepts pre-processed data dicts.
    """

    def __init__(self, db=None):
        self.db = db

    def generate(
        self,
        framework: str,
        data: dict,
        period_days: int = 30,
    ) -> ComplianceReport:
        """
        Generate a compliance report for a specific framework.

        Args:
            framework: "sox" | "eu_ai_act" | "gdpr" | "internal"
            data: Pre-processed governance data (decisions, trust_events, violations, etc.)
            period_days: Reporting period in days
        """
        template = FRAMEWORK_TEMPLATES.get(framework)
        if not template:
            raise ValueError(f"Unknown framework: {framework}. Valid: {list(FRAMEWORK_TEMPLATES.keys)}")

        now = datetime.now(UTC)
        report = ComplianceReport(
            framework=framework,
            framework_name=template["name"],
            period_start=now - timedelta(days=period_days),
            period_end=now,
        )

        # Build sections based on framework template
        generators = {
            "decision_trail_integrity": self._section_decision_integrity,
            "financial_authorization_summary": self._section_financial_auth,
            "policy_enforcement_log": self._section_policy_enforcement,
            "escalation_review": self._section_escalation_review,
            "approval_chain_verification": self._section_approval_chain,
            "human_override_summary": self._section_human_overrides,
            "escalation_effectiveness": self._section_escalation_effectiveness,
            "transparency_metrics": self._section_transparency,
            "risk_classification": self._section_risk_classification,
            "explainability_audit": self._section_explainability,
            "automated_decision_inventory": self._section_decision_inventory,
            "reasoning_trace_availability": self._section_reasoning_traces,
            "human_intervention_rate": self._section_human_intervention,
            "data_retention_compliance": self._section_data_retention,
            "agent_fleet_health": self._section_fleet_health,
            "trust_score_distribution": self._section_trust_distribution,
            "policy_violation_summary": self._section_violations,
            "cache_efficiency": self._section_cache_efficiency,
            "dna_integrity_audit": self._section_dna_integrity,
        }

        for section_id in template["sections"]:
            gen = generators.get(section_id)
            if gen:
                section = gen(data)
                report.sections.append(section)

        # Evaluate overall status
        risk_levels = [s.risk_level for s in report.sections]
        if "critical" in risk_levels:
            report.overall_status = "fail"
        elif "high" in risk_levels:
            report.overall_status = "warn"
        else:
            report.overall_status = "pass"

        report.summary = self._generate_summary(report)
        report.recommendations = self._generate_recommendations(report)

        logger.info(
            f"[COMPLIANCE] Report generated: framework={framework} "
            f"status={report.overall_status} score={report.compliance_score}"
        )
        return report

    def list_frameworks(self) -> list[dict]:
        return [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in FRAMEWORK_TEMPLATES.items
        ]

    # ──────────────────────────────────────────────
    # Section generators
    # ──────────────────────────────────────────────

    def _section_decision_integrity(self, data: dict) -> ComplianceSection:
        chain = data.get("chain_verification", {})
        section = ComplianceSection(
            id="decision_trail_integrity",
            title="Decision Trail Integrity (Hash Chain)",
        )
        section.metrics = [
            ComplianceMetric(
                name="Chain Valid",
                value=chain.get("valid", True),
                status="pass" if chain.get("valid", True) else "fail",
                description="SHA-256 hash chain verification — tamper detection",
            ),
            ComplianceMetric(
                name="Blocks Verified",
                value=chain.get("checked", 0),
                status="pass",
                description="Total decision blocks in verified chain",
            ),
            ComplianceMetric(
                name="Integrity Percentage",
                value=chain.get("integrity_pct", 100.0),
                status="pass" if chain.get("integrity_pct", 100) >= 99.9 else "fail",
                threshold=99.9,
                description="Percentage of chain blocks with valid hash linkage",
            ),
        ]
        section.risk_level = "critical" if not chain.get("valid", True) else "low"
        section.finding = ("Audit chain intact" if chain.get("valid", True) 
                          else "CHAIN INTEGRITY VIOLATION DETECTED")
        return section

    def _section_financial_auth(self, data: dict) -> ComplianceSection:
        decisions = data.get("decisions", [])
        total = len(decisions)
        high_amount = [d for d in decisions if d.get("amount", 0) > 50000]
        authorized = [d for d in decisions if d.get("verdict") == "allow"]
        section = ComplianceSection(
            id="financial_authorization_summary",
            title="Financial Authorization Summary",
        )
        section.metrics = [
            ComplianceMetric("Total Decisions", total, "pass"),
            ComplianceMetric("High-Value Decisions (>₹50K)", len(high_amount), "pass"),
            ComplianceMetric("Authorized Actions", len(authorized), "pass"),
            ComplianceMetric(
                "Authorization Rate",
                round(len(authorized) / total * 100, 1) if total else 0,
                "pass",
                description="Percentage of decisions that were authorized",
            ),
        ]
        section.finding = f"{total} financial decisions processed, {len(high_amount)} high-value"
        return section

    def _section_policy_enforcement(self, data: dict) -> ComplianceSection:
        violations = data.get("violations", [])
        blocks = data.get("policy_blocks", 0)
        section = ComplianceSection(
            id="policy_enforcement_log",
            title="Policy Enforcement Log",
        )
        section.metrics = [
            ComplianceMetric("Total Violations", len(violations),
                           "pass" if len(violations) == 0 else "warn"),
            ComplianceMetric("Policy Blocks", blocks, "pass"),
            ComplianceMetric("Critical Violations",
                           sum(1 for v in violations if v.get("severity") == "critical"),
                           "pass" if not any(v.get("severity") == "critical" for v in violations) else "fail"),
        ]
        section.risk_level = "high" if any(v.get("severity") == "critical" for v in violations) else "low"
        section.finding = f"{len(violations)} violations detected in period"
        return section

    def _section_escalation_review(self, data: dict) -> ComplianceSection:
        escalations = data.get("escalations", [])
        section = ComplianceSection(id="escalation_review", title="Escalation Review")
        section.metrics = [
            ComplianceMetric("Total Escalations", len(escalations), "pass"),
            ComplianceMetric("Resolved", sum(1 for e in escalations if e.get("resolved")), "pass"),
        ]
        section.finding = f"{len(escalations)} escalations to human reviewers"
        return section

    def _section_approval_chain(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="approval_chain_verification", title="Approval Chain Verification")
        decisions = data.get("decisions", [])
        with_trace = [d for d in decisions if d.get("reasoning_trace")]
        section.metrics = [
            ComplianceMetric(
                "Decisions with Reasoning Trace",
                len(with_trace),
                "pass" if len(with_trace) == len(decisions) else "warn",
            ),
            ComplianceMetric("Trace Coverage (%)",
                           round(len(with_trace) / len(decisions) * 100, 1) if decisions else 100,
                           "pass" if not decisions or len(with_trace) / len(decisions) >= 0.95 else "warn",
                           threshold=95.0),
        ]
        return section

    def _section_human_overrides(self, data: dict) -> ComplianceSection:
        overrides = data.get("human_overrides", [])
        section = ComplianceSection(id="human_override_summary", title="Human Override Summary")
        section.metrics = [
            ComplianceMetric("Total Overrides", len(overrides), "pass"),
        ]
        section.finding = f"{len(overrides)} human overrides in period"
        return section

    def _section_escalation_effectiveness(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="escalation_effectiveness", title="Escalation Effectiveness")
        escalations = data.get("escalations", [])
        correct = [e for e in escalations if e.get("was_necessary")]
        rate = round(len(correct) / len(escalations) * 100, 1) if escalations else 100
        section.metrics = [
            ComplianceMetric("Correct Escalation Rate (%)", rate, "pass" if rate >= 80 else "warn", threshold=80),
        ]
        return section

    def _section_transparency(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="transparency_metrics", title="Transparency & Explainability")
        decisions = data.get("decisions", [])
        explained = [d for d in decisions if d.get("reasoning_trace")]
        section.metrics = [
            ComplianceMetric("Explainability Rate (%)",
                           round(len(explained) / len(decisions) * 100, 1) if decisions else 100,
                           "pass"),
        ]
        return section

    def _section_risk_classification(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="risk_classification", title="AI Risk Classification")
        section.metrics = [
            ComplianceMetric("System Classification", data.get("risk_class", "limited"), "pass"),
        ]
        return section

    def _section_explainability(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="explainability_audit", title="Explainability Audit")
        section.metrics = [
            ComplianceMetric("Models Used", len(data.get("models", [])), "pass"),
        ]
        return section

    def _section_decision_inventory(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="automated_decision_inventory", title="Automated Decision Inventory")
        section.metrics = [
            ComplianceMetric("Total Automated Decisions", len(data.get("decisions", [])), "pass"),
        ]
        return section

    def _section_reasoning_traces(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="reasoning_trace_availability", title="Reasoning Trace Availability")
        decisions = data.get("decisions", [])
        with_trace = [d for d in decisions if d.get("reasoning_trace")]
        section.metrics = [
            ComplianceMetric("Trace Coverage (%)",
                           round(len(with_trace) / len(decisions) * 100, 1) if decisions else 100,
                           "pass"),
        ]
        return section

    def _section_human_intervention(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="human_intervention_rate", title="Human Intervention Rate")
        total = len(data.get("decisions", []))
        human = len(data.get("human_overrides", []))
        section.metrics = [
            ComplianceMetric("Intervention Rate (%)", round(human / total * 100, 1) if total else 0, "pass"),
        ]
        return section

    def _section_data_retention(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="data_retention_compliance", title="Data Retention Compliance")
        section.metrics = [
            ComplianceMetric("Retention Policy Active", data.get("retention_active", True), "pass"),
        ]
        return section

    def _section_fleet_health(self, data: dict) -> ComplianceSection:
        fleet = data.get("fleet", {})
        section = ComplianceSection(id="agent_fleet_health", title="Agent Fleet Health")
        section.metrics = [
            ComplianceMetric("Total Agents", fleet.get("total", 0), "pass"),
            ComplianceMetric("Alive", fleet.get("alive", 0), "pass"),
            ComplianceMetric("Dead", fleet.get("dead", 0), "pass" if fleet.get("dead", 0) == 0 else "warn"),
        ]
        return section

    def _section_trust_distribution(self, data: dict) -> ComplianceSection:
        section = ComplianceSection(id="trust_score_distribution", title="Trust Score Distribution")
        dist = data.get("trust_distribution", {})
        section.metrics = [
            ComplianceMetric("Average Trust Score", dist.get("avg", 0.0), "pass"),
            ComplianceMetric("Agents Below 0.5", dist.get("below_threshold", 0),
                           "pass" if dist.get("below_threshold", 0) == 0 else "warn"),
        ]
        return section

    def _section_violations(self, data: dict) -> ComplianceSection:
        violations = data.get("violations", [])
        section = ComplianceSection(id="policy_violation_summary", title="Policy Violation Summary")
        section.metrics = [
            ComplianceMetric("Total Violations", len(violations),
                           "pass" if len(violations) == 0 else "warn"),
        ]
        return section

    def _section_cache_efficiency(self, data: dict) -> ComplianceSection:
        cache = data.get("cache_stats", {})
        section = ComplianceSection(id="cache_efficiency", title="QICACHE Efficiency")
        hit_rate = cache.get("hit_rate", 0)
        section.metrics = [
            ComplianceMetric("Hit Rate (%)", hit_rate, "pass" if hit_rate >= 40 else "warn", threshold=40),
            ComplianceMetric("Token Savings", cache.get("tokens_saved", 0), "pass"),
        ]
        return section

    def _section_dna_integrity(self, data: dict) -> ComplianceSection:
        dna = data.get("dna_audit", {})
        section = ComplianceSection(id="dna_integrity_audit", title="GENESIS DNA Integrity")
        section.metrics = [
            ComplianceMetric("Genes Audited", dna.get("audited", 0), "pass"),
            ComplianceMetric("Tampered Genes", dna.get("tampered", 0),
                           "pass" if dna.get("tampered", 0) == 0 else "fail"),
        ]
        section.risk_level = "critical" if dna.get("tampered", 0) > 0 else "low"
        return section

    # ──────────────────────────────────────────────
    # Summary and recommendations
    # ──────────────────────────────────────────────

    def _generate_summary(self, report: ComplianceReport) -> str:
        total_metrics = sum(len(s.metrics) for s in report.sections)
        passing = sum(s.to_dict["pass_count"] for s in report.sections)
        return (
            f"{report.framework_name}: {passing}/{total_metrics} checks passing "
            f"({report.compliance_score}% compliant). "
            f"Overall status: {report.overall_status.upper}"
        )

    def _generate_recommendations(self, report: ComplianceReport) -> list[str]:
        recs = []
        for section in report.sections:
            if section.risk_level in ("high", "critical"):
                recs.append(f"URGENT: Review '{section.title}' — risk level: {section.risk_level}")
            for metric in section.metrics:
                if metric.status == "fail":
                    recs.append(f"Fix: {metric.name} — current: {metric.value}, required: {metric.threshold}")
                elif metric.status == "warn":
                    recs.append(f"Improve: {metric.name} — current: {metric.value}")
        return recs
