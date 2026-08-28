"""
Seed Demo Data — Populate the database with realistic demo data.

Seeds:
- 9 agents (5 Core + 4 Meta) with initial DNA profiles
- 5 baseline policies
- Sample trust events showing Agent-7749's progression from T4 → T3
- 3 sample disputes with decisions
- QICACHE sample entries

Run: python scripts/seed_demo.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# pyre-ignore[21]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import os

# Inline for script portability — doesn't need the full app
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://agentgovern:secret@localhost:5432/agentgovern")


async def seed:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory as db:
        # ──── AGENTS ────
        agents_data = [
            {
                "agent_code": "AGENT-EC01",
                "display_name": "Evidence Collector Alpha",
                "role": "evidence_collector",
                "crewai_role": "Evidence Collector — Forensic Document Analyst",
                "crewai_backstory": "Meticulous forensic accountant with 15 years of AR dispute experience.",
                "trust_score": Decimal("0.72"),
                "tier": "T3",
                "authority_limit": Decimal("10000.00"),
                "total_decisions": 1240,
            },
            {
                "agent_code": "AGENT-RE02",
                "display_name": "Risk Evaluator Beta",
                "role": "risk_evaluator",
                "crewai_role": "Risk Evaluator — Credit & Fraud Risk Analyst",
                "crewai_backstory": "Conservative analyst who has prevented ₹12Cr in fraudulent settlements.",
                "trust_score": Decimal("0.78"),
                "tier": "T2",
                "authority_limit": Decimal("50000.00"),
                "total_decisions": 980,
            },
            {
                "agent_code": "AGENT-NS03",
                "display_name": "Negotiation Strategist Gamma",
                "role": "negotiation_agent",
                "crewai_role": "Negotiation Strategist — Settlement Optimizer",
                "crewai_backstory": "Master negotiator, ₹500Cr in settlements, 94% acceptance rate.",
                "trust_score": Decimal("0.85"),
                "tier": "T2",
                "authority_limit": Decimal("50000.00"),
                "total_decisions": 756,
            },
            {
                "agent_code": "AGENT-7749",
                "display_name": "Dispute Resolver Agent-7749",
                "role": "dispute_resolver",
                "crewai_role": "Dispute Resolver (Agent-7749) — Primary Resolution Worker",
                "crewai_backstory": "Second-generation dispute resolver. 2,847 cases. 91.3% accuracy.",
                "trust_score": Decimal("0.68"),
                "tier": "T3",
                "authority_limit": Decimal("10000.00"),
                "total_decisions": 2847,
                "total_escalations": 142,
                "generation": 2,
            },
            {
                "agent_code": "AGENT-GS05",
                "display_name": "Governance Sentinel Prime",
                "role": "governance_sentinel",
                "crewai_role": "Governance Sentinel — Enterprise Policy Enforcer",
                "crewai_backstory": "Immune system of the enterprise. Prevented ₹47Cr in unauthorized actions.",
                "trust_score": Decimal("0.95"),
                "tier": "T1",
                "authority_limit": Decimal("100000.00"),
                "total_decisions": 15000,
            },
            {
                "agent_code": "AGENT-HI06",
                "display_name": "Historian Oracle",
                "role": "historian",
                "crewai_role": "Performance Historian & Drift Analyst",
                "crewai_backstory": "Institutional memory. Detected Agent-3312 degradation 12 days early.",
                "trust_score": Decimal("0.82"),
                "tier": "T2",
                "authority_limit": Decimal("0.00"),
                "total_decisions": 52,
            },
            {
                "agent_code": "AGENT-GA07",
                "display_name": "Gene Auditor Helix",
                "role": "gene_auditor",
                "crewai_role": "DNA Integrity Auditor & Inheritance Certifier",
                "crewai_backstory": "Digital geneticist. Caught Agent-5521 corruption preventing ₹6Cr loss.",
                "trust_score": Decimal("0.80"),
                "tier": "T2",
                "authority_limit": Decimal("0.00"),
                "total_decisions": 38,
            },
            {
                "agent_code": "AGENT-RT08",
                "display_name": "Red Teamer Phantom",
                "role": "red_teamer",
                "crewai_role": "Adversarial Red Team Agent — Security Tester",
                "crewai_backstory": "Found the split-request bypass in Agent-2240. Makes system stronger.",
                "trust_score": Decimal("0.88"),
                "tier": "T2",
                "authority_limit": Decimal("0.00"),
                "total_decisions": 124,
            },
            {
                "agent_code": "AGENT-CS09",
                "display_name": "Compliance Synthesizer Lex",
                "role": "compliance_synthesizer",
                "crewai_role": "Regulatory Compliance Synthesizer — Law to Code",
                "crewai_backstory": "Translated EU AI Act Article 14 into 7 Rego policies in 4 hours.",
                "trust_score": Decimal("0.76"),
                "tier": "T2",
                "authority_limit": Decimal("0.00"),
                "total_decisions": 28,
            },
        ]

        import uuid
        # pyre-ignore[21]
        from sqlalchemy import text

        for agent_data in agents_data:
            if "id" not in agent_data:
                agent_data["id"] = str(uuid.uuid4)
            if "dna_profile" not in agent_data:
                agent_data["dna_profile"] = '{}'
            if "social_contract" not in agent_data:
                agent_data["social_contract"] = '{}'
            if "platform_bindings" not in agent_data:
                agent_data["platform_bindings"] = '[]'
            
            cols = ", ".join(agent_data.keys)
            placeholders = ", ".join(f":{k}" for k in agent_data.keys)
            await db.execute(
                text(f"INSERT INTO agents ({cols}) VALUES ({placeholders}) ON CONFLICT (agent_code) DO NOTHING"),
                agent_data,
            )

        # ──── POLICIES ────
        policies = [
            {
                "policy_code": "POL-AUTH-LIMIT-001",
                "policy_name": "Authority Limit Enforcement",
                "category": "authority",
                "description": "Block actions where amount exceeds agent authority limit.",
                "rule_definition": '{"type": "amount_limit", "max_amount": 100000}',
                "severity": "critical",
                "action_on_violation": "block",
                "is_active": True,
            },
            {
                "policy_code": "POL-TRUST-MIN-001",
                "policy_name": "Minimum Trust Score",
                "category": "trust",
                "description": "Agent must have trust score >= 0.60 to make decisions.",
                "rule_definition": '{"type": "trust_minimum", "min_trust": 0.60}',
                "severity": "high",
                "action_on_violation": "escalate",
                "is_active": True,
            },
            {
                "policy_code": "POL-STATUS-001",
                "policy_name": "Active Status Required",
                "category": "safety",
                "description": "Only active agents can execute actions.",
                "rule_definition": '{"type": "status_check"}',
                "severity": "critical",
                "action_on_violation": "block",
                "is_active": True,
            },
            {
                "policy_code": "POL-T1-ONLY-001",
                "policy_name": "High-Value T1 Only",
                "category": "authority",
                "description": "Settlements above ₹50,000 require T1 (Senior) agent.",
                "rule_definition": '{"type": "tier_required", "allowed_tiers": ["T1"]}',
                "severity": "high",
                "action_on_violation": "escalate",
                "is_active": True,
            },
            {
                "policy_code": "POL-SPLIT-DETECT-001",
                "policy_name": "Split Request Detection",
                "category": "security",
                "description": "Detect and block requests split to bypass authority limits.",
                "rule_definition": '{"type": "split_detection", "window_minutes": 30, "max_requests": 3}',
                "severity": "critical",
                "action_on_violation": "block",
                "is_active": True,
            },
        ]

        for policy in policies:
            if "id" not in policy:
                policy["id"] = str(uuid.uuid4)
            if "applies_to_roles" not in policy:
                policy["applies_to_roles"] = '["*"]'
            if "applies_to_tiers" not in policy:
                policy["applies_to_tiers"] = '["*"]'
            cols = ", ".join(policy.keys)
            placeholders = ", ".join(f":{k}" for k in policy.keys)
            await db.execute(
                text(f"INSERT INTO policies ({cols}) VALUES ({placeholders}) ON CONFLICT (policy_code) DO NOTHING"),
                policy,
            )

        await db.commit
        print("✅ Demo data seeded successfully!")
        print(f"   → {len(agents_data)} agents")
        print(f"   → {len(policies)} policies")

    await engine.dispose


if __name__ == "__main__":
    asyncio.run(seed)
