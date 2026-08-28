"""CONTRACT Router — Social Contracts for AI Agents.

A Social Contract is the formal "employment agreement" between an AI agent
and the organisation. It defines:
  - Rights the agent is entitled to (compute, memory, tool access)
  - Responsibilities the agent must uphold (accuracy, escalation duties)
  - Authority bounds (max spend, allowed action categories)
  - Career path (promotion criteria, mentor assignments)
  - Performance benchmarks (min success rate, max failure rate, max escalations)
  - Review schedule (periodic human review dates)

Endpoints:
  POST   /api/v1/contracts/                          — Issue a new contract for an agent
  GET    /api/v1/contracts/                          — List contracts (filter by agent / status)
  GET    /api/v1/contracts/{contract_id}             — Get a single contract
  PATCH  /api/v1/contracts/{contract_id}             — Update contract terms
  DELETE /api/v1/contracts/{contract_id}             — Terminate a contract
  POST   /api/v1/contracts/{contract_id}/sign        — Human signs / approves the contract
  GET    /api/v1/contracts/{contract_id}/violations  — Detect contract violations
  GET    /api/v1/contracts/agent/{agent_id}          — Get active contract for an agent
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent, SocialContract
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class ContractCreate(BaseModel):
    agent_id: UUID
    rights: dict = Field(
        default_factory=lambda: {
            "compute_quota_daily": "unlimited",
            "memory_access": "read_write",
            "tool_access": [],
            "data_scope": "assigned_tasks_only",
        }
    )
    responsibilities: dict = Field(
        default_factory=lambda: {
            "must_escalate_above": 50000,
            "must_log_all_decisions": True,
            "max_autonomous_retries": 3,
            "prohibited_actions": [],
        }
    )
    authority_bounds: dict = Field(
        default_factory=lambda: {
            "max_spend_per_transaction": 10000,
            "max_spend_per_day": 50000,
            "allowed_action_categories": ["query", "report", "escalate"],
            "forbidden_action_categories": ["delete", "wire_transfer"],
        }
    )
    career_path: dict = Field(
        default_factory=lambda: {
            "current_tier": "T4",
            "promotion_target": "T3",
            "promotion_criteria": {"min_trust_score": 0.70, "min_decisions": 50, "min_success_rate": 0.90},
            "demotion_triggers": {"trust_below": 0.40, "failure_rate_above": 0.20},
        }
    )
    review_schedule: dict = Field(
        default_factory=lambda: {
            "frequency": "monthly",
            "next_review": None,
            "reviewer": "Platform Admin",
        }
    )
    mentor_assignments: list = Field(default_factory=list)
    performance_benchmarks: dict = Field(
        default_factory=lambda: {
            "min_success_rate": 0.85,
            "max_failure_rate": 0.10,
            "max_escalation_rate": 0.20,
            "min_trust_score": 0.50,
            "max_response_time_ms": 5000,
        }
    )
    expiry_date: datetime | None = None


class ContractUpdateRequest(BaseModel):
    rights: dict | None = None
    responsibilities: dict | None = None
    authority_bounds: dict | None = None
    career_path: dict | None = None
    review_schedule: dict | None = None
    mentor_assignments: list | None = None
    performance_benchmarks: dict | None = None
    expiry_date: datetime | None = None


class ContractSignRequest(BaseModel):
    signed_by: str = Field(..., description="Name or ID of the human administrator signing the contract")
    notes: str = Field(default="", description="Optional signing notes")


class ContractResponse(BaseModel):
    id: UUID
    agent_id: UUID
    contract_version: int
    status: str
    rights: dict
    responsibilities: dict
    authority_bounds: dict
    career_path: dict
    review_schedule: dict
    mentor_assignments: list
    performance_benchmarks: dict
    signed_by: str | None
    effective_date: datetime
    expiry_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# POST /contracts/  — issue a new contract
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(body: ContractCreate, db: AsyncSession = Depends(get_db)):
    """Issue a new Social Contract for an agent.

    If the agent already has an active contract, the existing one is
    superseded (set to 'superseded') and a new version is created.
    """
    agent = await db.get(Agent, body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Supersede any existing active contract
    existing_result = await db.execute(
        select(SocialContract)
        .where(SocialContract.agent_id == body.agent_id)
        .where(SocialContract.status == "active")
    )
    existing = existing_result.scalars.all
    latest_version = 0
    for old in existing:
        old.status = "superseded"
        if old.contract_version > latest_version:
            latest_version = old.contract_version

    contract = SocialContract(
        agent_id=body.agent_id,
        contract_version=latest_version + 1,
        status="draft",
        rights=body.rights,
        responsibilities=body.responsibilities,
        authority_bounds=body.authority_bounds,
        career_path=body.career_path,
        review_schedule=body.review_schedule,
        mentor_assignments=body.mentor_assignments,
        performance_benchmarks=body.performance_benchmarks,
        expiry_date=body.expiry_date,
    )
    db.add(contract)
    await db.flush
    await db.refresh(contract)

    logger.info(
        f"[CONTRACT] Issued v{contract.contract_version} for agent {agent.agent_code} "
        f"(status=draft, id={str(contract.id)[:8]})"
    )
    return contract


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/  — list contracts
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ContractResponse])
async def list_contracts(
    agent_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List Social Contracts with optional filters."""
    query = select(SocialContract).order_by(SocialContract.created_at.desc).limit(limit)
    if agent_id:
        query = query.where(SocialContract.agent_id == agent_id)
    if status_filter:
        query = query.where(SocialContract.status == status_filter)

    result = await db.execute(query)
    return result.scalars.all


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/agent/{agent_id}  — active contract for a specific agent
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/agent/{agent_id}", response_model=ContractResponse)
async def get_agent_active_contract(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the current active (or most recent) Social Contract for an agent."""
    result = await db.execute(
        select(SocialContract)
        .where(SocialContract.agent_id == agent_id)
        .where(SocialContract.status.in_(["active", "draft"]))
        .order_by(SocialContract.contract_version.desc)
    )
    contract = result.scalars.first
    if not contract:
        raise HTTPException(status_code=404, detail="No active contract found for this agent")
    return contract


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}  — single contract
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single Social Contract by ID."""
    contract = await db.get(SocialContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /contracts/{contract_id}  — update contract terms
# ──────────────────────────────────────────────────────────────────────────────

@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: UUID,
    updates: ContractUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update contract terms (partial update). Bumps contract_version."""
    contract = await db.get(SocialContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status == "terminated":
        raise HTTPException(status_code=400, detail="Cannot update a terminated contract")

    update_data = updates.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No update fields provided")

    allowed_fields = {
        "rights", "responsibilities", "authority_bounds",
        "career_path", "review_schedule", "mentor_assignments",
        "performance_benchmarks", "expiry_date",
    }
    for field, value in update_data.items:
        if field in allowed_fields:
            setattr(contract, field, value)

    contract.contract_version += 1
    await db.flush
    await db.refresh(contract)
    return contract


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /contracts/{contract_id}  — terminate a contract
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_contract(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    """Terminate a Social Contract (soft delete — sets status to 'terminated')."""
    contract = await db.get(SocialContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.status == "terminated":
        raise HTTPException(status_code=400, detail="Contract is already terminated")
    contract.status = "terminated"
    await db.flush


# ──────────────────────────────────────────────────────────────────────────────
# POST /contracts/{contract_id}/sign  — human signs the contract
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{contract_id}/sign", response_model=ContractResponse)
async def sign_contract(
    contract_id: UUID,
    body: ContractSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """Human administrator signs and activates a Social Contract.

    A contract must be in 'draft' status to be signed. On signing:
      - Status transitions draft → active
      - signed_by is recorded
      - effective_date is set to now
      - The agent's social_contract snapshot is updated
    """
    contract = await db.get(SocialContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Contract must be in 'draft' state to sign (current: '{contract.status}')",
        )

    contract.status = "active"
    contract.signed_by = body.signed_by
    contract.effective_date = datetime.now(UTC)

    # Sync agent's social_contract snapshot
    agent = await db.get(Agent, contract.agent_id)
    if agent:
        agent.social_contract = {
            "contract_id": str(contract.id),
            "contract_version": contract.contract_version,
            "signed_by": body.signed_by,
            "signed_at": datetime.now(UTC).isoformat,
            "notes": body.notes,
            "authority_bounds": contract.authority_bounds,
            "performance_benchmarks": contract.performance_benchmarks,
        }

    await db.flush
    await db.refresh(contract)

    logger.info(
        f"[CONTRACT] v{contract.contract_version} signed by '{body.signed_by}' "
        f"for agent {str(contract.agent_id)[:8]}"
    )
    return contract


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/violations  — violation detection
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{contract_id}/violations")
async def detect_violations(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    """Detect contract violations for an agent against its Social Contract.

    Checks the following against the contract's performance_benchmarks and
    authority_bounds:
      1. Trust score below minimum
      2. Authority limit exceeded (current agent limit > contract max)
      3. Decision failure rate above threshold (based on trust events)
      4. Escalation rate above threshold
      5. Contract expiry

    Returns a list of violations (empty = no violations).
    """

    contract = await db.get(SocialContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    agent = await db.get(Agent, contract.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent for this contract not found")

    violations: list[dict] = []
    benchmarks = contract.performance_benchmarks or {}
    authority_bounds = contract.authority_bounds or {}
    now = datetime.now(UTC)

    # ── Check 1: Trust score minimum ──
    min_trust = float(benchmarks.get("min_trust_score", 0.50))
    current_trust = float(agent.trust_score)
    if current_trust < min_trust:
        violations.append({
            "type": "trust_below_minimum",
            "severity": "high",
            "description": (
                f"Agent trust score {current_trust:.4f} is below contract minimum {min_trust:.4f}"
            ),
            "current_value": current_trust,
            "contract_threshold": min_trust,
        })

    # ── Check 2: Authority limit ──
    max_spend = float(authority_bounds.get("max_spend_per_transaction", float("inf")))
    current_limit = float(agent.authority_limit)
    if current_limit > max_spend and max_spend < float("inf"):
        violations.append({
            "type": "authority_limit_exceeded",
            "severity": "critical",
            "description": (
                f"Agent authority limit ₹{current_limit:,.0f} exceeds contract maximum "
                f"₹{max_spend:,.0f} per transaction"
            ),
            "current_value": current_limit,
            "contract_threshold": max_spend,
        })

    # ── Check 3: Decision failure rate ──
    total_decisions = agent.total_decisions
    if total_decisions > 0:
        failure_count = agent.total_overrides + agent.total_escalations
        failure_rate = round(failure_count / total_decisions, 4)
        max_failure_rate = float(benchmarks.get("max_failure_rate", 0.10))
        if failure_rate > max_failure_rate:
            violations.append({
                "type": "failure_rate_exceeded",
                "severity": "medium",
                "description": (
                    f"Agent failure/override rate {failure_rate:.2%} exceeds contract maximum "
                    f"{max_failure_rate:.2%}"
                ),
                "current_value": failure_rate,
                "contract_threshold": max_failure_rate,
            })

    # ── Check 4: Escalation rate ──
    if total_decisions > 0:
        escalation_rate = round(agent.total_escalations / total_decisions, 4)
        max_esc_rate = float(benchmarks.get("max_escalation_rate", 0.20))
        if escalation_rate > max_esc_rate:
            violations.append({
                "type": "escalation_rate_exceeded",
                "severity": "medium",
                "description": (
                    f"Agent escalation rate {escalation_rate:.2%} exceeds contract maximum "
                    f"{max_esc_rate:.2%}"
                ),
                "current_value": escalation_rate,
                "contract_threshold": max_esc_rate,
            })

    # ── Check 5: Contract expiry ──
    if contract.expiry_date and now > contract.expiry_date.replace(tzinfo=UTC):
        violations.append({
            "type": "contract_expired",
            "severity": "high",
            "description": (
                f"Contract expired on {contract.expiry_date.isoformat}. "
                f"A new contract must be issued and signed."
            ),
            "current_value": now.isoformat,
            "contract_threshold": contract.expiry_date.isoformat,
        })

    # ── Check 6: Agent status mismatch ──
    if agent.status in ("suspended", "retired"):
        violations.append({
            "type": "agent_inactive",
            "severity": "critical",
            "description": (
                f"Agent status is '{agent.status}' but contract is '{contract.status}'. "
                f"Contract should be terminated."
            ),
            "current_value": agent.status,
            "contract_threshold": "active",
        })

    critical_count = sum(1 for v in violations if v["severity"] == "critical")
    high_count = sum(1 for v in violations if v["severity"] == "high")

    return {
        "contract_id": str(contract.id),
        "contract_version": contract.contract_version,
        "agent_code": agent.agent_code,
        "contract_status": contract.status,
        "violations": violations,
        "violation_count": len(violations),
        "critical_violations": critical_count,
        "high_violations": high_count,
        "compliant": len(violations) == 0,
        "checked_at": now.isoformat,
        "recommendation": (
            "No violations detected — agent is operating within contract terms."
            if not violations
            else f"{len(violations)} violation(s) detected. "
            + ("Immediate action required." if critical_count > 0 else "Review recommended.")
        ),
    }
