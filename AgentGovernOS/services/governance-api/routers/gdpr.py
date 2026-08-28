"""GDPR Router — Data Export and Right-to-Erasure compliance endpoints.

Endpoints:
  GET    /api/v1/gdpr/export/{agent_id}   — Export all personal/operational data for an agent
  DELETE /api/v1/gdpr/forget/{agent_id}   — Right to Erasure: anonymise all agent data
  GET    /api/v1/gdpr/report              — Platform-level GDPR data inventory report

These endpoints require admin or auditor role.
"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from middleware.auth import ROLE_ADMIN, ROLE_AUDITOR, require_roles
from models import (
    Agent,
    Decision,
    EscalationCase,
    QueryCache,
    SocialContract,
    TrustEvent,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from models import AuditLog
except ImportError:  # pragma: no cover - compatibility for schemas missing AuditLog model
    AuditLog = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gdpr", tags=["gdpr"])


# ──────────────────────────────────────────────────────────────────────────────
# GET /gdpr/export/{agent_id}  — full data portability export
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/export/{agent_id}",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_AUDITOR))],
)
async def export_agent_data(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Export ALL data held for an agent (GDPR Article 20 — Data Portability).

    Returns a structured JSON document containing every record associated
    with the agent across all platform subsystems.

    Required role: admin or auditor.
    """
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # ── Trust Events ──
    trust_result = await db.execute(
        select(TrustEvent).where(TrustEvent.agent_id == agent_id)
        .order_by(TrustEvent.created_at.asc)
    )
    trust_events = trust_result.scalars.all

    # ── Decisions ──
    decision_result = await db.execute(
        select(Decision).where(Decision.agent_id == agent_id)
        .order_by(Decision.timestamp.asc)
    )
    decisions = decision_result.scalars.all

    # ── Escalation Cases ──
    esc_result = await db.execute(
        select(EscalationCase).where(EscalationCase.agent_id == agent_id)
        .order_by(EscalationCase.created_at.asc)
    )
    escalations = esc_result.scalars.all

    # ── Social Contracts ──
    contract_result = await db.execute(
        select(SocialContract).where(SocialContract.agent_id == agent_id)
        .order_by(SocialContract.created_at.asc)
    )
    contracts = contract_result.scalars.all

    # ── Query Cache Entries ──
    cache_result = await db.execute(
        select(QueryCache).where(QueryCache.created_by_agent_id == agent_id)
        .order_by(QueryCache.created_at.asc)
    )
    cache_entries = cache_result.scalars.all

    def _serialise_model(obj) -> dict:
        """Convert ORM row to plain dict, handling Decimal/UUID/datetime."""
        from decimal import Decimal
        result = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name, None)
            if isinstance(val, UUID):
                result[col.name] = str(val)
            elif isinstance(val, Decimal):
                result[col.name] = float(val)
            elif isinstance(val, datetime):
                result[col.name] = val.isoformat
            else:
                result[col.name] = val
        return result

    exported_at = datetime.now(UTC).isoformat

    return {
        "export_metadata": {
            "exported_at": exported_at,
            "agent_id": str(agent_id),
            "gdpr_basis": "Article 20 — Right to Data Portability",
            "platform": "AgentGovern OS",
        },
        "agent_profile": _serialise_model(agent),
        "trust_events": [_serialise_model(e) for e in trust_events],
        "decisions": [_serialise_model(d) for d in decisions],
        "escalations": [_serialise_model(e) for e in escalations],
        "social_contracts": [_serialise_model(c) for c in contracts],
        "cache_contributions": [_serialise_model(c) for c in cache_entries],
        "data_summary": {
            "trust_events": len(trust_events),
            "decisions": len(decisions),
            "escalations": len(escalations),
            "social_contracts": len(contracts),
            "cache_entries": len(cache_entries),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /gdpr/forget/{agent_id}  — right to erasure (anonymisation)
# ──────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/forget/{agent_id}",
    dependencies=[Depends(require_roles(ROLE_ADMIN))],
    status_code=status.HTTP_200_OK,
)
async def forget_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Anonymise all personal data for an agent (GDPR Article 17 — Right to Erasure).

    This is a SOFT erase that preserves audit chain integrity:
      - Agent record: name, description, and PII fields are anonymised
      - Trust events: reason text is cleared
      - Decisions: input_context and reasoning_trace are cleared
      - Social contracts: mentor_assignments and signed_by are cleared
      - Query cache entries attributed to this agent are cleared
      - The agent record status is set to 'anonymised'

    The decision hash chain is NOT broken — hashes remain intact so that
    ledger integrity can still be verified. Only payload fields are cleared.

    Required role: admin.
    """
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status == "anonymised":
        raise HTTPException(status_code=400, detail="Agent data has already been anonymised")

    anon_code = f"ANON-{uuid.uuid4.hex[:8].upper}"
    actions_taken: list[str] = []

    # ── Anonymise agent record ──
    agent.display_name = anon_code
    agent.description = "GDPR anonymised"
    agent.social_contract = {}
    agent.dna_profile = {}
    agent.status = "anonymised"
    actions_taken.append("agent_profile_anonymised")

    # ── Clear trust event reasons ──
    await db.execute(
        update(TrustEvent)
        .where(TrustEvent.agent_id == agent_id)
        .values(reason="[GDPR ERASED]", authority_change=None)
    )
    actions_taken.append("trust_event_reasons_cleared")

    # ── Clear decision payload (preserve hashes for chain integrity) ──
    await db.execute(
        update(Decision)
        .where(Decision.agent_id == agent_id)
        .values(
            input_context={},
            reasoning_trace=None,
            crewai_task_output=None,
            tools_used=[],
            delegation_chain=[],
            output_action={"anonymised": True},
            sentinel_assessment={"anonymised": True},
            prophecy_paths=None,
        )
    )
    actions_taken.append("decision_payloads_cleared")

    # ── Clear social contract personal data ──
    await db.execute(
        update(SocialContract)
        .where(SocialContract.agent_id == agent_id)
        .values(signed_by="[GDPR ERASED]", mentor_assignments=[])
    )
    actions_taken.append("contract_personal_data_cleared")

    # ── Clear cache entries attributed to this agent ──
    await db.execute(
        update(QueryCache)
        .where(QueryCache.created_by_agent_id == agent_id)
        .values(created_by_agent_id=None)
    )
    actions_taken.append("cache_attribution_cleared")

    # ── Write erasure audit record ──
    if AuditLog is not None:
        erasure_log = AuditLog(
            id=uuid.uuid4,
            action="gdpr_erasure",
            actor="gdpr_endpoint",
            target_resource=f"agent:{agent_id}",
            details={
                "original_agent_id": str(agent_id),
                "anonymised_as": anon_code,
                "actions_taken": actions_taken,
                "erased_at": datetime.now(UTC).isoformat,
            },
            outcome="success",
        )
        db.add(erasure_log)

    await db.flush

    logger.info(
        f"[GDPR] Agent {agent_id} anonymised as {anon_code}. "
        f"Actions: {', '.join(actions_taken)}"
    )

    return {
        "status": "erased",
        "agent_id": str(agent_id),
        "anonymised_as": anon_code,
        "actions_taken": actions_taken,
        "erased_at": datetime.now(UTC).isoformat,
        "note": (
            "Decision hash chain preserved for audit integrity. "
            "All payload content has been anonymised."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /gdpr/report  — platform-level data inventory
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/report",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_AUDITOR))],
)
async def gdpr_report(db: AsyncSession = Depends(get_db)):
    """Return a GDPR data inventory report for the entire platform.

    Useful for Data Protection Officers (DPOs) to understand what data is
    stored and at what scale.

    Required role: admin or auditor.
    """
    from sqlalchemy import func

    async def _count(model) -> int:
        result = await db.execute(select(func.count).select_from(model))
        return result.scalar_one

    agent_count = await _count(Agent)
    trust_count = await _count(TrustEvent)
    decision_count = await _count(Decision)
    esc_count = await _count(EscalationCase)
    contract_count = await _count(SocialContract)
    cache_count = await _count(QueryCache)
    audit_count = await _count(AuditLog)

    # Anonymised agents
    anon_result = await db.execute(
        select(func.count).select_from(Agent).where(Agent.status == "anonymised")
    )
    anon_count = anon_result.scalar_one

    return {
        "report_generated_at": datetime.now(UTC).isoformat,
        "platform": "AgentGovern OS",
        "gdpr_basis": "Article 30 — Records of Processing Activities",
        "data_categories": [
            {
                "category": "Agent Identity & Configuration",
                "table": "agents",
                "record_count": agent_count,
                "anonymised_count": anon_count,
                "retention_policy": "Until agent decommissioning + 7 years",
                "legal_basis": "Legitimate interest — AI governance compliance",
            },
            {
                "category": "Trust & Behavioural Events",
                "table": "trust_events",
                "record_count": trust_count,
                "retention_policy": "3 years from event date",
                "legal_basis": "Legal obligation — AI auditability",
            },
            {
                "category": "Decision Audit Ledger",
                "table": "decisions",
                "record_count": decision_count,
                "retention_policy": "7 years (financial decisions), 3 years (others)",
                "legal_basis": "Legal obligation — financial/regulatory compliance",
            },
            {
                "category": "Human Review Escalations",
                "table": "escalation_cases",
                "record_count": esc_count,
                "retention_policy": "5 years from resolution date",
                "legal_basis": "Legitimate interest — AI oversight",
            },
            {
                "category": "Social Contracts",
                "table": "social_contracts",
                "record_count": contract_count,
                "retention_policy": "Duration of contract + 3 years",
                "legal_basis": "Contract performance",
            },
            {
                "category": "Query Intelligence Cache",
                "table": "query_cache",
                "record_count": cache_count,
                "retention_policy": "3 days (auto-expiry via QICACHE TTL)",
                "legal_basis": "Legitimate interest — performance optimisation",
            },
            {
                "category": "API Access Audit Log",
                "table": "audit_log",
                "record_count": audit_count,
                "retention_policy": "1 year rolling",
                "legal_basis": "Legal obligation — security audit trail",
            },
        ],
        "total_records": (
            agent_count + trust_count + decision_count +
            esc_count + contract_count + cache_count + audit_count
        ),
        "data_subjects": agent_count,
        "erasure_requests_completed": anon_count,
    }
