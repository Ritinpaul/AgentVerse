"""ANCESTOR Audit Router — Immutable Decision Ledger endpoints.

Endpoints:
  GET  /api/v1/audit/                        — List recent decisions
  GET  /api/v1/audit/chain/verify            — Verify hash chain integrity
  GET  /api/v1/audit/{decision_id}           — Get a single decision record
  GET  /api/v1/audit/{decision_id}/replay    — Replay (re-evaluate) a past decision
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import Agent, Decision, Policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _recompute_hash(decision: Decision) -> str:
    """Recompute the SHA-256 hash for a Decision row using the canonical payload.

    Mirrors the hashing logic in services/crewai-engine/ancestor/decision_ledger.py
    so that we can verify ledger integrity without depending on the CrewAI service.
    """
    payload = {
        "id": str(decision.id),
        "agent_id": str(decision.agent_id),
        "task_id": str(decision.task_id),
        "decision_type": decision.decision_type,
        "output_action": decision.output_action,
        "confidence_score": (
            float(decision.confidence_score) if decision.confidence_score is not None else None
        ),
        "amount_involved": (
            float(decision.amount_involved) if decision.amount_involved is not None else None
        ),
        "timestamp": decision.timestamp.isoformat if decision.timestamp else "",
        "prev_hash": decision.prev_hash or "",
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode).hexdigest


def _decision_to_log(d: Decision) -> dict:
    """Convert a Decision ORM row to a compact audit log entry."""
    status = "allowed"
    if d.sentinel_assessment:
        verdt = d.sentinel_assessment.get("verdict", "").lower
        if verdt == "approve":
            status = "allowed"
        elif verdt == "block":
            status = "denied"
        elif verdt == "escalate":
            status = "escalated"

    env = "Cloud (Master)"
    if isinstance(d.input_context, dict):
        env = d.input_context.get("environment", "Cloud (Master)")

    return {
        "id": f"{d.hash[:8]}...{d.hash[-4:]}" if d.hash else "0x000...000",
        "agent": d.agent.did if getattr(d, "agent", None) else str(d.agent_id)[:8],
        "env": env,
        "action": d.decision_type.replace("_", " ").title,
        "amount": (
            f"\u20b9{float(d.amount_involved):,.0f}"
            if d.amount_involved is not None and d.amount_involved > 0
            else "-"
        ),
        "status": status,
        "time": d.timestamp.isoformat if d.timestamp else "Just now",
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/audit/  — list recent decisions
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_decisions(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List recent ledger decisions across all environments."""
    query = (
        select(Decision)
        .options(selectinload(Decision.agent))
        .order_by(Decision.timestamp.desc)
        .limit(limit)
    )
    result = await db.execute(query)
    decisions = result.scalars.all
    return [_decision_to_log(d) for d in decisions]


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/audit/chain/verify  — hash chain integrity check
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/chain/verify")
async def verify_chain(
    agent_id: UUID | None = None,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    """Walk the decision hash chain and verify its integrity.

    For every block:
      1. Recomputes the block's expected hash from its payload fields.
      2. Compares the stored hash against the recomputed one (tamper detection).
      3. Checks that stored prev_hash matches the previous block's hash (chain linkage).

    Returns:
      - valid: True if the entire chain is intact
      - total_blocks: how many blocks were checked
      - broken_blocks: list of decision IDs where integrity failed
      - broken_links: list of decision IDs where chain linkage failed
      - integrity_pct: percentage of blocks that passed both checks
      - verified_at: timestamp of this verification run
    """
    query = select(Decision).order_by(Decision.timestamp.asc).limit(limit)
    if agent_id:
        query = query.where(Decision.agent_id == agent_id)

    result = await db.execute(query)
    decisions = result.scalars.all

    if not decisions:
        return {
            "valid": True,
            "total_blocks": 0,
            "broken_blocks": [],
            "broken_links": [],
            "integrity_pct": 100.0,
            "note": "No decisions found in the ledger",
            "verified_at": datetime.now(UTC).isoformat,
        }

    broken_blocks: list[str] = []
    broken_links: list[str] = []
    expected_prev_hash = ""

    for decision in decisions:
        decision_id_str = str(decision.id)

        # ── Check 1: Hash integrity (tamper detection) ──
        recomputed = _recompute_hash(decision)
        if decision.hash and recomputed != decision.hash:
            broken_blocks.append(decision_id_str)
            logger.warning(
                f"[ANCESTOR] Hash mismatch on decision {decision_id_str}: "
                f"stored={decision.hash[:12]} computed={recomputed[:12]}"
            )

        # ── Check 2: Chain linkage ──
        stored_prev = decision.prev_hash or ""
        if stored_prev != expected_prev_hash:
            broken_links.append(decision_id_str)
            logger.warning(
                f"[ANCESTOR] Chain break at decision {decision_id_str}: "
                f"expected_prev={expected_prev_hash[:12] if expected_prev_hash else 'genesis'} "
                f"stored_prev={stored_prev[:12] if stored_prev else 'genesis'}"
            )

        expected_prev_hash = decision.hash or recomputed

    total = len(decisions)
    broken_total = len(set(broken_blocks) | set(broken_links))
    integrity_pct = round((total - broken_total) / total * 100, 2) if total else 100.0

    return {
        "valid": not broken_blocks and not broken_links,
        "total_blocks": total,
        "broken_blocks": broken_blocks,
        "broken_links": broken_links,
        "integrity_pct": integrity_pct,
        "verified_at": datetime.now(UTC).isoformat,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/audit/{decision_id}  — single decision detail
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{decision_id}")
async def get_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a single decision record by ID."""
    result = await db.execute(
        select(Decision)
        .options(selectinload(Decision.agent))
        .where(Decision.id == decision_id)
    )
    decision = result.scalar_one_or_none
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    return {
        "id": str(decision.id),
        "agent_id": str(decision.agent_id),
        "agent_code": decision.agent.agent_code if decision.agent else None,
        "task_id": str(decision.task_id),
        "dispute_id": decision.dispute_id,
        "decision_type": decision.decision_type,
        "input_context": decision.input_context,
        "reasoning_trace": decision.reasoning_trace,
        "crewai_task_output": decision.crewai_task_output,
        "tools_used": decision.tools_used,
        "delegation_chain": decision.delegation_chain,
        "output_action": decision.output_action,
        "confidence_score": float(decision.confidence_score) if decision.confidence_score is not None else None,
        "risk_score": float(decision.risk_score) if decision.risk_score is not None else None,
        "amount_involved": float(decision.amount_involved) if decision.amount_involved is not None else None,
        "currency": decision.currency,
        "policy_rules_applied": decision.policy_rules_applied,
        "policy_violations": decision.policy_violations,
        "sentinel_assessment": decision.sentinel_assessment,
        "prophecy_paths": decision.prophecy_paths,
        "human_override": decision.human_override,
        "hash": decision.hash,
        "prev_hash": decision.prev_hash,
        "timestamp": decision.timestamp.isoformat if decision.timestamp else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/v1/audit/{decision_id}/replay  — decision replay
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{decision_id}/replay")
async def replay_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    """Replay a past decision by re-running SENTINEL policy evaluation on its original context.

    This endpoint:
      1. Fetches the original Decision record.
      2. Loads the agent at its current state.
      3. Re-evaluates the original action + context against all active policies.
      4. Returns a side-by-side comparison: original verdict vs current verdict.

    Use this to:
      - Detect policy drift (same action would now be evaluated differently)
      - Audit historical decisions against current policies
      - Debug why a decision was made
    """

    result = await db.execute(
        select(Decision)
        .options(selectinload(Decision.agent))
        .where(Decision.id == decision_id)
    )
    decision = result.scalar_one_or_none
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    agent = decision.agent
    if not agent:
        agent = await db.get(Agent, decision.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent for this decision no longer exists")

    # ── Re-run policy evaluation using original input_context ──
    original_action = decision.output_action or {}
    original_context = decision.input_context or {}

    amount = float(original_context.get("amount", original_action.get("amount", 0)) or 0)
    action_type = original_action.get("type", decision.decision_type)

    policy_result = await db.execute(select(Policy).where(Policy.is_active == True))
    policies = policy_result.scalars.all

    current_violations = []
    current_policy_results = []
    for policy in policies:
        if "*" not in policy.applies_to_roles and agent.role not in policy.applies_to_roles:
            continue
        if "*" not in policy.applies_to_tiers and agent.tier not in policy.applies_to_tiers:
            continue

        rule = policy.rule_definition
        rule_type = rule.get("type")
        passed = True

        if rule_type == "amount_limit":
            passed = amount <= rule.get("max_amount", 0)
        elif rule_type == "trust_minimum":
            passed = float(agent.trust_score) >= rule.get("min_trust", 0)
        elif rule_type == "tier_required":
            passed = agent.tier in rule.get("allowed_tiers", [])
        elif rule_type == "status_check":
            passed = agent.status == "active"
        elif rule_type == "action_blocked":
            passed = action_type not in rule.get("blocked_actions", [])
        elif rule_type == "action_allowed":
            allowed = rule.get("allowed_actions", [])
            passed = not allowed or action_type in allowed

        current_policy_results.append({
            "policy_code": policy.policy_code,
            "policy_name": policy.policy_name,
            "passed": passed,
            "severity": policy.severity,
        })
        if not passed:
            current_violations.append({
                "policy_code": policy.policy_code,
                "severity": policy.severity,
            })

    if any(v["severity"] == "critical" for v in current_violations):
        current_verdict = "block"
        current_reasoning = "BLOCKED: Critical policy violation(s) detected"
    elif amount > float(agent.authority_limit):
        current_verdict = "escalate"
        current_reasoning = f"ESCALATE: Amount exceeds authority limit {float(agent.authority_limit):,.2f}"
    elif current_violations:
        current_verdict = "escalate"
        current_reasoning = "ESCALATE: Non-critical policy violations detected"
    else:
        current_verdict = "approve"
        current_reasoning = f"APPROVED: All {len(current_policy_results)} policies passed"

    # ── Extract original verdict ──
    original_verdict = None
    original_reasoning = None
    if decision.sentinel_assessment:
        original_verdict = decision.sentinel_assessment.get("verdict")
        original_reasoning = decision.sentinel_assessment.get("reasoning")

    # ── Verdict drift detection ──
    verdict_changed = original_verdict != current_verdict if original_verdict else None

    # ── Hash integrity ──
    computed_hash = _recompute_hash(decision)
    hash_valid = computed_hash == decision.hash if decision.hash else None

    return {
        "decision_id": str(decision.id),
        "original": {
            "verdict": original_verdict,
            "reasoning": original_reasoning,
            "policy_results": decision.policy_rules_applied,
            "prophecy_paths": decision.prophecy_paths,
            "confidence_score": float(decision.confidence_score) if decision.confidence_score is not None else None,
            "timestamp": decision.timestamp.isoformat if decision.timestamp else None,
        },
        "replayed": {
            "verdict": current_verdict,
            "reasoning": current_reasoning,
            "policy_results": current_policy_results,
            "replayed_at": datetime.now(UTC).isoformat,
        },
        "verdict_changed": verdict_changed,
        "hash_valid": hash_valid,
        "agent": {
            "id": str(agent.id),
            "agent_code": agent.agent_code,
            "tier": agent.tier,
            "trust_score": float(agent.trust_score),
            "authority_limit": float(agent.authority_limit),
        },
        "original_action": original_action,
        "original_context": original_context,
    }
