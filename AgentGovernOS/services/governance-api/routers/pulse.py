"""PULSE Router — Dynamic Trust Scoring Engine.

Endpoints:
  GET    /api/v1/trust/{agent_id}                     — Get current trust score (Redis-cached)
  GET    /api/v1/trust/{agent_id}/history             — Trust event history
  GET    /api/v1/trust/{agent_id}/velocity            — Trust velocity (rolling rate of change) ← NEW
  GET    /api/v1/trust/{agent_id}/promotion-eligibility — Tier promotion check
  POST   /api/v1/trust/event                          — Record a trust event (invalidates cache)
  GET    /api/v1/trust/leaderboard                    — Fleet trust leaderboard
"""

import json
import logging
from datetime import UTC
from decimal import Decimal
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import Agent, TrustEvent
from schemas import TrustEventCreate, TrustEventResponse, TrustScoreResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trust", tags=["pulse"])

# Trust event deltas
TRUST_DELTAS: dict[str, Decimal] = {
    "decision_success_simple": Decimal("0.01"),
    "decision_success_complex": Decimal("0.03"),
    "decision_success_boundary": Decimal("0.05"),
    "correct_escalation": Decimal("0.02"),
    "learning_milestone": Decimal("0.02"),
    "zero_incident_streak_7d": Decimal("0.03"),
    "zero_incident_streak_30d": Decimal("0.05"),
    "decision_failure_minor": Decimal("-0.05"),
    "decision_failure_major": Decimal("-0.15"),
    "human_override": Decimal("-0.03"),
    "policy_violation_low": Decimal("-0.05"),
    "policy_violation_high": Decimal("-0.10"),
    "policy_violation_critical": Decimal("-0.20"),
    "unnecessary_escalation": Decimal("-0.01"),
    "time_decay_daily": Decimal("-0.001"),
}

# Tier thresholds: tier → (min_score, max_score, authority_limit)
TIER_THRESHOLDS: dict[str, tuple[Decimal, Decimal, Decimal]] = {
    "T4": (Decimal("0.00"), Decimal("0.60"), Decimal("0.00")),
    "T3": (Decimal("0.60"), Decimal("0.75"), Decimal("10000.00")),
    "T2": (Decimal("0.75"), Decimal("0.90"), Decimal("50000.00")),
    "T1": (Decimal("0.90"), Decimal("1.00"), Decimal("100000.00")),
}

# Tier progression order (lowest → highest)
TIER_ORDER = ["T4", "T3", "T2", "T1"]

# Redis TTL for cached trust scores (seconds)
_TRUST_CACHE_TTL = 60


def _compute_tier(score: Decimal) -> tuple[str, Decimal]:
    """Determine tier and authority limit from trust score."""
    for tier, (low, high, limit) in TIER_THRESHOLDS.items:
        if low <= score < high:
            return tier, limit
    return "T1", Decimal("100000.00")


def _get_redis():
    """Lazy-import Redis to avoid breaking tests that don't have Redis running."""
    try:
        import redis
        from config import get_settings
        settings = get_settings()
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
        client.ping
        return client
    except Exception:
        return None


def _cache_key(agent_id: UUID) -> str:
    return f"trust:score:{agent_id}"


# ──────────────────────────────────────────────────────────────────────────────
# GET /trust/{agent_id}  — Redis-cached (60s TTL)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}", response_model=TrustScoreResponse)
async def get_trust_score(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get current trust score with tier and velocity.

    Checks Redis first (60s TTL). Falls back to PostgreSQL on cache miss.
    """
    # ── Try Redis cache ──
    redis = _get_redis
    cache_key = _cache_key(agent_id)
    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                logger.debug(f"[PULSE] Redis cache HIT for agent {agent_id}")
                return TrustScoreResponse(**{
                    **data,
                    "agent_id": UUID(data["agent_id"]),
                    "current_score": Decimal(str(data["current_score"])),
                    "authority_limit": Decimal(str(data["authority_limit"])),
                })
        except Exception as e:
            logger.warning(f"[PULSE] Redis cache read failed: {e}")

    # ── Cache miss — hit DB ──
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    velocity = await _calculate_velocity(db, agent_id, days=7)
    trend = "rising" if velocity > 0.001 else "falling" if velocity < -0.001 else "stable"

    response = TrustScoreResponse(
        agent_id=agent.id,
        agent_code=agent.agent_code,
        current_score=agent.trust_score,
        tier=agent.tier,
        authority_limit=agent.authority_limit,
        velocity_7d=velocity,
        trend=trend,
    )

    # ── Populate Redis cache ──
    if redis:
        try:
            payload = {
                "agent_id": str(agent.id),
                "agent_code": agent.agent_code,
                "current_score": str(agent.trust_score),
                "tier": agent.tier,
                "authority_limit": str(agent.authority_limit),
                "velocity_7d": velocity,
                "trend": trend,
            }
            redis.setex(cache_key, _TRUST_CACHE_TTL, json.dumps(payload))
            logger.debug(f"[PULSE] Redis cache SET for agent {agent_id} (TTL={_TRUST_CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"[PULSE] Redis cache write failed: {e}")

    return response


# ──────────────────────────────────────────────────────────────────────────────
# POST /trust/event  — Record event + invalidate Redis cache
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/event", response_model=TrustEventResponse)
async def record_trust_event(event_in: TrustEventCreate, db: AsyncSession = Depends(get_db)):
    """Record a trust event and update the agent's score.

    Invalidates the Redis trust score cache for the affected agent.
    """
    agent = await db.get(Agent, event_in.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    delta = TRUST_DELTAS.get(event_in.event_type, Decimal("0.00"))
    previous_score = agent.trust_score
    new_score = max(Decimal("0.00"), min(Decimal("1.00"), previous_score + delta))

    # Check tier change
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
            f"[PULSE] Tier change for {agent.agent_code}: {old_tier} → {new_tier} "
            f"(score {previous_score} → {new_score})"
        )

    # Update agent
    agent.trust_score = new_score
    agent.tier = new_tier
    agent.authority_limit = new_limit

    # Create trust event
    event = TrustEvent(
        agent_id=event_in.agent_id,
        event_type=event_in.event_type,
        trigger_decision_id=event_in.trigger_decision_id,
        delta=delta,
        previous_score=previous_score,
        new_score=new_score,
        authority_change=authority_change,
        reason=event_in.reason,
    )
    db.add(event)
    await db.flush
    await db.refresh(event)

    # ── Invalidate Redis cache ──
    redis = _get_redis
    if redis:
        try:
            redis.delete(_cache_key(event_in.agent_id))
            logger.debug(f"[PULSE] Redis cache invalidated for agent {event_in.agent_id}")
        except Exception as e:
            logger.warning(f"[PULSE] Redis cache invalidation failed: {e}")

    return event


# ──────────────────────────────────────────────────────────────────────────────
# GET /trust/{agent_id}/history
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/history", response_model=list[TrustEventResponse])
async def get_trust_history(
    agent_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """Get trust event history for an agent."""
    result = await db.execute(
        select(TrustEvent)
        .where(TrustEvent.agent_id == agent_id)
        .order_by(desc(TrustEvent.timestamp))
        .limit(limit)
    )
    return result.scalars.all


# ──────────────────────────────────────────────────────────────────────────────
# NEW: GET /trust/{agent_id}/velocity — rolling trust velocity metrics
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/velocity")
async def get_trust_velocity(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get trust velocity (rate of change) across multiple rolling windows.

    Returns per-day trust gain/loss over 7d, 14d, and 30d windows with
    acceleration (change-in-velocity), projected score in 30 days, and
    consecutive positive/negative event streaks.
    """
    from datetime import datetime, timedelta

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    now = datetime.now(UTC)

    async def _velocity_for_window(days: int) -> float:
        cutoff = now - timedelta(days=days)
        result = await db.execute(
            select(func.sum(TrustEvent.delta))
            .where(TrustEvent.agent_id == agent_id)
            .where(TrustEvent.timestamp >= cutoff)
        )
        total = result.scalar or Decimal("0.00")
        return round(float(total) / days, 6)

    async def _event_count_for_window(days: int) -> int:
        cutoff = now - timedelta(days=days)
        result = await db.execute(
            select(func.count)
            .select_from(TrustEvent)
            .where(TrustEvent.agent_id == agent_id)
            .where(TrustEvent.timestamp >= cutoff)
        )
        return result.scalar or 0

    v7 = await _velocity_for_window(7)
    v14 = await _velocity_for_window(14)
    v30 = await _velocity_for_window(30)
    events_7d = await _event_count_for_window(7)

    # Acceleration = difference between short and medium window velocity
    acceleration = round(v7 - v14, 6)

    # Projected score in 30 days based on current 7d velocity
    current = float(agent.trust_score)
    projected_30d = round(min(1.0, max(0.0, current + v7 * 30)), 4)

    # Determine tier at projected score
    def _tier_for_score(s: float) -> str:
        for tier, (low, high, _) in TIER_THRESHOLDS.items:
            if float(low) <= s < float(high):
                return tier
        return "T1"

    projected_tier = _tier_for_score(projected_30d)

    # Streak: count consecutive positive / negative events from most recent
    recent_events_result = await db.execute(
        select(TrustEvent.delta)
        .where(TrustEvent.agent_id == agent_id)
        .order_by(desc(TrustEvent.timestamp))
        .limit(50)
    )
    deltas = [float(d) for d in recent_events_result.scalars.all]
    positive_streak = negative_streak = 0
    if deltas:
        first_sign = deltas[0] >= 0
        for d in deltas:
            if (d >= 0) == first_sign:
                if first_sign:
                    positive_streak += 1
                else:
                    negative_streak += 1
            else:
                break

    trend = "rising" if v7 > 0.001 else "falling" if v7 < -0.001 else "stable"

    return {
        "agent_code": agent.agent_code,
        "current_score": float(agent.trust_score),
        "current_tier": agent.tier,
        "velocity_7d": v7,
        "velocity_14d": v14,
        "velocity_30d": v30,
        "acceleration": acceleration,
        "trend": trend,
        "events_last_7d": events_7d,
        "positive_streak": positive_streak,
        "negative_streak": negative_streak,
        "projected_score_30d": projected_30d,
        "projected_tier_30d": projected_tier,
        "projection_note": (
            f"At current 7d velocity of {v7:+.5f}/day, "
            f"{agent.agent_code} will reach {projected_30d:.4f} in 30 days "
            f"(projected tier: {projected_tier})."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# NEW: GET /trust/{agent_id}/promotion-eligibility
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/promotion-eligibility")
async def get_promotion_eligibility(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Check if an agent is eligible for a tier promotion.

    Returns:
    - **eligible**: whether the agent meets the score threshold for the next tier
    - **current_tier** / **next_tier**: the tiers involved
    - **current_score**: the agent's current trust score
    - **threshold**: the minimum score required for the next tier
    - **gap**: how many trust points are still needed (0 if eligible)
    - **authority_increase**: the authority limit change on promotion
    - **recommendation**: human-readable summary
    """
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    current_tier = agent.tier
    current_score = float(agent.trust_score)

    # Find position in tier order
    try:
        tier_index = TIER_ORDER.index(current_tier)
    except ValueError:
        tier_index = 0

    # Already at highest tier
    if tier_index >= len(TIER_ORDER) - 1:
        return {
            "agent_code": agent.agent_code,
            "eligible": False,
            "current_tier": current_tier,
            "next_tier": None,
            "current_score": current_score,
            "threshold": None,
            "gap": 0.0,
            "current_authority_limit": float(agent.authority_limit),
            "next_authority_limit": None,
            "authority_increase": 0.0,
            "recommendation": f"{agent.agent_code} is already at the highest tier (T1). No further promotion possible.",
        }

    next_tier = TIER_ORDER[tier_index + 1]
    _, next_threshold, next_limit = TIER_THRESHOLDS[next_tier]
    threshold = float(next_threshold)
    gap = max(0.0, round(threshold - current_score, 4))
    eligible = gap == 0.0

    # Additional eligibility checks
    eligibility_notes = []
    if agent.status != "active":
        eligible = False
        eligibility_notes.append(f"Agent status is '{agent.status}' — must be 'active' for promotion")
    if agent.total_decisions < 10:
        eligible = False
        eligibility_notes.append(f"Insufficient decision history ({agent.total_decisions}/10 minimum)")

    if eligible:
        recommendation = (
            f"{agent.agent_code} is eligible for promotion from {current_tier} → {next_tier}. "
            f"Authority limit will increase from ₹{float(agent.authority_limit):,.0f} to ₹{float(next_limit):,.0f}."
        )
    elif gap > 0:
        recommendation = (
            f"{agent.agent_code} needs {gap:.4f} more trust points to reach {next_tier} "
            f"(current: {current_score:.4f}, threshold: {threshold:.4f})."
        )
    else:
        recommendation = f"Promotion blocked: {'; '.join(eligibility_notes)}"

    return {
        "agent_code": agent.agent_code,
        "eligible": eligible,
        "current_tier": current_tier,
        "next_tier": next_tier,
        "current_score": current_score,
        "threshold": threshold,
        "gap": gap,
        "current_authority_limit": float(agent.authority_limit),
        "next_authority_limit": float(next_limit),
        "authority_increase": float(next_limit) - float(agent.authority_limit),
        "eligibility_notes": eligibility_notes,
        "recommendation": recommendation,
        "total_decisions": agent.total_decisions,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /trust/leaderboard
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/leaderboard")
async def trust_leaderboard(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Fleet trust leaderboard — top agents by trust score."""
    result = await db.execute(
        select(Agent)
        .where(Agent.status == "active")
        .order_by(desc(Agent.trust_score))
        .limit(limit)
    )
    agents = result.scalars.all
    return [
        {
            "rank": i + 1,
            "agent_code": a.agent_code,
            "display_name": a.display_name,
            "trust_score": float(a.trust_score),
            "tier": a.tier,
            "total_decisions": a.total_decisions,
        }
        for i, a in enumerate(agents)
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Internal helper
# ──────────────────────────────────────────────────────────────────────────────

async def _calculate_velocity(db: AsyncSession, agent_id: UUID, days: int = 7) -> float:
    """Calculate trust velocity over a rolling window."""
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(func.sum(TrustEvent.delta))
        .where(TrustEvent.agent_id == agent_id)
        .where(TrustEvent.timestamp >= cutoff)
    )
    total_delta = result.scalar or Decimal("0.00")
    return float(total_delta) / days
