#!/usr/bin/env python3
"""
AgentGovern OS — End-to-End Demo Script
========================================
Demonstrates the complete distributed governance lifecycle:

  SAP BTP Event
    → SAP BTP Adapter (normalize)
    → SENTINEL Policy Engine (evaluate)
    → ANCESTOR Audit Chain (log)
    → React Dashboard (display live)

Usage:
  python scripts/demo_flow.py [--seed] [--live]

Flags:
  --seed    Seed demo agents and policies into the governance API first
  --live    Run continuous event stream (simulates live SAP production traffic)

Prerequisites:
  - Governance API running on localhost:8000
  - SAP BTP Adapter running on localhost:8001
"""

import asyncio
import argparse
import uuid
import json
import time
from datetime import datetime, timezone
import httpx

# ─── Config ───────────────────────────────────────────────────────────────────

GOVERNANCE_API = "http://localhost:8000"
SAP_ADAPTER_API = "http://localhost:8002"

# ─── Demo Agent Definitions ───────────────────────────────────────────────────

DEMO_AGENTS = [
    {
        "agent_code": "FI-ANALYST-DEMO",
        "display_name": "Finance Analyst Agent",
        "role": "fi_analyst",
        "crewai_role": "Senior Financial Analyst responsible for procurement and payment approvals",
        "crewai_backstory": "I analyze financial transactions and enforce spending policies across the enterprise. I have access to SAP S/4HANA Finance module and comply with SOX and internal audit requirements.",
        "tier": "T2",
        "dna_profile": {"specialization": "finance", "risk_tolerance": "medium"},
        "platform_bindings": ["SAP_S4HANA", "SAP_BTP", "CLOUD_AWS"],
    },
    {
        "agent_code": "HR-BOT-DEMO",
        "display_name": "HR Process Bot",
        "role": "hr_bot",
        "crewai_role": "Human Resources Automation Agent handling employee lifecycle events",
        "crewai_backstory": "I manage employee onboarding, access provisioning, and termination workflows. I handle sensitive PII and strictly follow GDPR and internal data governance policies.",
        "tier": "T3",
        "dna_profile": {"specialization": "hr", "risk_tolerance": "low"},
        "platform_bindings": ["SAP_SUCCESSFACTORS", "SAP_BTP"],
    },
    {
        "agent_code": "SALES-REP-DEMO",
        "display_name": "Sales Automation Agent",
        "role": "sales_rep",
        "crewai_role": "Sales Process Automation Agent managing order approvals and discount issuance",
        "crewai_backstory": "I handle sales order creation and discount approval workflows in SAP S/4HANA Sales module. I enforce pricing policies and margin protection rules.",
        "tier": "T3",
        "dna_profile": {"specialization": "sales", "risk_tolerance": "medium"},
        "platform_bindings": ["SAP_S4HANA_SALES", "SAP_BTP"],
    },
    {
        "agent_code": "EDGE-SENSOR-DEMO",
        "display_name": "Edge IoT Sensor Agent",
        "role": "edge_sensor",
        "crewai_role": "Edge Gateway IoT monitoring and threshold alert agent",
        "crewai_backstory": "I monitor IoT sensors at edge locations, detect threshold breaches, and trigger alert notifications through SAP BTP Alert Notification Service.",
        "tier": "T4",
        "dna_profile": {"specialization": "iot", "risk_tolerance": "high"},
        "platform_bindings": ["SAP_BTP_ALERT", "EDGE_IOT"],
    },
    {
        "agent_code": "BTP-AGENT-DEMO",
        "display_name": "BTP Workflow Orchestrator",
        "role": "btp_agent",
        "crewai_role": "SAP BTP Workflow Service integration agent",
        "crewai_backstory": "I orchestrate complex multi-step workflows in SAP BTP. I coordinate approvals and delegate tasks across the enterprise.",
        "tier": "T2",
        "dna_profile": {"specialization": "workflow", "risk_tolerance": "low"},
        "platform_bindings": ["SAP_BTP_WORKFLOW", "SAP_BTP"],
    },
]

# ─── Demo Policy Definitions ───────────────────────────────────────────────────

DEMO_POLICIES = [
    {
        "policy_code": "POL-FI-AMOUNT-LIMIT-001",
        "policy_name": "Finance Agent Purchase Order Limit",
        "category": "authority",
        "description": "Finance agents cannot approve purchase orders above ₹1,00,000 without human escalation.",
        "rule_definition": {"type": "amount_limit", "max_amount": 100000},
        "applies_to_roles": ["fi_analyst"],
        "applies_to_tiers": ["*"],
        "severity": "high",
        "action_on_violation": "escalate",
    },
    {
        "policy_code": "POL-GLOBAL-TRUST-MIN-001",
        "policy_name": "Minimum Trust Score for Autonomous Action",
        "category": "trust",
        "description": "All agents must have a trust score of at least 0.40 to execute actions autonomously.",
        "rule_definition": {"type": "trust_minimum", "min_trust": 0.40},
        "applies_to_roles": ["*"],
        "applies_to_tiers": ["*"],
        "severity": "critical",
        "action_on_violation": "block",
    },
    {
        "policy_code": "POL-HR-ACCESS-CONTROL-001",
        "policy_name": "HR PII Access Control",
        "category": "data_governance",
        "description": "HR agents are permitted to access PII only during active business hours.",
        "rule_definition": {"type": "status_check", "required_status": "active"},
        "applies_to_roles": ["hr_bot"],
        "applies_to_tiers": ["*"],
        "severity": "critical",
        "action_on_violation": "block",
    },
    {
        "policy_code": "POL-SALES-DISCOUNT-LIMIT-001",
        "policy_name": "Sales Discount Authority Limit",
        "category": "authority",
        "description": "Sales agents cannot issue discounts on orders above ₹50,000.",
        "rule_definition": {"type": "amount_limit", "max_amount": 50000},
        "applies_to_roles": ["sales_rep"],
        "applies_to_tiers": ["*"],
        "severity": "medium",
        "action_on_violation": "escalate",
    },
    {
        "policy_code": "POL-EDGE-TIER-REQUIRE-001",
        "policy_name": "Edge Tier Access Restriction",
        "category": "environment",
        "description": "Only T4 agents are permitted to operate on bare edge environments.",
        "rule_definition": {"type": "tier_required", "allowed_tiers": ["T4", "T3"]},
        "applies_to_roles": ["edge_sensor"],
        "applies_to_tiers": ["T4", "T3"],
        "severity": "medium",
        "action_on_violation": "block",
    },
]

# ─── Demo SAP Events ───────────────────────────────────────────────────────────

def build_demo_events -> list[dict]:
    """Build a realistic sequence of SAP BTP events for the demo."""
    return [
        # 1. Small finance event → APPROVE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/s4hana-prod/purchaseorder",
            "type": "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
            "sap_source_system": "S4H-PROD-001",
            "data": {
                "PurchaseOrder": f"PO-{uuid.uuid4.hex[:6].upper}",
                "Supplier": "VENDOR-TATA-001",
                "NetAmount": 45000,
                "DocumentCurrency": "INR",
                "CompanyCode": "1000",
                "PurchasingGroup": "G01",
            },
        },
        # 2. Large finance event → ESCALATE (exceeds limit)
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/s4hana-prod/purchaseorder",
            "type": "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Created.v1",
            "sap_source_system": "S4H-PROD-001",
            "data": {
                "PurchaseOrder": f"PO-{uuid.uuid4.hex[:6].upper}",
                "Supplier": "VENDOR-INFOSYS-003",
                "NetAmount": 850000,
                "DocumentCurrency": "INR",
                "CompanyCode": "1000",
                "PurchasingGroup": "G01",
            },
        },
        # 3. HR onboarding → APPROVE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/successfactors/employee",
            "type": "sap.s4.beh.employee.v1.Employee.Onboarded.v1",
            "sap_source_system": "SF-PROD-001",
            "data": {
                "EmployeeId": f"EMP-{uuid.uuid4.hex[:6].upper}",
                "FirstName": "Ravi",
                "LastName": "Shankar",
                "Department": "Engineering",
                "StartDate": datetime.now(timezone.utc).date.isoformat,
            },
        },
        # 4. Sales order → APPROVE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/s4hana-prod/salesorder",
            "type": "sap.s4.beh.salesorder.v1.SalesOrder.Created.v1",
            "sap_source_system": "S4H-PROD-001",
            "data": {
                "SalesOrder": f"SO-{uuid.uuid4.hex[:6].upper}",
                "SoldToParty": "CUSTOMER-WIPRO-007",
                "TotalNetAmount": 12000,
                "TransactionCurrency": "INR",
                "SalesOrganization": "1000",
            },
        },
        # 5. IoT threshold breach → ESCALATE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/btp/alert-notification/iot-sensor-cluster-a",
            "type": "com.sap.alert.notification.v1.AlertNotification.Triggered.v1",
            "sap_source_system": "EDGE-CLUSTER-A",
            "data": {
                "alertType": "THRESHOLD_BREACH",
                "resourceName": "EDGE-SENSOR-47",
                "region": "ap-south-1",
                "thresholdValue": 92.7,
                "unit": "celsius",
                "severity": "HIGH",
                "message": "Temperature exceeds critical threshold",
            },
        },
        # 6. BTP Workflow → ESCALATE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/btp/workflow/process-integration",
            "type": "com.sap.btp.workflow.v1.WorkflowInstance.Started.v1",
            "sap_source_system": "BTP-INTEGRATION-001",
            "data": {
                "workflowInstanceId": str(uuid.uuid4),
                "workflowDefinitionId": "CapEx-Approval-v2",
                "status": "started",
                "initiatedBy": "priya.nair@enterprise.com",
            },
        },
        # 7. Payment posting → APPROVE
        {
            "specversion": "1.0",
            "id": str(uuid.uuid4),
            "source": "/sap/s4hana-prod/paymentadvice",
            "type": "sap.s4.beh.paymentAdvice.v1.PaymentAdvice.Posted.v1",
            "sap_source_system": "S4H-PROD-001",
            "data": {
                "PaymentAdvice": f"PA-{uuid.uuid4.hex[:6].upper}",
                "Payee": "VENDOR-TATA-001",
                "Amount": 45000,
                "Currency": "INR",
                "PostingDate": datetime.now(timezone.utc).date.isoformat,
            },
        },
    ]


# ─── Seeding ───────────────────────────────────────────────────────────────────

async def seed_agents(client: httpx.AsyncClient) -> dict[str, str]:
    """Seed demo agents into the governance registry. Returns {agent_code: id}."""
    print("\n📋 Seeding demo agents...")
    agent_ids: dict[str, str] = {}

    for agent_def in DEMO_AGENTS:
        try:
            resp = await client.post(
                f"{GOVERNANCE_API}/api/v1/agents/",
                json=agent_def,
                timeout=10.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json
                agent_ids[agent_def["agent_code"]] = data["id"]
                print(f"  ✅ Registered: {agent_def['agent_code']} (ID: {data['id'][:8]}...)")
            elif resp.status_code == 409:
                # Already exists — fetch the ID
                list_resp = await client.get(
                    f"{GOVERNANCE_API}/api/v1/agents/",
                    params={"role": agent_def["role"], "limit": 1},
                )
                if list_resp.status_code == 200 and list_resp.json.get("agents"):
                    existing = list_resp.json["agents"][0]
                    agent_ids[agent_def["agent_code"]] = existing["id"]
                    print(f"  ♻️  Already exists: {agent_def['agent_code']}")
            else:
                print(f"  ⚠️  Failed to register {agent_def['agent_code']}: {resp.status_code}")
        except httpx.RequestError as e:
            print(f"  ❌ Error registering {agent_def['agent_code']}: {e}")

    return agent_ids


async def seed_policies(client: httpx.AsyncClient) -> None:
    """Seed governance policies into SENTINEL."""
    print("\n📋 Seeding governance policies...")

    for policy_def in DEMO_POLICIES:
        try:
            resp = await client.post(
                f"{GOVERNANCE_API}/api/v1/policies/",
                json=policy_def,
                timeout=10.0,
            )
            if resp.status_code in (200, 201):
                print(f"  ✅ Created policy: {policy_def['policy_code']}")
            elif resp.status_code == 409:
                print(f"  ♻️  Policy exists: {policy_def['policy_code']}")
            else:
                print(f"  ⚠️  Failed to create {policy_def['policy_code']}: {resp.status_code}")
        except httpx.RequestError as e:
            print(f"  ❌ Error creating policy: {e}")


# ─── Demo Event Flow ───────────────────────────────────────────────────────────

async def run_demo_events(client: httpx.AsyncClient, continuous: bool = False) -> None:
    """Fire SAP events through the adapter and display governance verdicts."""
    events = build_demo_events

    if continuous:
        print("\n🔁 Running continuous event stream (Ctrl+C to stop)...")
        iteration = 0
        while True:
            event = events[iteration % len(events)]
            event["id"] = str(uuid.uuid4)  # Fresh ID each time
            await process_single_event(client, event, iteration + 1)
            iteration += 1
            await asyncio.sleep(3)  # 3 seconds between events
    else:
        print(f"\n🚀 Running {len(events)} SAP BTP demo events through AgentGovern OS...\n")
        print("─" * 80)
        for i, event in enumerate(events, 1):
            await process_single_event(client, event, i)
            await asyncio.sleep(0.5)  # Small delay for readability


async def process_single_event(client: httpx.AsyncClient, event: dict, num: int) -> None:
    """Send a single SAP event to the adapter and print the governance result."""
    event_type_short = event["type"].split(".")[-2]  # e.g. "PurchaseOrder"
    amount = event["data"].get("NetAmount") or event["data"].get("Amount") or event["data"].get("TotalNetAmount")
    amount_str = f" (₹{amount:,.0f})" if amount else ""

    print(f"[{num:02d}] 📤 SAP Event: {event_type_short}{amount_str}")
    print(f"      Source: {event['sap_source_system']} → {event['source']}")

    try:
        resp = await client.post(
            f"{SAP_ADAPTER_API}/sap/governance/evaluate",
            json=event,
            timeout=15.0,
        )

        if resp.status_code == 200:
            result = resp.json
            verdict = result["verdict"]
            confidence = result["confidence"]
            workflow = result["workflow_decision"]
            human_review = "🔔 Human Review Required" if result["requires_human_review"] else "🤖 Autonomous"

            verdict_icon = {"APPROVE": "✅", "BLOCK": "🚫", "ESCALATE": "⚠️"}.get(verdict, "❓")
            print(f"      {verdict_icon} Verdict: {verdict} ({confidence:.0%} confidence) → SAP: {workflow}")
            print(f"      {human_review}")
            if result["reasoning"]:
                # Truncate long reasoning
                reasoning = result["reasoning"][:120] + ("..." if len(result["reasoning"]) > 120 else "")
                print(f"      Reasoning: {reasoning}")
            if result["policy_violations"]:
                print(f"      ⚔️  Policy violations: {', '.join(result['policy_violations'])}")
        else:
            print(f"      ❌ Adapter error: HTTP {resp.status_code}")
            print(f"      {resp.text[:200]}")

    except httpx.ConnectError:
        print(f"      ❌ Could not connect to SAP BTP Adapter at {SAP_ADAPTER_API}")
        print(f"         Make sure the adapter is running: uvicorn services.sap-btp-adapter.main:app --port 8001")
    except Exception as e:
        print(f"      ❌ Unexpected error: {e}")

    print("─" * 80)


# ─── Health Check ──────────────────────────────────────────────────────────────

async def check_services(client: httpx.AsyncClient) -> bool:
    """Verify all services are running before the demo."""
    print("🔍 Checking service health...")
    all_ok = True

    services = [
        (GOVERNANCE_API, "AgentGovern Governance API"),
        (SAP_ADAPTER_API, "SAP BTP Adapter"),
    ]

    for url, name in services:
        try:
            resp = await client.get(f"{url}/health", timeout=3.0)
            if resp.status_code == 200:
                print(f"  ✅ {name} → {url}/health")
            else:
                print(f"  ⚠️  {name} responded with HTTP {resp.status_code}")
        except httpx.ConnectError:
            print(f"  ❌ {name} is NOT running at {url}")
            all_ok = False

    return all_ok


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main:
    parser = argparse.ArgumentParser(description="AgentGovern OS Demo Flow")
    parser.add_argument("--seed", action="store_true", help="Seed agents and policies first")
    parser.add_argument("--live", action="store_true", help="Continuous live event stream")
    args = parser.parse_args

    print("=" * 80)
    print("   AgentGovern OS — End-to-End Demo")
    print("   Distributed Governance Platform for Enterprise AI Agents")
    print("=" * 80)
    print(f"   Governance API : {GOVERNANCE_API}")
    print(f"   SAP Adapter    : {SAP_ADAPTER_API}")
    print(f"   Time           : {datetime.now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    async with httpx.AsyncClient as client:
        # Health check
        services_ok = await check_services(client)

        if not services_ok:
            print("\n❌ Some services are not running. Please start all services and try again.")
            print("\nQuick start:")
            print("  Governance API : cd services/governance-api && uvicorn main:app --port 8000 --reload")
            print("  SAP Adapter    : cd services/sap-btp-adapter && uvicorn main:app --port 8001 --reload")
            return

        # Optionally seed test data
        if args.seed:
            await seed_agents(client)
            await seed_policies(client)
            print

        # Run demo events
        await run_demo_events(client, continuous=args.live)

        if not args.live:
            print("\n✅ Demo complete!")
            print(f"   View live results: http://localhost:5173 (React Dashboard)")
            print(f"   API Documentation: {GOVERNANCE_API}/docs")
            print(f"   Adapter Docs     : {SAP_ADAPTER_API}/docs")


if __name__ == "__main__":
    asyncio.run(main)
