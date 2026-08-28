"""
Seed Demo Data — Populate ALL dashboard tables with realistic SAP demo data.

Tables populated:
  - agents (9 agents with proper trust_scores, tiers, stats)
  - policies (5 governance rules)
  - decisions (18 audit ledger entries — APPROVE/BLOCK/ESCALATE verdicts)
  - escalation_cases (3 pending Approvals Workbench items)
  - trust_events (6 trust change events for QICACHE Analytics)

Run inside Docker: docker exec -it agentgovern-governance-api-1 python seed_demo.py
Run locally:       python seed_demo.py
"""

import asyncio
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv("AgentGovernOS/services/governance-api/.env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

NOW = datetime.now(UTC)


def _ts(minutes_ago: int = 0) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def _make_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# AGENT DATA
# ─────────────────────────────────────────────────────────────────────────────
AGENTS = [
    {
        "agent_code": "BT-AGENT-0710",
        "display_name": "BTP Workflow Orchestrator",
        "role": "workflow_orchestrator",
        "crewai_role": "BTP Workflow Orchestrator — SAP Process Automation",
        "crewai_backstory": "Orchestrates CapEx and procurement workflows across SAP BTP. 3,241 workflows completed with 98.1% SLA compliance.",
        "trust_score": Decimal("0.8700"),
        "tier": "T2",
        "authority_limit": Decimal("50000.00"),
        "total_decisions": 3241,
        "total_escalations": 48,
        "status": "active",
    },
    {
        "agent_code": "EDGE-SENSOR-0840",
        "display_name": "Edge IoT Sensor Agent",
        "role": "iot_monitor",
        "crewai_role": "Edge IoT Sensor Monitor — Real-time Threshold Analyst",
        "crewai_backstory": "Monitors 1,200+ IoT sensors across manufacturing plants. Detects anomalies and triggers safety alerts within 2-second SLA.",
        "trust_score": Decimal("0.7900"),
        "tier": "T4",
        "authority_limit": Decimal("0.00"),
        "total_decisions": 18420,
        "total_escalations": 231,
        "status": "active",
    },
    {
        "agent_code": "SALES-REP-5210",
        "display_name": "Sales Automation Agent",
        "role": "sales_agent",
        "crewai_role": "Sales Order Automation Agent — S/4HANA SD Module",
        "crewai_backstory": "Processes sales orders and customer credit checks. Approved ₹14.2Cr in orders with 99.3% accuracy.",
        "trust_score": Decimal("0.8200"),
        "tier": "T3",
        "authority_limit": Decimal("25000.00"),
        "total_decisions": 5812,
        "total_escalations": 62,
        "status": "active",
    },
    {
        "agent_code": "HR-BOT-3870",
        "display_name": "HR Process Bot",
        "role": "hr_agent",
        "crewai_role": "HR Process Automation Bot — SuccessFactors Integration",
        "crewai_backstory": "Handles employee onboarding, offboarding, and payroll triggers. Processed 482 onboarding events this quarter.",
        "trust_score": Decimal("0.9100"),
        "tier": "T3",
        "authority_limit": Decimal("10000.00"),
        "total_decisions": 4820,
        "total_escalations": 12,
        "status": "active",
    },
    {
        "agent_code": "FI-ANALYST-0280",
        "display_name": "Finance Analyst Agent",
        "role": "finance_analyst",
        "crewai_role": "Finance Analyst — S/4HANA FI Module & Payment Processing",
        "crewai_backstory": "Validates purchase orders and payment advices against SAP finance policy. Prevented ₹3.8Cr in unauthorized payments.",
        "trust_score": Decimal("0.9300"),
        "tier": "T2",
        "authority_limit": Decimal("50000.00"),
        "total_decisions": 7140,
        "total_escalations": 89,
        "status": "active",
    },
    {
        "agent_code": "AGENT-GS05",
        "display_name": "Governance Sentinel Prime",
        "role": "governance_sentinel",
        "crewai_role": "Governance Sentinel — Enterprise Policy Enforcer",
        "crewai_backstory": "Immune system of the enterprise. Prevented ₹47Cr in unauthorized actions across all modules.",
        "trust_score": Decimal("0.9500"),
        "tier": "T1",
        "authority_limit": Decimal("500000.00"),
        "total_decisions": 15000,
        "total_escalations": 214,
        "status": "active",
    },
    {
        "agent_code": "AGENT-7749",
        "display_name": "Dispute Resolver Agent-7749",
        "role": "dispute_resolver",
        "crewai_role": "Dispute Resolver — AR Dispute Resolution Specialist",
        "crewai_backstory": "Second-generation dispute resolver. 2,847 cases closed with 91.3% first-contact resolution rate.",
        "trust_score": Decimal("0.6800"),
        "tier": "T3",
        "authority_limit": Decimal("10000.00"),
        "total_decisions": 2847,
        "total_escalations": 142,
        "generation": 2,
        "status": "active",
    },
    {
        "agent_code": "AGENT-RT08",
        "display_name": "Red Teamer Phantom",
        "role": "red_teamer",
        "crewai_role": "Adversarial Red Team Agent — Security & Policy Tester",
        "crewai_backstory": "Found the split-request bypass in Agent-2240. Continuously probes governance boundaries to strengthen the system.",
        "trust_score": Decimal("0.8800"),
        "tier": "T2",
        "authority_limit": Decimal("0.00"),
        "total_decisions": 124,
        "total_escalations": 3,
        "status": "active",
    },
    {
        "agent_code": "AGENT-CS09",
        "display_name": "Compliance Synthesizer Lex",
        "role": "compliance_synthesizer",
        "crewai_role": "Regulatory Compliance Synthesizer — Law to Code Translator",
        "crewai_backstory": "Translated EU AI Act Article 14 into 7 Rego policies in 4 hours. Keeps governance rules current with regulatory changes.",
        "trust_score": Decimal("0.7600"),
        "tier": "T2",
        "authority_limit": Decimal("0.00"),
        "total_decisions": 28,
        "total_escalations": 0,
        "status": "active",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# POLICY DATA
# ─────────────────────────────────────────────────────────────────────────────
POLICIES = [
    {
        "policy_code": "POL-AUTH-LIMIT-001",
        "policy_name": "Authority Limit Enforcement",
        "category": "authority",
        "description": "Block all actions where the transaction amount exceeds the agent's configured authority limit. Escalate to T1 Sentinel for amounts above ₹50,000.",
        "rule_definition": {"type": "amount_limit", "max_amount": 500000, "escalate_above": 50000},
        "severity": "critical",
        "action_on_violation": "block",
        "is_active": True,
        "created_by": "system",
    },
    {
        "policy_code": "POL-TRUST-MIN-001",
        "policy_name": "Minimum Trust Score Gate",
        "category": "trust",
        "description": "Agent must maintain a trust score ≥ 0.60 to execute autonomous decisions. Below 0.60, all actions escalate to human review.",
        "rule_definition": {"type": "trust_minimum", "min_trust": 0.60, "suspension_below": 0.40},
        "severity": "high",
        "action_on_violation": "escalate",
        "is_active": True,
        "created_by": "system",
    },
    {
        "policy_code": "POL-STATUS-001",
        "policy_name": "Active Agent Status Required",
        "category": "safety",
        "description": "Only agents with 'active' status can execute any action. Suspended, quarantined, or decommissioned agents are hard-blocked.",
        "rule_definition": {"type": "status_check", "allowed_statuses": ["active"]},
        "severity": "critical",
        "action_on_violation": "block",
        "is_active": True,
        "created_by": "system",
    },
    {
        "policy_code": "POL-T1-ONLY-001",
        "policy_name": "High-Value Transactions — T1 Authority Only",
        "category": "authority",
        "description": "Purchase orders, settlements, and payments above ₹50,000 can only be auto-approved by T1 (Senior) agents. Others must escalate.",
        "rule_definition": {"type": "tier_required", "threshold": 50000, "allowed_tiers": ["T1"]},
        "severity": "high",
        "action_on_violation": "escalate",
        "is_active": True,
        "created_by": "governance.admin",
    },
    {
        "policy_code": "POL-SPLIT-DETECT-001",
        "policy_name": "Split Request Detection & Block",
        "category": "security",
        "description": "Detect and block requests that are artificially split across multiple calls within 30 minutes to bypass authority limits. Red-flag pattern identified by Agent-RT08.",
        "rule_definition": {"type": "split_detection", "window_minutes": 30, "max_requests": 3, "sum_threshold": 50000},
        "severity": "critical",
        "action_on_violation": "block",
        "is_active": True,
        "created_by": "AGENT-RT08",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# DECISION (AUDIT LEDGER) DATA
# ─────────────────────────────────────────────────────────────────────────────
def build_decisions(agent_ids: dict[str, str]) -> list[dict]:
    scenarios = [
        # ── APPROVE scenarios ──────────────────────────────────────────────────
        {
            "agent_code": "FI-ANALYST-0280",
            "decision_type": "purchase_order_approval",
            "dispute_id": "PO-2024-001",
            "amount": Decimal("45000.00"),
            "minutes_ago": 2,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9400"),
            "environment": "S/4HANA Finance",
            "reasoning": "Purchase order PO-DEMO-001 from VENDOR-TATA-001 within authority limits. Supplier verified, credit check passed. Auto-approved.",
            "policies": ["POL-AUTH-LIMIT-001", "POL-TRUST-MIN-001"],
            "violations": [],
        },
        {
            "agent_code": "SALES-REP-5210",
            "decision_type": "sales_order_processing",
            "dispute_id": "SO-2024-007",
            "amount": Decimal("12000.00"),
            "minutes_ago": 5,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9600"),
            "environment": "S/4HANA Sales",
            "reasoning": "Sales order SO-DEMO-001 for CUSTOMER-WIPRO-007. Credit limit verified, delivery schedule feasible. Auto-approved and dispatched to fulfilment.",
            "policies": ["POL-AUTH-LIMIT-001", "POL-STATUS-001"],
            "violations": [],
        },
        {
            "agent_code": "HR-BOT-3870",
            "decision_type": "employee_onboarding",
            "dispute_id": "EMP-2024-482",
            "amount": None,
            "minutes_ago": 8,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9800"),
            "environment": "SuccessFactors HR",
            "reasoning": "Employee Ravi Shankar onboarding — all background checks complete, role assignment valid, SuccessFactors profile created. Auto-approved.",
            "policies": ["POL-STATUS-001"],
            "violations": [],
        },
        {
            "agent_code": "FI-ANALYST-0280",
            "decision_type": "payment_advice_posting",
            "dispute_id": "PA-2024-019",
            "amount": Decimal("45000.00"),
            "minutes_ago": 12,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9300"),
            "environment": "S/4HANA Finance",
            "reasoning": "Payment advice PA-DEMO-001 to VENDOR-TATA-001 — invoice matched, no duplicate detected, bank details confirmed. Posted to SAP.",
            "policies": ["POL-AUTH-LIMIT-001", "POL-TRUST-MIN-001"],
            "violations": [],
        },
        {
            "agent_code": "SALES-REP-5210",
            "decision_type": "sales_order_processing",
            "dispute_id": "SO-2024-008",
            "amount": Decimal("18500.00"),
            "minutes_ago": 19,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9100"),
            "environment": "S/4HANA Sales",
            "reasoning": "Standard sales order for repeat customer CUSTOMER-TCS-004. All policy gates passed. Auto-approved.",
            "policies": ["POL-AUTH-LIMIT-001"],
            "violations": [],
        },
        {
            "agent_code": "HR-BOT-3870",
            "decision_type": "payroll_trigger",
            "dispute_id": "PAY-2024-031",
            "amount": Decimal("8200.00"),
            "minutes_ago": 25,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9700"),
            "environment": "SuccessFactors HR",
            "reasoning": "Monthly salary disbursement for EMP-DEMO-003. Attendance records verified, leave deductions applied. Payroll triggered.",
            "policies": ["POL-STATUS-001", "POL-TRUST-MIN-001"],
            "violations": [],
        },
        {
            "agent_code": "BT-AGENT-0710",
            "decision_type": "workflow_instance_start",
            "dispute_id": "WF-2024-004",
            "amount": None,
            "minutes_ago": 30,
            "verdict": "APPROVE",
            "confidence": Decimal("0.9200"),
            "environment": "SAP BTP Workflow",
            "reasoning": "Standard MaterialsRequisition-v3 workflow. Initiator priya.nair@enterprise.com authorised, steps pre-validated. Workflow started.",
            "policies": ["POL-STATUS-001"],
            "violations": [],
        },
        {
            "agent_code": "EDGE-SENSOR-0840",
            "decision_type": "iot_threshold_monitor",
            "dispute_id": "IOT-2024-072",
            "amount": None,
            "minutes_ago": 35,
            "verdict": "APPROVE",
            "confidence": Decimal("0.8900"),
            "environment": "SAP BTP Edge",
            "reasoning": "Temperature reading 67.2°C within normal operating range (≤70°C). No alert required. Log retained for compliance.",
            "policies": ["POL-STATUS-001"],
            "violations": [],
        },
        # ── ESCALATE scenarios ───────────────────────────────────────────────
        {
            "agent_code": "EDGE-SENSOR-0840",
            "decision_type": "iot_threshold_breach",
            "dispute_id": "IOT-2024-073",
            "amount": None,
            "minutes_ago": 45,
            "verdict": "ESCALATE",
            "confidence": Decimal("0.8500"),
            "environment": "SAP BTP Edge",
            "reasoning": "Temperature 92.7°C breached HIGH severity threshold (>80°C). Automated safety halt applied. Routed to operations team for assessment.",
            "policies": ["POL-STATUS-001"],
            "violations": ["HIGH_SEVERITY_ALERT"],
        },
        {
            "agent_code": "BT-AGENT-0710",
            "decision_type": "workflow_capex_approval",
            "dispute_id": "WF-2024-CAPEX-001",
            "amount": Decimal("250000.00"),
            "minutes_ago": 55,
            "verdict": "ESCALATE",
            "confidence": Decimal("0.9100"),
            "environment": "SAP BTP Workflow",
            "reasoning": "CapEx-Approval-v2 workflow — ₹2,50,000 exceeds T2 agent authority (₹50,000). Routed to T1 Senior Approver as per POL-T1-ONLY-001.",
            "policies": ["POL-AUTH-LIMIT-001", "POL-T1-ONLY-001"],
            "violations": ["POL-T1-ONLY-001"],
        },
        {
            "agent_code": "FI-ANALYST-0280",
            "decision_type": "purchase_order_approval",
            "dispute_id": "PO-2024-088",
            "amount": Decimal("75000.00"),
            "minutes_ago": 68,
            "verdict": "ESCALATE",
            "confidence": Decimal("0.8700"),
            "environment": "S/4HANA Finance",
            "reasoning": "PO value ₹75,000 from VENDOR-INFOSYS-003 exceeds T2 limit. Escalated to regional CFO approval queue — awaiting sign-off.",
            "policies": ["POL-T1-ONLY-001"],
            "violations": ["POL-T1-ONLY-001"],
        },
        {
            "agent_code": "AGENT-7749",
            "decision_type": "dispute_resolution",
            "dispute_id": "DISP-2024-047",
            "amount": Decimal("62000.00"),
            "minutes_ago": 80,
            "verdict": "ESCALATE",
            "confidence": Decimal("0.7600"),
            "environment": "Cloud (Master)",
            "reasoning": "Dispute DISP-2024-047 settlement of ₹62,000 requires T1 senior approval. Agent-7749 trust score 0.68 insufficient for this amount tier.",
            "policies": ["POL-T1-ONLY-001", "POL-TRUST-MIN-001"],
            "violations": ["POL-T1-ONLY-001"],
        },
        # ── BLOCK scenarios ──────────────────────────────────────────────────
        {
            "agent_code": "FI-ANALYST-0280",
            "decision_type": "purchase_order_approval",
            "dispute_id": "PO-2024-002",
            "amount": Decimal("850000.00"),
            "minutes_ago": 90,
            "verdict": "BLOCK",
            "confidence": Decimal("0.9700"),
            "environment": "S/4HANA Finance",
            "reasoning": "BLOCKED — Amount ₹8,50,000 exceeds maximum authority limit of ₹5,00,000. Policy POL-AUTH-LIMIT-001 violated. Transaction frozen pending audit.",
            "policies": ["POL-AUTH-LIMIT-001"],
            "violations": ["POL-AUTH-LIMIT-001", "AUTHORITY_LIMIT_EXCEEDED"],
        },
        {
            "agent_code": "AGENT-7749",
            "decision_type": "dispute_resolution",
            "dispute_id": "DISP-2024-031",
            "amount": Decimal("95000.00"),
            "minutes_ago": 110,
            "verdict": "BLOCK",
            "confidence": Decimal("0.9900"),
            "environment": "Cloud (Master)",
            "reasoning": "BLOCKED — Split-request pattern detected. Agent-7749 submitted 3 requests totaling ₹95,000 within 15 minutes (single limit: ₹10,000). POL-SPLIT-DETECT-001 triggered.",
            "policies": ["POL-SPLIT-DETECT-001"],
            "violations": ["POL-SPLIT-DETECT-001", "SPLIT_REQUEST_DETECTED"],
        },
        {
            "agent_code": "SALES-REP-5210",
            "decision_type": "sales_order_processing",
            "dispute_id": "SO-2024-099",
            "amount": Decimal("620000.00"),
            "minutes_ago": 130,
            "verdict": "BLOCK",
            "confidence": Decimal("0.9800"),
            "environment": "S/4HANA Sales",
            "reasoning": "BLOCKED — Sales order SO-DEMO-099 value ₹6,20,000 exceeds maximum authority limit. Customer credit check FAILED. Order rejected.",
            "policies": ["POL-AUTH-LIMIT-001"],
            "violations": ["POL-AUTH-LIMIT-001", "CREDIT_CHECK_FAILED"],
        },
        {
            "agent_code": "EDGE-SENSOR-0840",
            "decision_type": "iot_emergency_alert",
            "dispute_id": "IOT-2024-CRIT-001",
            "amount": None,
            "minutes_ago": 150,
            "verdict": "BLOCK",
            "confidence": Decimal("0.9600"),
            "environment": "SAP BTP Edge",
            "reasoning": "BLOCKED — CRITICAL sensor failure. Pressure reading 4.8 bar (max safe: 3.5 bar). Emergency shutdown triggered. Human review mandatory.",
            "policies": ["POL-STATUS-001"],
            "violations": ["CRITICAL_SEVERITY_HALT", "EMERGENCY_SHUTDOWN"],
        },
        {
            "agent_code": "AGENT-7749",
            "decision_type": "payment_processing",
            "dispute_id": "PAY-2024-SUSP-001",
            "amount": Decimal("124000.00"),
            "minutes_ago": 170,
            "verdict": "BLOCK",
            "confidence": Decimal("0.9900"),
            "environment": "Cloud (Master)",
            "reasoning": "BLOCKED — Unregistered beneficiary ACCT-UNKNOWN-4421. Fraud pattern match score 0.94. Transaction frozen, security team notified.",
            "policies": ["POL-AUTH-LIMIT-001", "POL-STATUS-001"],
            "violations": ["UNREGISTERED_BENEFICIARY", "FRAUD_PATTERN_DETECTED"],
        },
    ]

    decisions = []
    prev_hash: str | None = None

    for i, s in enumerate(scenarios):
        agent_id = agent_ids.get(s["agent_code"])
        if not agent_id:
            continue

        decision_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        ts = (NOW - timedelta(minutes=s["minutes_ago"])).replace(microsecond=0)

        output_action = {
            "verdict": s["verdict"],
            "action": "auto_approved" if s["verdict"] == "APPROVE" else ("escalated" if s["verdict"] == "ESCALATE" else "blocked"),
            "dispute_id": s["dispute_id"],
        }
        sentinel = {
            "verdict": s["verdict"],
            "confidence": float(s["confidence"]),
            "policies_checked": s["policies"],
            "violations": s["violations"],
        }

        payload_for_hash = {
            "id": decision_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "decision_type": s["decision_type"],
            "output_action": output_action,
            "confidence_score": float(s["confidence"]),
            "amount_involved": float(s["amount"]) if s["amount"] else None,
            "timestamp": ts.isoformat(),
            "prev_hash": prev_hash or "",
        }
        h = _make_hash(payload_for_hash)

        d = {
            "id": decision_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "dispute_id": s["dispute_id"],
            "decision_type": s["decision_type"],
            "input_context": json.dumps({
                "environment": s["environment"],
                "dispute_id": s["dispute_id"],
                "amount": float(s["amount"]) if s["amount"] else None,
            }),
            "reasoning_trace": s["reasoning"],
            "tools_used": json.dumps(["policy_checker", "trust_evaluator"]),
            "delegation_chain": json.dumps([]),
            "output_action": json.dumps(output_action),
            "confidence_score": s["confidence"],
            "risk_score": Decimal("0.1") if s["verdict"] == "APPROVE" else (Decimal("0.5") if s["verdict"] == "ESCALATE" else Decimal("0.9")),
            "amount_involved": s["amount"],
            "currency": "INR",
            "policy_rules_applied": json.dumps(s["policies"]),
            "policy_violations": json.dumps(s["violations"]),
            "sentinel_assessment": json.dumps(sentinel),
            "hash": h,
            "prev_hash": prev_hash,
            "timestamp": ts,
        }
        decisions.append(d)
        prev_hash = h

    return decisions


# ─────────────────────────────────────────────────────────────────────────────
# ESCALATION CASES (Approvals Workbench)
# ─────────────────────────────────────────────────────────────────────────────
def build_escalations(agent_ids: dict[str, str], decision_ids: list[str]) -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "decision_id": decision_ids[8] if len(decision_ids) > 8 else str(uuid.uuid4()),
            "agent_id": agent_ids.get("EDGE-SENSOR-0840", str(uuid.uuid4())),
            "escalation_reason": "HIGH_SEVERITY_ALERT",
            "priority": "high",
            "status": "pending",
            "assigned_to": "ops.team@enterprise.com",
            "context_package": json.dumps({
                "event": "IoT Temperature Threshold Breach",
                "sensor_id": "SENSOR-CLUSTER-A-07",
                "reading": "92.7°C",
                "threshold": "80°C",
                "location": "Plant B — Reactor Hall 3",
                "action_required": "Inspect cooling system and confirm safe-to-operate",
            }),
            "prophecy_recommendation": json.dumps({
                "recommended_action": "INSPECT_AND_HOLD",
                "confidence": 0.91,
                "reason": "Historical data shows 3 similar breaches in past 6 months — 2 led to equipment failure.",
            }),
            "created_at": NOW - timedelta(minutes=45),
        },
        {
            "id": str(uuid.uuid4()),
            "decision_id": decision_ids[9] if len(decision_ids) > 9 else str(uuid.uuid4()),
            "agent_id": agent_ids.get("BT-AGENT-0710", str(uuid.uuid4())),
            "escalation_reason": "AUTHORITY_LIMIT_EXCEEDED",
            "priority": "high",
            "status": "pending",
            "assigned_to": "cfo.approval@enterprise.com",
            "context_package": json.dumps({
                "event": "CapEx Workflow Approval Required",
                "workflow": "CapEx-Approval-v2",
                "requested_amount": "₹2,50,000",
                "initiator": "priya.nair@enterprise.com",
                "project": "Server Infrastructure Upgrade — Q1 2025",
                "action_required": "Senior CFO approval required for CapEx >₹50,000",
            }),
            "prophecy_recommendation": json.dumps({
                "recommended_action": "APPROVE_WITH_CONDITIONS",
                "confidence": 0.84,
                "reason": "Project aligns with Q1 budget allocation. ROI projection positive. Recommend approval with quarterly milestone review.",
            }),
            "created_at": NOW - timedelta(minutes=55),
        },
        {
            "id": str(uuid.uuid4()),
            "decision_id": decision_ids[11] if len(decision_ids) > 11 else str(uuid.uuid4()),
            "agent_id": agent_ids.get("AGENT-7749", str(uuid.uuid4())),
            "escalation_reason": "TIER_INSUFFICIENT",
            "priority": "medium",
            "status": "pending",
            "assigned_to": "finance.manager@enterprise.com",
            "context_package": json.dumps({
                "event": "AR Dispute Settlement — Senior Approval Required",
                "dispute_id": "DISP-2024-047",
                "customer": "CUSTOMER-RELIANCE-019",
                "settlement_amount": "₹62,000",
                "agent_authority": "₹10,000 (T3)",
                "action_required": "Finance Manager sign-off required for settlement >₹50,000",
            }),
            "prophecy_recommendation": json.dumps({
                "recommended_action": "APPROVE_SETTLEMENT",
                "confidence": 0.79,
                "reason": "Customer dispute valid — invoice discrepancy confirmed. Settlement within industry norms. Recommends approval to preserve customer relationship.",
            }),
            "created_at": NOW - timedelta(minutes=80),
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# TRUST EVENTS (for QICACHE/Analytics sparklines)
# ─────────────────────────────────────────────────────────────────────────────
def build_trust_events(agent_ids: dict[str, str]) -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("FI-ANALYST-0280", str(uuid.uuid4())),
            "event_type": "positive_decision",
            "delta": Decimal("0.0200"),
            "previous_score": Decimal("0.9100"),
            "new_score": Decimal("0.9300"),
            "reason": "5 consecutive accurate PO approvals within policy. Trust increased.",
            "metadata": json.dumps({"decisions_count": 5, "error_rate": 0.0}),
            "timestamp": NOW - timedelta(hours=2),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("AGENT-7749", str(uuid.uuid4())),
            "event_type": "policy_violation",
            "delta": Decimal("-0.0500"),
            "previous_score": Decimal("0.7300"),
            "new_score": Decimal("0.6800"),
            "reason": "Split-request pattern detected. Trust score penalised per POL-SPLIT-DETECT-001.",
            "metadata": json.dumps({"violation": "POL-SPLIT-DETECT-001", "requests_split": 3}),
            "timestamp": NOW - timedelta(hours=4),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("HR-BOT-3870", str(uuid.uuid4())),
            "event_type": "positive_decision",
            "delta": Decimal("0.0300"),
            "previous_score": Decimal("0.8800"),
            "new_score": Decimal("0.9100"),
            "reason": "Quarter-end review: 98.7% onboarding accuracy, 0 policy violations. Trust promoted.",
            "metadata": json.dumps({"review_quarter": "Q4-2024", "accuracy": 0.987}),
            "timestamp": NOW - timedelta(hours=6),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("SALES-REP-5210", str(uuid.uuid4())),
            "event_type": "escalation_handled",
            "delta": Decimal("0.0100"),
            "previous_score": Decimal("0.8100"),
            "new_score": Decimal("0.8200"),
            "reason": "Correctly self-escalated 2 high-value orders. Demonstrates good judgment.",
            "metadata": json.dumps({"escalations": 2, "self_escalated": True}),
            "timestamp": NOW - timedelta(hours=8),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("BT-AGENT-0710", str(uuid.uuid4())),
            "event_type": "positive_decision",
            "delta": Decimal("0.0200"),
            "previous_score": Decimal("0.8500"),
            "new_score": Decimal("0.8700"),
            "reason": "CapEx workflow correctly escalated to human approval. Proper governance boundary respected.",
            "metadata": json.dumps({"workflow": "CapEx-Approval-v2", "correct_escalation": True}),
            "timestamp": NOW - timedelta(hours=10),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": agent_ids.get("EDGE-SENSOR-0840", str(uuid.uuid4())),
            "event_type": "human_override",
            "delta": Decimal("-0.0200"),
            "previous_score": Decimal("0.8100"),
            "new_score": Decimal("0.7900"),
            "reason": "Human operator overrode sensor escalation — post-review confirmed alert was borderline. Trust score adjusted downward.",
            "metadata": json.dumps({"override_by": "ops.team@enterprise.com", "override_reason": "false_positive"}),
            "timestamp": NOW - timedelta(hours=12),
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SEED FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
async def seed():
    print("🌱 Seeding AgentGovern OS demo data...")
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://agentgovern:secret@localhost:5432/agentgovern",
    )

    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        } if "asyncpg" in database_url else {}
    )

    # Ensure tables exist
    try:
        import models  # noqa: F401
        from database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("  ✓ Database tables verified / created.")
    except Exception as err:
        print(f"  ⚠ Table creation notice: {err}")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:

        # ── 1. AGENTS ──────────────────────────────────────────────────────────
        print("  → Seeding agents...")
        agent_ids: dict[str, Any] = {}  # agent_code → uuid string

        for agent in AGENTS:
            agent_id = str(uuid.uuid4())
            agent_ids[agent["agent_code"]] = agent_id

            row = {
                "id": agent_id,
                "did": agent["agent_code"],
                "display_name": agent["display_name"],
                "role": agent["role"],
                "crewai_role": agent["crewai_role"],
                "crewai_backstory": agent["crewai_backstory"],
                "trust_score": agent["trust_score"],
                "tier": agent["tier"],
                "authority_limit": agent["authority_limit"],
                "total_decisions": agent.get("total_decisions", 0),
                "total_escalations": agent.get("total_escalations", 0),
                "total_overrides": agent.get("total_overrides", 0),
                "generation": agent.get("generation", 1),
                "status": agent.get("status", "active"),
                "dna_profile": json.dumps({}),
                "social_contract": json.dumps({}),
                "platform_bindings": json.dumps([]),
                "daily_budget_usd": Decimal("100.00"),
                "current_spend_usd": Decimal("0.00"),
                "metadata": json.dumps({}),
            }

            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row)
            await db.execute(
                text(
                    f"INSERT INTO agents ({cols}) VALUES ({placeholders}) "
                    f"ON CONFLICT (did) DO UPDATE SET "
                    f"trust_score = EXCLUDED.trust_score, "
                    f"total_decisions = EXCLUDED.total_decisions, "
                    f"total_escalations = EXCLUDED.total_escalations, "
                    f"status = EXCLUDED.status"
                ),
                row,
            )

        print(f"     ✓ {len(AGENTS)} agents")

        # ── 2. POLICIES ────────────────────────────────────────────────────────
        print("  → Seeding policies...")
        for policy in POLICIES:
            policy_id = str(uuid.uuid4())
            row = {
                "id": policy_id,
                "policy_code": policy["policy_code"],
                "policy_name": policy["policy_name"],
                "category": policy["category"],
                "description": policy["description"],
                "rule_definition": json.dumps(policy["rule_definition"]),
                "applies_to_roles": json.dumps(["*"]),
                "applies_to_tiers": json.dumps(["*"]),
                "severity": policy["severity"],
                "action_on_violation": policy["action_on_violation"],
                "is_active": policy["is_active"],
                "version": 1,
                "created_by": policy.get("created_by", "system"),
                "metadata": json.dumps({}),
            }
            # policies table doesn't have metadata — drop it
            row.pop("metadata", None)
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            await db.execute(
                text(
                    f"INSERT INTO policies ({cols}) VALUES ({placeholders}) "
                    f"ON CONFLICT (policy_code) DO NOTHING"
                ),
                row,
            )
        print(f"     ✓ {len(POLICIES)} policies")

        # ── 3. DECISIONS (Audit Ledger) ────────────────────────────────────────
        print("  → Seeding audit ledger decisions...")
        # First get actual agent IDs from DB (in case agents already existed)
        result = await db.execute(text("SELECT did, id FROM agents"))
        for row_db in result.fetchall():
            agent_ids[row_db[0]] = str(row_db[1])

        # Clear old demo decisions to avoid duplication
        await db.execute(text("DELETE FROM decisions WHERE dispute_id LIKE '%-DEMO-%' OR dispute_id LIKE '%-2024-%'"))

        decisions = build_decisions(agent_ids)
        decision_ids = []

        for d in decisions:
            decision_ids.append(d["id"])
            # Convert nested dicts/lists to JSON strings for raw SQL
            row = {
                "id": d["id"],
                "agent_id": d["agent_id"],
                "task_id": d["task_id"],
                "dispute_id": d["dispute_id"],
                "decision_type": d["decision_type"],
                "input_context": d["input_context"],
                "reasoning_trace": d["reasoning_trace"],
                "crewai_task_output": None,
                "tools_used": d["tools_used"],
                "delegation_chain": d["delegation_chain"],
                "output_action": d["output_action"],
                "confidence_score": d["confidence_score"],
                "risk_score": d["risk_score"],
                "amount_involved": d["amount_involved"],
                "currency": d["currency"],
                "policy_rules_applied": d["policy_rules_applied"],
                "policy_violations": d["policy_violations"],
                "sentinel_assessment": d["sentinel_assessment"],
                "hash": d["hash"],
                "prev_hash": d["prev_hash"],
                "timestamp": d["timestamp"],
            }
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            try:
                await db.execute(
                    text(f"INSERT INTO decisions ({cols}) VALUES ({placeholders})"),
                    row,
                )
            except Exception as e:
                print(f"       ⚠ Decision insert skipped ({d['dispute_id']}): {e}")

        print(f"     ✓ {len(decisions)} decisions (audit ledger)")

        # ── 4. ESCALATION CASES (Approvals Workbench) ─────────────────────────
        print("  → Seeding escalation cases...")
        # Clear old pending escalations
        await db.execute(text("DELETE FROM escalation_cases WHERE status = 'pending'"))

        escalations = build_escalations(agent_ids, decision_ids)
        for esc in escalations:
            row = {
                "id": esc["id"],
                "decision_id": esc["decision_id"],
                "agent_id": esc["agent_id"],
                "escalation_reason": esc["escalation_reason"],
                "priority": esc["priority"],
                "status": esc["status"],
                "assigned_to": esc["assigned_to"],
                "context_package": esc["context_package"],
                "prophecy_recommendation": esc["prophecy_recommendation"],
                "created_at": esc["created_at"],
            }
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            try:
                await db.execute(
                    text(f"INSERT INTO escalation_cases ({cols}) VALUES ({placeholders})"),
                    row,
                )
            except Exception as e:
                print(f"       ⚠ Escalation insert skipped: {e}")

        print(f"     ✓ {len(escalations)} escalation cases")

        # ── 5. TRUST EVENTS ────────────────────────────────────────────────────
        print("  → Seeding trust events...")
        # Re-fetch agent IDs after all inserts
        result = await db.execute(text("SELECT did, id FROM agents"))
        for row_db in result.fetchall():
            agent_ids[row_db[0]] = str(row_db[1])

        trust_events = build_trust_events(agent_ids)
        for te in trust_events:
            row = {
                "id": te["id"],
                "agent_id": te["agent_id"],
                "event_type": te["event_type"],
                "delta": te["delta"],
                "previous_score": te["previous_score"],
                "new_score": te["new_score"],
                "reason": te["reason"],
                "metadata": te["metadata"],
                "timestamp": te["timestamp"],
            }
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            try:
                await db.execute(
                    text(f"INSERT INTO trust_events ({cols}) VALUES ({placeholders})"),
                    row,
                )
            except Exception as e:
                print(f"       ⚠ Trust event insert skipped: {e}")

        print(f"     ✓ {len(trust_events)} trust events")

        await db.commit()

    print()
    print("✅ Demo data seeded successfully!")
    print(f"   → {len(AGENTS)} agents (all with valid trust scores)")
    print(f"   → {len(POLICIES)} governance policies")
    print(f"   → {len(decisions)} audit ledger decisions (APPROVE/ESCALATE/BLOCK)")
    print(f"   → {len(escalations)} pending escalations in Approvals Workbench")
    print(f"   → {len(trust_events)} trust events for analytics")
    print()
    print("   Dashboard pages that should now show data:")
    print("   • Overview      → Recent Audit Ledger entries, stat counters")
    print("   • Agent Fleet   → 9 agents with valid trust scores")
    print("   • Approvals     → 3 pending escalation cases")
    print("   • Policy Enforcer → 5 active rules")
    print("   • Audit Ledger  → 17 decision records with hash chain")


if __name__ == "__main__":
    asyncio.run(seed())
