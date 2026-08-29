"""
Billing Engine — Execution metering, plan enforcement, payout aggregation.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.billing_models import (
    AgentPricing, ExecutionRecord, OrganizationPlan, BuilderPayout, CreditBalance, PayoutRequest
)
from app.models.agent_listing import AgentListing


TIER_RUN_LIMITS = {
    "free": 100,
    "pro": -1,        # unlimited
    "enterprise": -1,  # unlimited (custom SLA)
}

PLATFORM_FEE_RATE = 0.20   # Nuuvixx takes 20%
BUILDER_SHARE_RATE = 0.80  # Builder keeps 80%


def get_or_create_org_plan(org_id: str, db: Session) -> OrganizationPlan:
    plan = db.query(OrganizationPlan).filter(OrganizationPlan.org_id == org_id).first()
    if not plan:
        plan = OrganizationPlan(
            org_id=org_id,
            tier="free",
            runs_limit=TIER_RUN_LIMITS["free"],
            runs_used_this_month=0,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def check_plan_limit(org_id: str, db: Session) -> tuple[bool, OrganizationPlan]:
    """
    Returns (allowed: bool, plan: OrganizationPlan).
    allowed=False means org has exceeded their monthly limit.
    """
    plan = get_or_create_org_plan(org_id, db)
    if plan.runs_limit == -1:
        return True, plan
    allowed = plan.runs_used_this_month < plan.runs_limit
    return allowed, plan


def compute_execution_cost(listing_id: int, tokens_used: int, db: Session) -> float:
    """Compute USD cost for an execution based on AgentPricing config."""
    pricing = db.query(AgentPricing).filter(AgentPricing.listing_id == listing_id).first()
    if not pricing or pricing.price_per_run == 0.0:
        return 0.0
    # Simple model: base price per run + token surcharge ($0.000001 per token)
    token_cost = tokens_used * 0.000001
    return round(pricing.price_per_run + token_cost, 6)


def meter_execution(
    listing_id: int,
    org_id: str,
    caller_id: str,
    duration_ms: int,
    tokens_used: int,
    db: Session,
) -> dict:
    """
    Record a single execution. Checks plan limits first.
    Returns {"allowed": bool, "record_id": int | None, "cost_usd": float}
    """
    allowed, plan = check_plan_limit(org_id, db)
    if not allowed:
        return {"allowed": False, "record_id": None, "cost_usd": 0.0, "reason": "Monthly run limit exceeded. Upgrade to Pro."}

    cost = compute_execution_cost(listing_id, tokens_used, db)

    record = ExecutionRecord(
        listing_id=listing_id,
        org_id=org_id,
        caller_id=caller_id,
        run_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        cost_usd=cost,
        billed=False,
    )
    db.add(record)

    # Increment usage counter
    plan.runs_used_this_month += 1
    plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return {"allowed": True, "record_id": record.id, "cost_usd": cost}


def get_org_usage(org_id: str, db: Session) -> dict:
    """Current period usage summary for an organization."""
    plan = get_or_create_org_plan(org_id, db)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_cost = db.query(func.sum(ExecutionRecord.cost_usd)).filter(
        ExecutionRecord.org_id == org_id,
        ExecutionRecord.run_at >= month_start,
    ).scalar() or 0.0

    return {
        "org_id": org_id,
        "tier": plan.tier,
        "runs_used": plan.runs_used_this_month,
        "runs_limit": plan.runs_limit if plan.runs_limit != -1 else "unlimited",
        "total_cost_usd": round(total_cost, 4),
    }


def get_builder_revenue(builder_id: str, db: Session) -> dict:
    """Revenue summary for a builder."""
    # Find all listing IDs owned by this builder
    listing_ids = [
        row.id for row in db.query(AgentListing.id).filter(AgentListing.builder_id == builder_id).all()
    ]
    if not listing_ids:
        return {"builder_id": builder_id, "gross_revenue_usd": 0.0, "net_revenue_usd": 0.0, "total_runs": 0, "listings": []}

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    gross = db.query(func.sum(ExecutionRecord.cost_usd)).filter(
        ExecutionRecord.listing_id.in_(listing_ids),
        ExecutionRecord.run_at >= month_start,
    ).scalar() or 0.0

    total_runs = db.query(func.count(ExecutionRecord.id)).filter(
        ExecutionRecord.listing_id.in_(listing_ids),
        ExecutionRecord.run_at >= month_start,
    ).scalar() or 0

    # Per-listing breakdown
    listings_data = []
    for lid in listing_ids:
        listing = db.query(AgentListing).filter(AgentListing.id == lid).first()
        if not listing:
            continue
        l_gross = db.query(func.sum(ExecutionRecord.cost_usd)).filter(
            ExecutionRecord.listing_id == lid,
            ExecutionRecord.run_at >= month_start,
        ).scalar() or 0.0
        l_runs = db.query(func.count(ExecutionRecord.id)).filter(
            ExecutionRecord.listing_id == lid,
            ExecutionRecord.run_at >= month_start,
        ).scalar() or 0
        listings_data.append({
            "slug": listing.slug,
            "name": listing.name,
            "runs": l_runs,
            "gross_usd": round(l_gross, 4),
            "net_usd": round(l_gross * BUILDER_SHARE_RATE, 4),
        })

    return {
        "builder_id": builder_id,
        "period": month_start.strftime("%Y-%m"),
        "gross_revenue_usd": round(gross, 4),
        "platform_fee_usd": round(gross * PLATFORM_FEE_RATE, 4),
        "net_revenue_usd": round(gross * BUILDER_SHARE_RATE, 4),
        "total_runs": total_runs,
        "listings": listings_data,
    }


def aggregate_builder_payouts(period_start: datetime, period_end: datetime, db: Session) -> list[dict]:
    """Batch job: compute monthly BuilderPayout records for all active builders."""
    builders = db.query(AgentListing.builder_id).distinct().all()
    results = []
    for (builder_id,) in builders:
        listing_ids = [
            row.id for row in db.query(AgentListing.id).filter(AgentListing.builder_id == builder_id).all()
        ]
        gross = db.query(func.sum(ExecutionRecord.cost_usd)).filter(
            ExecutionRecord.listing_id.in_(listing_ids),
            ExecutionRecord.run_at >= period_start,
            ExecutionRecord.run_at < period_end,
            ExecutionRecord.billed == True,
        ).scalar() or 0.0

        if gross == 0:
            continue

        payout = BuilderPayout(
            builder_id=builder_id,
            period_start=period_start,
            period_end=period_end,
            gross_revenue_usd=round(gross, 4),
            platform_fee_usd=round(gross * PLATFORM_FEE_RATE, 4),
            net_payout_usd=round(gross * BUILDER_SHARE_RATE, 4),
            status="pending",
        )
        db.add(payout)
        results.append({"builder_id": builder_id, "net_payout_usd": payout.net_payout_usd})

    db.commit()
    return results


def get_or_create_credit_balance(org_id: str, db: Session) -> CreditBalance:
    """Fetch or initialize credit balance for an organization."""
    balance = db.query(CreditBalance).filter(CreditBalance.org_id == org_id).first()
    if not balance:
        balance = CreditBalance(org_id=org_id, balance_usd=0.0, total_deposited_usd=0.0)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def topup_credit_balance(org_id: str, amount_usd: float, db: Session) -> CreditBalance:
    """Deposit credit balance for an organization."""
    if amount_usd <= 0:
        raise ValueError("Topup amount must be greater than zero.")
    balance = get_or_create_credit_balance(org_id, db)
    balance.balance_usd = round(balance.balance_usd + amount_usd, 4)
    balance.total_deposited_usd = round(balance.total_deposited_usd + amount_usd, 4)
    balance.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(balance)
    return balance


def deduct_credits(org_id: str, amount_usd: float, db: Session) -> tuple[bool, CreditBalance]:
    """Deduct credit balance for paid execution. Returns (success, balance)."""
    balance = get_or_create_credit_balance(org_id, db)
    if balance.balance_usd < amount_usd:
        return False, balance
    balance.balance_usd = round(balance.balance_usd - amount_usd, 4)
    balance.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(balance)
    return True, balance


MINIMUM_PAYOUT_THRESHOLD_USD = 50.0

def process_builder_payout_request(
    builder_id: str, amount_usd: float, payout_method: str, db: Session
) -> tuple[bool, str, PayoutRequest | None]:
    """Process a builder payout request enforcing minimum withdrawal limits."""
    if amount_usd < MINIMUM_PAYOUT_THRESHOLD_USD:
        return False, f"Minimum payout request amount is ${MINIMUM_PAYOUT_THRESHOLD_USD:.2f}.", None

    revenue = get_builder_revenue(builder_id, db)
    if revenue["net_revenue_usd"] < amount_usd:
        return False, f"Requested amount ${amount_usd:.2f} exceeds available net revenue ${revenue['net_revenue_usd']:.2f}.", None

    payout_req = PayoutRequest(
        builder_id=builder_id,
        amount_usd=round(amount_usd, 4),
        payout_method=payout_method,
        status="pending",
        requested_at=datetime.now(timezone.utc),
    )
    db.add(payout_req)
    db.commit()
    db.refresh(payout_req)
    return True, "Payout request submitted successfully.", payout_req

