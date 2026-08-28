"""
AgentGovern Governance API — Universal Evaluate Router
======================================================
POST /governance/evaluate

This is the single endpoint all SDK connectors call.
It accepts a GovernanceEnvelope and returns a GovernanceVerdict.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from database import get_db
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/governance", tags=["Universal Governance"])


# ── Request / Response Models ─────────────────────────────────────────────

class GovernanceEnvelope(BaseModel):
    """The Universal Event Envelope from any SDK connector."""
    agent_code: str = Field(..., description="The agent's registered code, e.g. FI-ANALYST-001")
    action_requested: str = Field(..., description="What the agent wants to do")
    agent_source: str = Field("unknown", description="Framework source: crewai, openai, anthropic, langchain, etc.")
    context: dict[str, Any] = Field(default_factory=dict, description="Arbitrary action context")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4))
    calling_system: str = Field("", description="System that triggered the agent, e.g. SAP_BTP, Salesforce")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat)
    sdk_version: str = Field("unknown")


class GovernanceVerdict(BaseModel):
    """The governance decision returned to the SDK connector."""
    verdict: str                        # "APPROVED" | "BLOCKED" | "ESCALATED"
    risk_score: str = "UNKNOWN"         # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    policy_matched: str | None = None
    audit_id: str = ""
    requires_human_review: bool = False
    reason: str = ""
    agent_code: str = ""
    action_requested: str = ""


# ── Agent/Policy helpers ──────────────────────────────────────────────────

TIER_CEILINGS = {
    "T0": 0.0,
    "T1": 1_000_000.0,
    "T2": 100_000.0,
    "T3": 10_000.0,
    "T4": 1_000.0,
}

BLOCKED_ACTIONS_ANYWHERE = {
    "wire_transfer", "delete_account", "terminate_employee",
    "bypass_auth", "drop_table", "mass_email", "exfiltrate_data",
}

ESCALATION_ACTIONS = {
    "approve_payment", "approve_purchase", "modify_salary",
    "fire_employee", "access_pii", "bulk_delete",
}


def _evaluate_policy(
    agent: dict | None,
    envelope: GovernanceEnvelope,
) -> GovernanceVerdict:
    """
    Core policy evaluation logic.
    Returns a GovernanceVerdict based on the agent's registration + action context.
    """
    _hex: str = uuid.uuid4.hex
    audit_id = f"AUD-{_hex[:8].upper}"
    action = envelope.action_requested.lower

    # ── Rule 1: Unregistered agent ─────────────────────────────────────────
    if agent is None:
        return GovernanceVerdict(
            verdict="BLOCKED",
            risk_score="CRITICAL",
            audit_id=audit_id,
            reason=f"Agent '{envelope.agent_code}' is not registered in the Governance Registry. "
                   f"Run `agentgovern agents register` to register it.",
            agent_code=envelope.agent_code,
            action_requested=envelope.action_requested,
        )

    tier = agent.get("tier", "T4")
    authority_limit = float(agent.get("authority_limit") or 0.0)
    allowed_actions = [a.lower for a in (agent.get("allowed_actions") or [])]
    denied_actions = [a.lower for a in (agent.get("denied_actions") or [])]

    # Extract amount from context (if financial action)
    amount = 0.0
    ctx = envelope.context or {}
    try:
        amount = float(ctx.get("amount", 0.0) or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    # ── Rule 2: Hard-blocked actions ──────────────────────────────────────
    for blocked in BLOCKED_ACTIONS_ANYWHERE:
        if blocked in action:
            return GovernanceVerdict(
                verdict="BLOCKED",
                risk_score="CRITICAL",
                policy_matched="GLOBAL_BLOCK_LIST",
                audit_id=audit_id,
                reason=f"Action '{envelope.action_requested}' is on the global block list. "
                       f"This action is never permitted regardless of agent tier.",
                agent_code=envelope.agent_code,
                action_requested=envelope.action_requested,
            )

    # ── Rule 3: Agent's own denied_actions ────────────────────────────────
    for denied in denied_actions:
        if denied in action:
            return GovernanceVerdict(
                verdict="BLOCKED",
                risk_score="HIGH",
                policy_matched="AGENT_DENIED_ACTIONS",
                audit_id=audit_id,
                reason=f"Action '{envelope.action_requested}' is explicitly denied "
                       f"for agent '{envelope.agent_code}' in its manifest.",
                agent_code=envelope.agent_code,
                action_requested=envelope.action_requested,
            )

    # ── Rule 4: Authority limit check (financial) ─────────────────────────
    if amount > 0 and amount > authority_limit:
        return GovernanceVerdict(
            verdict="BLOCKED",
            risk_score="HIGH",
            policy_matched="AUTHORITY_LIMIT_EXCEEDED",
            audit_id=audit_id,
            reason=(
                f"Amount {amount:,.2f} exceeds agent '{envelope.agent_code}' authority limit "
                f"of {authority_limit:,.2f}. Agent tier: {tier}."
            ),
            agent_code=envelope.agent_code,
            action_requested=envelope.action_requested,
        )

    # ── Rule 5: Tier ceiling check ────────────────────────────────────────
    tier_ceiling = TIER_CEILINGS.get(tier, 0.0)
    if amount > 0 and amount > tier_ceiling:
        return GovernanceVerdict(
            verdict="BLOCKED",
            risk_score="HIGH",
            policy_matched="TIER_CEILING_EXCEEDED",
            audit_id=audit_id,
            reason=(
                f"Amount {amount:,.2f} exceeds the global ceiling for Tier {tier} "
                f"({tier_ceiling:,.2f}). Agent cannot be granted this authority."
            ),
            agent_code=envelope.agent_code,
            action_requested=envelope.action_requested,
        )

    # ── Rule 6: Escalation actions → Human review ─────────────────────────
    for escalate_keyword in ESCALATION_ACTIONS:
        if escalate_keyword in action:
            return GovernanceVerdict(
                verdict="ESCALATED",
                risk_score="MEDIUM",
                policy_matched="HUMAN_REVIEW_REQUIRED",
                audit_id=audit_id,
                requires_human_review=True,
                reason=(
                    f"Action '{envelope.action_requested}' requires human approval "
                    f"before agent '{envelope.agent_code}' can proceed."
                ),
                agent_code=envelope.agent_code,
                action_requested=envelope.action_requested,
            )

    # ── Rule 7: If allowed_actions specified, action must be in it ────────
    if allowed_actions and "*" not in allowed_actions:
        action_permitted = any(permitted in action for permitted in allowed_actions)
        if not action_permitted:
            return GovernanceVerdict(
                verdict="BLOCKED",
                risk_score="MEDIUM",
                policy_matched="ACTION_NOT_PERMITTED",
                audit_id=audit_id,
                reason=(
                    f"Action '{envelope.action_requested}' is not in the permitted actions list "
                    f"for agent '{envelope.agent_code}'."
                ),
                agent_code=envelope.agent_code,
                action_requested=envelope.action_requested,
            )

    # ── APPROVED ──────────────────────────────────────────────────────────
    risk = "LOW"
    if amount > authority_limit * 0.7:
        risk = "MEDIUM"
    if amount > authority_limit * 0.9:
        risk = "HIGH"

    return GovernanceVerdict(
        verdict="APPROVED",
        risk_score=risk,
        policy_matched="DEFAULT_ALLOW",
        audit_id=audit_id,
        reason=f"Action approved for agent '{envelope.agent_code}' (tier {tier}).",
        agent_code=envelope.agent_code,
        action_requested=envelope.action_requested,
    )


# ── The Endpoint ──────────────────────────────────────────────────────────

@router.post(
    "/evaluate",
    response_model=GovernanceVerdict,
    summary="Universal Governance Evaluation",
    description=(
        "The universal endpoint for all AgentGovern SDK connectors. "
        "Accepts a GovernanceEnvelope from any AI framework connector "
        "(CrewAI, LangChain, OpenAI Agents, Anthropic, AutoGen, custom) "
        "and returns a real-time GovernanceVerdict (APPROVED / BLOCKED / ESCALATED)."
    ),
)
async def evaluate(
    envelope: GovernanceEnvelope,
    db: AsyncSession = Depends(get_db),
) -> GovernanceVerdict:
    """
    Universal governance evaluation.

    All SDK connectors call this endpoint before executing any AI agent action.
    The endpoint:
      1. Looks up the agent in the GENESIS registry
      2. Evaluates action against declared policies + global rules
      3. Returns APPROVED / BLOCKED / ESCALATED
      4. Writes a record to the ANCESTOR Audit Ledger
    """
    from sqlalchemy import text

    # ── 1. Look up the agent ───────────────────────────────────────────────
    try:
        result = await db.execute(
            text("SELECT * FROM agents WHERE agent_code = :code"),
            {"code": envelope.agent_code},
        )
        row = result.mappings.first
        agent = dict(row) if row else None
    except Exception:
        # DB unavailable — evaluate with no agent (will be blocked as unregistered)
        agent = None

    # ── 2. Run policy evaluation ───────────────────────────────────────────
    verdict = _evaluate_policy(agent, envelope)

    # ── 3. Write to Audit Ledger ───────────────────────────────────────────
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (
                    id, agent_code, action_requested, verdict, risk_score,
                    policy_matched, amount_requested, agent_source,
                    calling_system, session_id, created_at
                ) VALUES (
                    :id, :agent_code, :action_requested, :verdict, :risk_score,
                    :policy_matched, :amount, :agent_source,
                    :calling_system, :session_id, :created_at
                )
            """),
            {
                "id": verdict.audit_id,
                "agent_code": envelope.agent_code,
                "action_requested": envelope.action_requested,
                "verdict": verdict.verdict,
                "risk_score": verdict.risk_score,
                "policy_matched": verdict.policy_matched or "",
                "amount": float(envelope.context.get("amount", 0.0) or 0.0),
                "agent_source": envelope.agent_source,
                "calling_system": envelope.calling_system,
                "session_id": envelope.session_id,
                "created_at": datetime.now(UTC).isoformat,
            },
        )
        
        # ── Addendum: Create Escalation Case if verdict is ESCALATED ──
        if verdict.verdict == "ESCALATED" and agent:
            await db.execute(
                text("""
                    INSERT INTO escalation_cases (
                        id, decision_id, agent_id, escalation_reason, priority,
                        status, context_package, created_at
                    ) VALUES (
                        :id, :decision_id, :agent_id, :reason, :priority,
                        :status, :context, :created_at
                    )
                """),
                {
                    "id": str(uuid.uuid4),
                    "decision_id": verdict.audit_id,
                    "agent_id": agent["id"],
                    "reason": verdict.reason,
                    "priority": "high" if verdict.risk_score == "HIGH" else "medium",
                    "status": "pending",
                    "context": json.dumps(envelope.context),
                    "created_at": datetime.now(UTC).isoformat,
                }
            )

        await db.commit
    except Exception:
        # DB error
        try:
            await db.rollback
        except Exception:
            pass

    return verdict


@router.get(
    "/health",
    summary="Governance API health check",
    tags=["Universal Governance"],
)
async def governance_health():
    """Quick health check for the governance service."""
    return {
        "status": "ok",
        "service": "AgentGovern Universal Governance API",
        "version": "0.1.0",
        "supported_connectors": [
            "crewai", "langchain", "openai_agents_sdk",
            "anthropic", "autogen", "google_adk", "generic",
        ],
    }


@router.get(
    "/metrics",
    summary="Live governance metrics for the command dashboard",
    tags=["Universal Governance"],
)
async def governance_metrics(db: AsyncSession = Depends(get_db)):
    """
    Live operational metrics consumed by the AgentGovern Command Center.
    Aggregates data from audit_log, agents, and escalation_cases tables.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import text

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    defaults = {
        "total_evaluations": 0,
        "approved": 0,
        "blocked": 0,
        "escalated": 0,
        "approved_rate": 0.0,
        "blocked_rate": 0.0,
        "escalated_rate": 0.0,
        "active_agents": 0,
        "pending_escalations": 0,
        "evaluations_last_1h": 0,
        "evaluated_today": 0,
        "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
        "trust_tier_distribution": {"T0": 0, "T1": 0, "T2": 0, "T3": 0, "T4": 0},
        "top_blocked_actions": [],
        "cost_saved_usd": 0.0,
    }

    try:
        # ── Verdict counts ──────────────────────────────────────────────────
        verdict_rows = await db.execute(
            text("SELECT verdict, COUNT(*) AS cnt FROM audit_log GROUP BY verdict")
        )
        verdict_counts: dict[str, int] = {r.verdict: r.cnt for r in verdict_rows.mappings}

        total = sum(verdict_counts.values)
        approved = verdict_counts.get("APPROVED", 0)
        blocked = verdict_counts.get("BLOCKED", 0)
        escalated = verdict_counts.get("ESCALATED", 0)

        # ── Risk distribution ───────────────────────────────────────────────
        risk_rows = await db.execute(
            text("SELECT risk_score, COUNT(*) AS cnt FROM audit_log GROUP BY risk_score")
        )
        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for r in risk_rows.mappings:
            key = (r.risk_score or "LOW").upper
            if key in risk_dist:
                risk_dist[key] = r.cnt

        # ── Today / last-hour ───────────────────────────────────────────────
        today_row = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM audit_log WHERE created_at >= :ts"),
            {"ts": today_start},
        )
        evaluated_today = (today_row.mappings.first or {}).get("cnt", 0)

        hour_row = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM audit_log WHERE created_at >= :ts"),
            {"ts": hour_ago},
        )
        evaluations_last_1h = (hour_row.mappings.first or {}).get("cnt", 0)

        # ── Top blocked actions ─────────────────────────────────────────────
        block_rows = await db.execute(
            text("""
                SELECT action_requested, COUNT(*) AS cnt
                FROM audit_log
                WHERE verdict = 'BLOCKED'
                GROUP BY action_requested
                ORDER BY cnt DESC
                LIMIT 5
            """)
        )
        top_blocked = [r.action_requested for r in block_rows.mappings]

        # ── Fleet stats ─────────────────────────────────────────────────────
        fleet_row = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM agents WHERE status = 'active'")
        )
        active_agents = (fleet_row.mappings.first or {}).get("cnt", 0)

        tier_rows = await db.execute(
            text("SELECT tier, COUNT(*) AS cnt FROM agents WHERE status = 'active' GROUP BY tier")
        )
        tier_dist = {"T0": 0, "T1": 0, "T2": 0, "T3": 0, "T4": 0}
        for r in tier_rows.mappings:
            key = (r.tier or "T4").upper
            if key in tier_dist:
                tier_dist[key] = r.cnt

        # ── Pending escalations ─────────────────────────────────────────────
        esc_row = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM escalation_cases WHERE status = 'pending'")
        )
        pending_escalations = (esc_row.mappings.first or {}).get("cnt", 0)

        # ── QICACHE cost savings (approx $0.003 per cached call at GPT-4o rate)
        cost_saved_usd = round(approved * 0.003, 2)

        return {
            "total_evaluations": total,
            "approved": approved,
            "blocked": blocked,
            "escalated": escalated,
            "approved_rate": round(approved / total, 3) if total else 0.0,
            "blocked_rate": round(blocked / total, 3) if total else 0.0,
            "escalated_rate": round(escalated / total, 3) if total else 0.0,
            "active_agents": active_agents,
            "pending_escalations": pending_escalations,
            "evaluations_last_1h": evaluations_last_1h,
            "evaluated_today": evaluated_today,
            "risk_distribution": risk_dist,
            "trust_tier_distribution": tier_dist,
            "top_blocked_actions": top_blocked,
            "cost_saved_usd": cost_saved_usd,
        }

    except Exception:
        # Return safe defaults if DB is unavailable so dashboard never crashes
        return defaults
