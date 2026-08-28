"""
ECLIPSE Router — Human-in-the-loop (HITL) Approval Workbench.

Endpoints:
  POST   /api/v1/escalations/              — Create a new escalation case (manual or auto-triggered)
  GET    /api/v1/escalations/              — List escalations (filter by status)
  GET    /api/v1/escalations/{id}          — Get escalation details
  POST   /api/v1/escalations/{id}/resolve  — Human approval or rejection + trust feedback loop
"""

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent, EscalationCase, TrustEvent
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/escalations", tags=["eclipse"])


# ── Trust deltas for resolution outcomes ──────────────────────────────────────
_TRUST_DELTAS = {
    "correct_escalation": Decimal("0.02"),   # Human approved — escalation was justified
    "human_override": Decimal("-0.03"),       # Human rejected — agent acted incorrectly
    "unnecessary_escalation": Decimal("-0.01"),  # Human approved but marked as unnecessary
}

_TIER_THRESHOLDS: dict[str, tuple[Decimal, Decimal, Decimal]] = {
    "T4": (Decimal("0.00"), Decimal("0.60"), Decimal("0.00")),
    "T3": (Decimal("0.60"), Decimal("0.75"), Decimal("10000.00")),
    "T2": (Decimal("0.75"), Decimal("0.90"), Decimal("50000.00")),
    "T1": (Decimal("0.90"), Decimal("1.00"), Decimal("100000.00")),
}


def _compute_tier(score: Decimal) -> tuple[str, Decimal]:
    for tier, (lo, hi, limit) in _TIER_THRESHOLDS.items:
        if lo <= score < hi:
            return tier, limit
    return "T1", Decimal("100000.00")


# ── Schemas ───────────────────────────────────────────────────────────────────

class EscalationCreate(BaseModel):
    """Body for manually creating or auto-triggering an escalation case."""
    agent_id: UUID
    decision_id: str = Field(
        default_factory=lambda: f"AUD-{uuid.uuid4.hex[:8].upper}",
        description="Audit / Decision ID that triggered this escalation",
    )
    escalation_reason: str = Field(
        ...,
        max_length=50,
        description="Short reason code: AUTHORITY_EXCEEDED | POLICY_VIOLATION | RISK_THRESHOLD | MANUAL",
        examples=["AUTHORITY_EXCEEDED"],
    )
    priority: str = Field(default="medium", description="high | medium | low")
    context_package: dict = Field(
        default_factory=dict,
        description="Full action context — action, amount, policy results, agent state, etc.",
    )
    prophecy_recommendation: dict | None = Field(
        default=None,
        description="Optional Prophecy Engine paths attached to this escalation",
    )


class EscalationResolve(BaseModel):
    verdict: str = Field(..., description="APPROVED | REJECTED | UNNECESSARY")
    human_reason: str = Field(..., description="Admin's reasoning memo")
    assigned_to: str = Field(default="Admin")
    apply_trust_feedback: bool = Field(
        default=True,
        description="Whether to update the agent's trust score based on the resolution verdict",
    )


class EscalationResponse(BaseModel):
    id: UUID
    agent_id: UUID
    decision_id: UUID | str
    escalation_reason: str
    priority: str
    status: str
    context_package: dict
    prophecy_recommendation: dict | None = None
    created_at: datetime
    resolved_at: datetime | None
    human_decision: dict | None
    agent_code: str | None = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# POST /escalations/  — create a new escalation (manual or from Sentinel)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=EscalationResponse, status_code=status.HTTP_201_CREATED)
async def create_escalation(body: EscalationCreate, db: AsyncSession = Depends(get_db)):
    """Create a new escalation case.

    Called automatically by the Sentinel policy engine when a verdict is
    ESCALATED, or manually by admins who want to flag an action for review.

    The case is created with status='pending' and placed in the ECLIPSE queue.
    """
    agent = await db.get(Agent, body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Normalise priority
    priority = body.priority.lower
    if priority not in ("high", "medium", "low"):
        priority = "medium"

    case = EscalationCase(
        agent_id=body.agent_id,
        decision_id=body.decision_id if isinstance(body.decision_id, UUID)
                    else uuid.UUID(str(body.decision_id)) if _is_valid_uuid(str(body.decision_id))
                    else uuid.uuid4,
        escalation_reason=body.escalation_reason,
        priority=priority,
        status="pending",
        context_package=body.context_package,
        prophecy_recommendation=body.prophecy_recommendation,
    )
    db.add(case)

    # Bump agent escalation counter
    agent.total_escalations += 1

    await db.flush
    await db.refresh(case)

    logger.info(
        f"[ECLIPSE] Escalation created: id={str(case.id)[:8]} "
        f"agent={agent.agent_code} reason={body.escalation_reason} priority={priority}"
    )

    resp = EscalationResponse.model_validate(case)
    resp.agent_code = agent.agent_code
    return resp


# ──────────────────────────────────────────────────────────────────────────────
# GET /escalations/  — list
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[EscalationResponse])
async def list_escalations(
    status: str = "pending",
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List agent actions waiting for human approval."""
    query = (
        select(EscalationCase, Agent.agent_code)
        .join(Agent, EscalationCase.agent_id == Agent.id)
        .where(EscalationCase.status == status)
        .order_by(desc(EscalationCase.created_at))
        .limit(limit)
    )
    result = await db.execute(query)

    cases = []
    for row in result.all:
        case_obj, agent_code = row[0], row[1]
        data = EscalationResponse.model_validate(case_obj)
        data.agent_code = agent_code
        cases.append(data)
    return cases


# ──────────────────────────────────────────────────────────────────────────────
# GET /escalations/{case_id}  — single case detail
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{case_id}", response_model=EscalationResponse)
async def get_escalation(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full details for a specific escalation case."""
    case = await db.get(EscalationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Escalation case not found")

    agent = await db.get(Agent, case.agent_id)
    resp = EscalationResponse.model_validate(case)
    resp.agent_code = agent.agent_code if agent else "unknown"
    return resp


# ──────────────────────────────────────────────────────────────────────────────
# POST /escalations/{case_id}/resolve  — human decision + trust feedback loop
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    case_id: UUID,
    resolution: EscalationResolve,
    db: AsyncSession = Depends(get_db),
):
    """Human decision to APPROVE, REJECT, or mark UNNECESSARY an escalated action.

    Trust Feedback Loop (when apply_trust_feedback=True):
      - APPROVED    → +0.02 (correct_escalation) — agent was right to escalate
      - REJECTED    → -0.03 (human_override)     — agent should have handled it
      - UNNECESSARY → -0.01 (unnecessary_escalation) — escalation was not needed

    A tier re-evaluation is triggered if the trust score crosses a tier boundary.
    """
    case = await db.get(EscalationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Escalation case not found")

    if case.status != "pending":
        raise HTTPException(status_code=400, detail=f"Case is already '{case.status}'")

    verdict = resolution.verdict.upper
    if verdict not in ("APPROVED", "REJECTED", "UNNECESSARY"):
        raise HTTPException(
            status_code=422,
            detail="verdict must be one of: APPROVED, REJECTED, UNNECESSARY",
        )

    now = datetime.now(UTC)

    # ── 1. Update case record ──
    case.status = "resolved"
    case.resolved_at = now
    case.assigned_to = resolution.assigned_to
    case.human_decision = {
        "verdict": verdict,
        "reason": resolution.human_reason,
        "resolved_by": resolution.assigned_to,
        "timestamp": now.isoformat,
        "trust_feedback_applied": resolution.apply_trust_feedback,
    }

    agent = await db.get(Agent, case.agent_id)

    if agent:
        agent.last_review_date = now

        # ── 2. Trust Feedback Loop ──
        if resolution.apply_trust_feedback:
            if verdict == "APPROVED":
                event_type = "correct_escalation"
            elif verdict == "REJECTED":
                event_type = "human_override"
                agent.total_overrides += 1
            else:
                event_type = "unnecessary_escalation"

            delta = _TRUST_DELTAS[event_type]
            previous_score = agent.trust_score
            new_score = max(Decimal("0.00"), min(Decimal("1.00"), previous_score + delta))

            # Tier re-evaluation
            old_tier = agent.tier
            new_tier, new_limit = _compute_tier(new_score)
            authority_change = None
            if old_tier != new_tier:
                authority_change = {
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "old_limit": float(agent.authority_limit),
                    "new_limit": float(new_limit),
                }
                logger.info(
                    f"[ECLIPSE] Trust tier change for {agent.agent_code}: "
                    f"{old_tier} → {new_tier} (score {previous_score} → {new_score})"
                )

            agent.trust_score = new_score
            agent.tier = new_tier
            agent.authority_limit = new_limit

            trust_event = TrustEvent(
                agent_id=case.agent_id,
                event_type=event_type,
                delta=delta,
                previous_score=previous_score,
                new_score=new_score,
                authority_change=authority_change,
                reason=(
                    f"ECLIPSE resolution: {verdict} by {resolution.assigned_to}. "
                    f"Case: {str(case_id)[:8]}. Reason: {resolution.human_reason}"
                ),
            )
            db.add(trust_event)

            # Invalidate Redis trust cache
            try:
                import redis as _redis
                from config import get_settings
                settings = get_settings()
                r = _redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
                r.ping
                r.delete(f"trust:score:{case.agent_id}")
                logger.debug(f"[ECLIPSE] Redis trust cache invalidated for agent {case.agent_id}")
            except Exception:
                pass

            logger.info(
                f"[ECLIPSE] Trust feedback: agent={agent.agent_code} "
                f"event={event_type} delta={delta} "
                f"{previous_score} → {new_score}"
            )
        else:
            # Still bump total_overrides stat even without trust change for REJECTED
            if verdict == "REJECTED":
                agent.total_overrides += 1

    await db.flush
    await db.refresh(case)

    resp = EscalationResponse.model_validate(case)
    resp.agent_code = agent.agent_code if agent else "unknown"
    return resp


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
