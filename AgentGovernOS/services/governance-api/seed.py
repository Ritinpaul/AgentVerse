import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from database import async_session, init_db  # pyre-ignore[21]
from models import Agent, Decision, EscalationCase, Policy, TrustEvent  # pyre-ignore[21]
from sqlalchemy import select  # pyre-ignore[21]


async def seed_data():
    await init_db
    
    async with async_session as session:
        # Check if already seeded
        result = await session.execute(select(Agent))
        if result.scalars.first:
            print("Database already seeded. Delete the db file to re-seed if you are using sqlite.")
            return
            
        print("Seeding agents...")
        agent1 = Agent(
            id=uuid.uuid4,
            agent_code="FIN-001",
            display_name="Finance Auditor Beta",
            role="Financial Auditor",
            crewai_role="Senior Financial Auditor",
            crewai_backstory="An expert in financial compliance and anomaly detection.",
            status="active",
            trust_score=Decimal("0.8500"),
            authority_limit=Decimal("50000.00"),
            tier="T2",
            generation=1,
            total_decisions=142,
            total_escalations=3,
            total_overrides=1,
        )
        
        agent2 = Agent(
            id=uuid.uuid4,
            agent_code="HR-002",
            display_name="HR Policy Enforcer",
            role="HR Compliance",
            crewai_role="HR Compliance Specialist",
            crewai_backstory="Specializes in checking employee expenses against HR policies.",
            status="active",
            trust_score=Decimal("0.9200"),
            authority_limit=Decimal("10000.00"),
            tier="T3",
            generation=1,
            total_decisions=89,
            total_escalations=0,
            total_overrides=0,
        )

        agent3 = Agent(
            id=uuid.uuid4,
            agent_code="SEC-001",
            display_name="Security Sentinel (New)",
            role="Security Monitoring",
            crewai_role="Infrastructure Security Monitor",
            crewai_backstory="Monitors access logs and flags suspicious activity.",
            status="probation",
            trust_score=Decimal("0.5000"),
            authority_limit=Decimal("0.00"),
            tier="T4",
            generation=1,
            total_decisions=5,
            total_escalations=5,
            total_overrides=0,
        )

        session.add_all([agent1, agent2, agent3])
        await session.flush()

        print("Seeding policies...")
        policy1 = Policy(
            id=uuid.uuid4,
            policy_code="POL-FIN-101",
            policy_name="Expense Limit Enforcement",
            category="Finance",
            description="Blocks any expense over 10k without explicit human approval.",
            rule_definition={"max_amount": 10000, "currency": "USD"},
            applies_to_roles=["Financial Auditor", "HR Compliance"],
            applies_to_tiers=["*"],
            severity="high",
            action_on_violation="block",
            is_active=True
        )
        
        policy2 = Policy(
            id=uuid.uuid4,
            policy_code="POL-SEC-001",
            policy_name="Off-hours Access Flag",
            category="Security",
            description="Requires escalation for infrastructure access outside business hours.",
            rule_definition={"allowed_hours": "08:00-18:00"},
            applies_to_roles=["Security Monitoring"],
            applies_to_tiers=["T3", "T4"],
            severity="medium",
            action_on_violation="escalate",
            is_active=True
        )
        
        session.add_all([policy1, policy2])
        await session.flush()

        print("Seeding decisions...")
        now = datetime.now(UTC)
        
        dec1 = Decision(
            id=uuid.uuid4,
            agent_id=agent1.id,
            task_id=uuid.uuid4,
            decision_type="expense_approval",
            input_context={"expense_id": "EXP-992", "amount": 8500, "employee": "John Doe"},
            reasoning_trace="Expense amount 8500 is within the 10000 limit. No anomalies found in receipt.",
            output_action={"action": "approve", "reason": "Compliant with POL-FIN-101"},
            confidence_score=Decimal("0.9500"),
            risk_score=Decimal("0.1000"),
            amount_involved=Decimal("8500.00"),
            currency="USD",
            policy_rules_applied=["POL-FIN-101"],
            hash="abc123hash1",
            timestamp=now - timedelta(hours=2)
        )

        dec2 = Decision(
            id=uuid.uuid4,
            agent_id=agent2.id,
            task_id=uuid.uuid4,
            decision_type="leave_approval",
            input_context={"employee_id": "EMP-404", "days": 3},
            reasoning_trace="Employee EMP-404 has 15 days of PTO remaining. Request is for 3 days. Approving.",
            output_action={"action": "approve"},
            confidence_score=Decimal("0.9900"),
            risk_score=Decimal("0.0500"),
            policy_rules_applied=[],
            hash="def456hash2",
            timestamp=now - timedelta(minutes=45)
        )
        
        session.add_all([dec1, dec2])
        await session.flush()

        print("Seeding escalations...")
        # Need a decision for the escalation
        dec3 = Decision(
            id=uuid.uuid4,
            agent_id=agent1.id,
            task_id=uuid.uuid4,
            decision_type="expense_approval",
            input_context={"expense_id": "EXP-993", "amount": 15000, "employee": "Jane Smith"},
            reasoning_trace="Expense amount 15000 exceeds the 10000 limit set by POL-FIN-101. Escalating to human.",
            output_action={"action": "escalate", "reason": "Amount exceeds threshold"},
            confidence_score=Decimal("0.8000"),
            risk_score=Decimal("0.7500"),
            amount_involved=Decimal("15000.00"),
            currency="USD",
            policy_rules_applied=["POL-FIN-101"],
            hash="ghi789hash3",
            timestamp=now - timedelta(minutes=15)
        )
        session.add(dec3)
        await session.flush()
        
        esc1 = EscalationCase(
            id=uuid.uuid4,
            decision_id=dec3.id,
            agent_id=agent1.id,
            escalation_reason="policy_violation",
            priority="high",
            status="pending",
            context_package={"expense_amount": 15000, "limit": 10000},
            prophecy_recommendation={"proposed_action": "reject", "confidence": 0.88},
            created_at=now - timedelta(minutes=15)
        )
        session.add(esc1)
        
        print("Seeding trust events...")
        te1 = TrustEvent(
            id=uuid.uuid4,
            agent_id=agent1.id,
            event_type="successful_audit",
            trigger_decision_id=dec1.id,
            delta=Decimal("0.0100"),
            previous_score=Decimal("0.8400"),
            new_score=Decimal("0.8500"),
            reason="Correctly approved compliant expense.",
            timestamp=now - timedelta(hours=1)
        )
        session.add(te1)

        await session.commit()
        print("Database successfully seeded with mock data!")

if __name__ == "__main__":
    asyncio.run(seed_data)
