"""SENTINEL Router — Policy Engine & Pre-Execution Evaluation.

Endpoints:
  POST   /api/v1/sentinel/evaluate  — Evaluate a proposed agent action (with Prophecy)
  POST   /api/v1/sentinel/simulate  — Dry-run evaluation (no decision written) ← NEW
  GET    /api/v1/sentinel/health    — Sentinel service health ← NEW
  GET    /api/v1/policies/          — List all policies
  POST   /api/v1/policies/          — Create a new policy
  PATCH  /api/v1/policies/{id}      — Update a policy
  DELETE /api/v1/policies/{id}      — Deactivate a policy

Prophecy Engine is now wired into /sentinel/evaluate. It is triggered automatically
for boundary decisions (≥70% authority limit), low-trust agents (<0.6), or agents
with fewer than 5 total decisions.
"""

import logging
from datetime import UTC
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent, Policy
from policy.distribution import PolicyDistributionService, PolicyRule
from policy.prophecy import ProphecyEngine
from policy.compiled_sentinel import sentinel_engine, telemetry_streamer
from pydantic import BaseModel
from schemas import (
    ActionEvaluationRequest,
    PolicyCreate,
    PolicyResponse,
    SentinelVerdict,
    SentinelVerdictResponse,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.circuit_breaker import CircuitBreakerService
from services.cost_governance import CostGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["sentinel"])

_prophecy = ProphecyEngine()
_policy_distribution = PolicyDistributionService()
_circuit_breaker = CircuitBreakerService()


# ──────────────────────────────────────────────────────────────────────────────
# POST /sentinel/evaluate  — with Prophecy Engine wired in
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/sentinel/evaluate", response_model=SentinelVerdictResponse)
@router.post("/evaluate", response_model=SentinelVerdictResponse)
async def evaluate_action(
    request: ActionEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pre-execution evaluation of a proposed agent action.

    Steps:
    1. Fetch agent trust score and authority limits
    2. Evaluate action against all applicable policies
    3. Check Prophecy triggers — if boundary/unstable/new agent, run 3-path simulation
    4. Return verdict: APPROVE | BLOCK | ESCALATE + optional prophecy_paths
    """
    agent = await db.get(Agent, request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    amount = request.action.get("amount", 0)
    action_type = request.action.get("type", "unknown")
    policy_results = []
    
    # ── Step 1.5: Circuit Breaker Check ──
    if _circuit_breaker.is_open(str(agent.id)):
        return SentinelVerdictResponse(
            verdict=SentinelVerdict.block,
            reasoning="BLOCKED: Circuit Breaker Open due to too many recent failures.",
            policy_results=[],
            prophecy_paths=None,
            confidence=0.99,
        )

    # ── Step 1.6: Cost Governance Check ──
    cost_estimate = Decimal("0.00")
    # Dummy estimate for demonstration
    if action_type == "complex_search":
        cost_estimate = Decimal("0.05")
        
    cost_check = await CostGovernanceService.evaluate_budget(db, str(agent.id), cost_estimate)
    if not cost_check.get("approved"):
        return SentinelVerdictResponse(
            verdict=SentinelVerdict.block,
            reasoning=f"BLOCKED: {cost_check.get('reason')}",
            policy_results=[],
            prophecy_paths=None,
            confidence=0.99,
        )

    # ── Step 2: Evaluate active policies ──
    result = await db.execute(select(Policy).where(Policy.is_active == True))
    policies = result.scalars().all()

    violations = []
    for policy in policies:
        # Role applicability
        if "*" not in policy.applies_to_roles and agent.role not in policy.applies_to_roles:
            continue
        # Tier applicability
        if "*" not in policy.applies_to_tiers and agent.tier not in policy.applies_to_tiers:
            continue

        rule = policy.rule_definition
        passed = _evaluate_rule(rule, agent, request.action, request.context)
        policy_results.append({
            "policy_code": policy.policy_code,
            "policy_name": policy.policy_name,
            "passed": passed,
            "severity": policy.severity,
        })
        if not passed:
            violations.append({
                "policy_code": policy.policy_code,
                "severity": policy.severity,
                "action": policy.action_on_violation,
            })

    # ── Step 3: Determine base verdict ──
    if any(v["severity"] == "critical" for v in violations):
        verdict = SentinelVerdict.block
        reasoning = (
            f"BLOCKED: Critical policy violation(s) detected — "
            f"{[v['policy_code'] for v in violations if v['severity'] == 'critical']}"
        )
        confidence = 0.99
    elif amount > float(agent.authority_limit):
        verdict = SentinelVerdict.escalate
        reasoning = (
            f"ESCALATE: Amount ₹{amount:,.2f} exceeds authority limit "
            f"₹{float(agent.authority_limit):,.2f} for {agent.tier} agent"
        )
        confidence = 0.95
    elif violations:
        verdict = SentinelVerdict.escalate
        reasoning = (
            f"ESCALATE: Non-critical policy violations require human review — "
            f"{[v['policy_code'] for v in violations]}"
        )
        confidence = 0.85
    else:
        verdict = SentinelVerdict.approve
        reasoning = (
            f"APPROVED: All {len(policy_results)} policies passed. "
            f"Agent {agent.agent_code} within authority limits."
        )
        confidence = 0.92

    # ── Step 4: Prophecy Engine ──
    prophecy_paths = None
    should_run, trigger_reason = _prophecy.should_trigger(
        trust_score=float(agent.trust_score),
        amount=float(amount),
        authority_limit=float(agent.authority_limit),
        historical_action_count=agent.total_decisions,
    )

    if should_run:
        try:
            prophecy_result = _prophecy.simulate(
                agent_id=str(agent.id),
                action_type=action_type,
                amount=float(amount),
                trust_score=float(agent.trust_score),
                tier=agent.tier,
                authority_limit=float(agent.authority_limit),
                historical_success_rate=_estimate_success_rate(agent),
                trigger_reason=trigger_reason,
            )
            prophecy_paths = [p.to_dict() for p in prophecy_result.paths]

            # Let Prophecy refine the verdict if currently APPROVE but Prophecy strongly warns
            if verdict == SentinelVerdict.approve and prophecy_result.recommended_path == "escalate":
                if prophecy_result.confidence >= 0.75:
                    verdict = SentinelVerdict.escalate
                    reasoning = (
                        f"ESCALATE (Prophecy override): {reasoning}. "
                        f"Prophecy recommends escalation with {prophecy_result.confidence:.0%} confidence. "
                        f"Trigger: {trigger_reason}"
                    )
                    confidence = min(confidence, prophecy_result.confidence)

            logger.info(
                f"[SENTINEL] Prophecy ran for {agent.agent_code} — "
                f"recommended={prophecy_result.recommended_path} "
                f"conf={prophecy_result.confidence:.2f} trigger={trigger_reason}"
            )
        except Exception as e:
            # Prophecy failure must not block the governance response
            logger.error(f"[SENTINEL] Prophecy Engine error: {e}", exc_info=True)

    return SentinelVerdictResponse(
        verdict=verdict,
        reasoning=reasoning,
        policy_results=policy_results,
        prophecy_paths=prophecy_paths,
        confidence=confidence,
    )


def _estimate_success_rate(agent: Agent) -> float:
    """Estimate historical success rate from agent metrics."""
    total = agent.total_decisions
    if total == 0:
        return 0.70  # Assume moderate success for new agents
    failures = agent.total_overrides + agent.total_escalations
    success = max(0, total - failures)
    return round(success / total, 3)


def _evaluate_rule(rule: dict, agent: Agent, action: dict, context: dict) -> bool:
    """Evaluate a policy rule against current state using the compiled AOT Sentinel Bytecode Engine."""
    return sentinel_engine.evaluate_rule(rule, agent, action, context)


# ──────────────────────────────────────────────────────────────────────────────
# Policy CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/policies/", response_model=list[PolicyResponse])
async def list_policies(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    """List all policies."""
    query = select(Policy)
    if active_only:
        query = query.where(Policy.is_active == True)
    result = await db.execute(query.order_by(Policy.category, Policy.policy_code))
    return list(result.scalars().all())


@router.post("/policies/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(policy_in: PolicyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new policy."""
    existing = await db.execute(select(Policy).where(Policy.policy_code == policy_in.policy_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Policy {policy_in.policy_code} already exists")

    policy = Policy(**policy_in.model_dump())
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    return policy


# ──── NEW: PATCH /policies/{id} ────

class PolicyUpdateRequest(BaseModel):
    """Fields that can be updated on an existing policy."""
    policy_name: str | None = None
    description: str | None = None
    rule_definition: dict | None = None
    applies_to_roles: list[str] | None = None
    applies_to_tiers: list[str] | None = None
    severity: str | None = None
    action_on_violation: str | None = None
    is_active: bool | None = None


class PolicyPublishResponse(BaseModel):
    version: str
    hash: str
    rule_count: int
    published_at: str


def _policy_to_rule(policy: Policy) -> PolicyRule:
    """Convert ORM policy rows into distributable policy bundle rules."""
    environment_scope = policy.rule_definition.get("environment_scope", ["cloud", "edge", "client"])
    params = {
        k: v
        for k, v in policy.rule_definition.items()
        if k != "type"
    }
    return PolicyRule(
        id=str(policy.id),
        name=policy.policy_code,
        type=policy.rule_definition.get("type", "custom"),
        parameters=params,
        on_fail=policy.action_on_violation,
        environment_scope=environment_scope,
        active=policy.is_active,
    )


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    updates: PolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a policy.

    Accepts partial updates — only the fields provided in the request body
    are changed. Increments the policy version on every successful update.
    """
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = updates.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No update fields provided")

    allowed = {
        "policy_name", "description", "rule_definition",
        "applies_to_roles", "applies_to_tiers",
        "severity", "action_on_violation", "is_active",
    }
    for field, value in update_data.items():
        if field in allowed:
            setattr(policy, field, value)

    # Bump version on every successful update
    policy.version = (policy.version or 1) + 1

    await db.flush()
    await db.refresh(policy)
    return policy


@router.post("/policies/publish", response_model=PolicyPublishResponse)
async def publish_policies(db: AsyncSession = Depends(get_db)):
    """Create and activate a new policy bundle from all active policies."""
    result = await db.execute(select(Policy).where(Policy.is_active == True).order_by(Policy.policy_code))
    active_policies = result.scalars().all()
    if not active_policies:
        raise HTTPException(status_code=400, detail="No active policies to publish")

    rules = [_policy_to_rule(policy) for policy in active_policies]
    bundle = _policy_distribution.create_bundle(
        rules=rules,
        metadata={"source": "dashboard", "policy_count": len(active_policies)},
    )

    return PolicyPublishResponse(
        version=bundle.version,
        hash=bundle.hash,
        rule_count=len(rules),
        published_at=bundle.valid_from.isoformat(),
    )


@router.get("/sentinel/policies/bundle")
async def get_edge_policy_bundle(db: AsyncSession = Depends(get_db)):
    """Serve latest edge-scoped policy bundle for gateway sync clients."""
    current = _policy_distribution.get_current_bundle()
    if not current:
        result = await db.execute(select(Policy).where(Policy.is_active == True).order_by(Policy.policy_code))
        active_policies = result.scalars().all()
        if not active_policies:
            return {"version": "none", "hash": "", "rules": [], "environment": "edge", "total_rules": 0}

        rules = [_policy_to_rule(policy) for policy in active_policies]
        _policy_distribution.create_bundle(
            rules=rules,
            metadata={"source": "auto-init", "policy_count": len(active_policies)},
        )

    return _policy_distribution.get_bundle_for_environment("edge")


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deactivate a policy (soft delete)."""
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.is_active = False
    await db.flush()


# ──────────────────────────────────────────────────────────────────────────────
# NEW: POST /sentinel/simulate  — dry-run (no decision written)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/sentinel/simulate", response_model=SentinelVerdictResponse)
@router.post("/simulate", response_model=SentinelVerdictResponse)
async def simulate_action(
    request: ActionEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dry-run evaluation of a proposed agent action.

    Identical to /sentinel/evaluate but writes **no** Decision record to the
    Ancestor ledger. Safe to call repeatedly for what-if analysis, testing
    policy rule changes, or pre-flight checks before commit.

    Returns the same SentinelVerdictResponse including optional Prophecy paths.
    """
    agent = await db.get(Agent, request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    amount = request.action.get("amount", 0)
    policy_results = []
    violations = []

    result = await db.execute(select(Policy).where(Policy.is_active == True))
    policies = result.scalars().all()

    for policy in policies:
        if "*" not in policy.applies_to_roles and agent.role not in policy.applies_to_roles:
            continue
        if "*" not in policy.applies_to_tiers and agent.tier not in policy.applies_to_tiers:
            continue

        rule = policy.rule_definition
        passed = _evaluate_rule(rule, agent, request.action, request.context)
        policy_results.append({
            "policy_code": policy.policy_code,
            "policy_name": policy.policy_name,
            "passed": passed,
            "severity": policy.severity,
        })
        if not passed:
            violations.append({
                "policy_code": policy.policy_code,
                "severity": policy.severity,
                "action": policy.action_on_violation,
            })

    if any(v["severity"] == "critical" for v in violations):
        verdict = SentinelVerdict.block
        reasoning = "[DRY-RUN] BLOCKED: Critical policy violation(s)"
        confidence = 0.99
    elif amount > float(agent.authority_limit):
        verdict = SentinelVerdict.escalate
        reasoning = f"[DRY-RUN] ESCALATE: Amount exceeds authority limit ₹{float(agent.authority_limit):,.2f}"
        confidence = 0.95
    elif violations:
        verdict = SentinelVerdict.escalate
        reasoning = "[DRY-RUN] ESCALATE: Non-critical policy violations"
        confidence = 0.85
    else:
        verdict = SentinelVerdict.approve
        reasoning = f"[DRY-RUN] APPROVED: All {len(policy_results)} policies passed"
        confidence = 0.92

    # Run Prophecy if triggered — same criteria as evaluate
    prophecy_paths = None
    action_type = request.action.get("type", "unknown")
    should_run, trigger_reason = _prophecy.should_trigger(
        trust_score=float(agent.trust_score),
        amount=float(amount),
        authority_limit=float(agent.authority_limit),
        historical_action_count=agent.total_decisions,
    )
    if should_run:
        try:
            prophecy_result = _prophecy.simulate(
                agent_id=str(agent.id),
                action_type=action_type,
                amount=float(amount),
                trust_score=float(agent.trust_score),
                tier=agent.tier,
                authority_limit=float(agent.authority_limit),
                historical_success_rate=_estimate_success_rate(agent),
                trigger_reason=trigger_reason,
            )
            prophecy_paths = [p.to_dict() for p in prophecy_result.paths]
        except Exception as e:
            logger.error(f"[SENTINEL][simulate] Prophecy Engine error: {e}", exc_info=True)

    return SentinelVerdictResponse(
        verdict=verdict,
        reasoning=reasoning,
        policy_results=policy_results,
        prophecy_paths=prophecy_paths,
        confidence=confidence,
    )


# ──────────────────────────────────────────────────────────────────────────────
# NEW: GET /sentinel/health  — service health
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/sentinel/health")
@router.get("/health")
async def sentinel_health(db: AsyncSession = Depends(get_db)):
    """Sentinel service health check.

    Returns active policy count, prophecy engine status, and service version.
    """
    from datetime import datetime

    result = await db.execute(
        select(Policy).where(Policy.is_active == True)
    )
    active_policies = len(result.scalars().all())

    return {
        "status": "healthy",
        "service": "SENTINEL",
        "active_policies": active_policies,
        "prophecy_engine": "ready",
        "checked_at": datetime.now(UTC).isoformat(),
    }


@router.get("/sentinel/telemetry")
@router.get("/telemetry")
async def get_sentinel_telemetry(limit: int = 50):
    """Returns streaming decision telemetry events with SHA-256 audit hashes."""
    return {
        "status": "ok",
        "total_buffered": len(telemetry_streamer._buffer),
        "events": telemetry_streamer.get_recent_events(limit=limit),
    }

