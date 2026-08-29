"""
Billing Router — /api/v1/billing
Execution metering, org usage, plan management, builder revenue, Razorpay webhooks.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, cast, Any
import os

from app.db.session import get_db
from app.core.rate_limit import mutation_limit
from app.models.billing_models import OrganizationPlan, BuilderPayout
from app.services.billing_engine import (
    meter_execution, get_org_usage, get_builder_revenue,
    get_or_create_org_plan, TIER_RUN_LIMITS,
    get_or_create_credit_balance, topup_credit_balance, process_builder_payout_request
)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# ── Schemas ────────────────────────────────────────────────────────────────────

from typing import Union

class MeterRequest(BaseModel):
    listing_id: Union[int, str]
    org_id: str
    caller_id: str
    duration_ms: int = 0
    tokens_used: int = 0


class SubscribeRequest(BaseModel):
    tier: str               # pro, enterprise
    email: str
    razorpay_customer_id: Optional[str] = None


class CreditTopupRequest(BaseModel):
    amount_usd: float


class PayoutSubmitRequest(BaseModel):
    amount_usd: float
    payout_method: Optional[str] = "bank_transfer"



# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/meter")
@mutation_limit("30/minute")
def record_execution(request: Request, req: MeterRequest, db: Session = Depends(get_db)):
    """Called by AgentOS on every agent execution to meter usage."""
    try:
        lid = int(req.listing_id)
    except (ValueError, TypeError):
        lid = 1  # Fallback demo listing ID if non-numeric string passed

    result = meter_execution(
        listing_id=lid,
        org_id=req.org_id,
        caller_id=req.caller_id,
        duration_ms=req.duration_ms,
        tokens_used=req.tokens_used,
        db=db,
    )
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=result.get("reason", "Monthly run limit exceeded. Upgrade plan to continue."),
        )
    return result


@router.get("/orgs/{org_id}/usage")
def org_usage(org_id: str, db: Session = Depends(get_db)):
    """Get current period usage and cost for an organization."""
    return get_org_usage(org_id, db)


@router.get("/orgs/{org_id}/plan")
def org_plan(org_id: str, db: Session = Depends(get_db)):
    """Get the active subscription plan for an organization."""
    plan = get_or_create_org_plan(org_id, db)
    return {
        "org_id": plan.org_id,
        "tier": plan.tier,
        "runs_limit": plan.runs_limit if plan.runs_limit != -1 else "unlimited",
        "runs_used_this_month": plan.runs_used_this_month,
        "plan_started_at": plan.plan_started_at,
        "plan_expires_at": plan.plan_expires_at,
        "razorpay_subscription_id": plan.razorpay_subscription_id,
    }


@router.post("/orgs/{org_id}/subscribe")
@mutation_limit("10/minute")
def subscribe_org(request: Request, org_id: str, req: SubscribeRequest, db: Session = Depends(get_db)):
    """Upgrade an organization's plan tier."""
    valid_tiers = {"pro", "enterprise"}
    if req.tier not in valid_tiers:
        raise HTTPException(status_code=422, detail=f"tier must be one of {valid_tiers}.")

    plan = get_or_create_org_plan(org_id, db)
    plan.tier = cast(Any, req.tier)
    plan.runs_limit = cast(Any, TIER_RUN_LIMITS.get(req.tier, -1))
    if req.razorpay_customer_id:
        plan.razorpay_customer_id = cast(Any, req.razorpay_customer_id)

    db.commit()
    db.refresh(plan)
    return {
        "org_id": org_id,
        "tier": plan.tier,
        "runs_limit": "unlimited" if plan.runs_limit == -1 else plan.runs_limit,
        "message": f"Successfully upgraded to {req.tier} plan.",
    }


@router.post("/orgs/{org_id}/cancel")
@mutation_limit("10/minute")
def cancel_plan(request: Request, org_id: str, db: Session = Depends(get_db)):
    """Downgrade organization back to free tier."""
    plan = get_or_create_org_plan(org_id, db)
    plan.tier = cast(Any, "free")
    plan.runs_limit = cast(Any, TIER_RUN_LIMITS["free"])
    plan.razorpay_subscription_id = cast(Any, None)
    db.commit()
    return {"org_id": org_id, "tier": "free", "message": "Plan cancelled. Reverted to free tier."}


@router.get("/builders/{builder_id}/revenue")
def builder_revenue(builder_id: str, db: Session = Depends(get_db)):
    """Revenue dashboard data for a builder (current month)."""
    return get_builder_revenue(builder_id, db)


@router.get("/builders/{builder_id}/payouts")
def builder_payouts(builder_id: str, db: Session = Depends(get_db)):
    """Historical payout records for a builder."""
    payouts = (
        db.query(BuilderPayout)
        .filter(BuilderPayout.builder_id == builder_id)
        .order_by(BuilderPayout.id.desc())
        .limit(24)
        .all()
    )
    return [
        {
            "id": p.id,
            "period_start": p.period_start,
            "period_end": p.period_end,
            "gross_revenue_usd": p.gross_revenue_usd,
            "platform_fee_usd": p.platform_fee_usd,
            "net_payout_usd": p.net_payout_usd,
            "status": p.status,
            "razorpay_payout_id": p.razorpay_payout_id,
        }
        for p in payouts
    ]


@router.get("/orgs/{org_id}/credits")
def get_credit_balance(org_id: str, db: Session = Depends(get_db)):
    """Get current credit balance for an organization."""
    bal = get_or_create_credit_balance(org_id, db)
    return {
        "org_id": bal.org_id,
        "balance_usd": bal.balance_usd,
        "total_deposited_usd": bal.total_deposited_usd,
        "updated_at": bal.updated_at,
    }


@router.post("/orgs/{org_id}/credits/topup")
@mutation_limit("10/minute")
def topup_credits(request: Request, org_id: str, req: CreditTopupRequest, db: Session = Depends(get_db)):
    """Top-up credit balance for an organization."""
    if req.amount_usd <= 0:
        raise HTTPException(status_code=422, detail="amount_usd must be greater than 0.")
    bal = topup_credit_balance(org_id, req.amount_usd, db)
    return {
        "org_id": org_id,
        "balance_usd": bal.balance_usd,
        "total_deposited_usd": bal.total_deposited_usd,
        "message": f"Successfully deposited ${req.amount_usd:.2f} USD.",
    }


@router.post("/builders/{builder_id}/payouts/request")
@mutation_limit("5/minute")
def request_payout(request: Request, builder_id: str, req: PayoutSubmitRequest, db: Session = Depends(get_db)):
    """Submit a builder payout withdrawal request (Minimum $50 USD)."""
    success, msg, payout_req = process_builder_payout_request(
        builder_id=builder_id,
        amount_usd=req.amount_usd,
        payout_method=req.payout_method or "bank_transfer",
        db=db,
    )
    if not success or payout_req is None:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "request_id": payout_req.id,
        "builder_id": builder_id,
        "amount_usd": payout_req.amount_usd,
        "payout_method": payout_req.payout_method,
        "status": payout_req.status,
        "message": msg,
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Handle Razorpay webhook events (subscription activated/cancelled, payment success)."""
    body = await request.body()
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    if webhook_secret and x_razorpay_signature:
        from app.services.razorpay_client import verify_webhook_signature
        if not verify_webhook_signature(body, x_razorpay_signature, webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    import json
    payload = json.loads(body)
    event = payload.get("event", "")

    if event == "subscription.activated":
        sub_id = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")
        notes = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("notes", {})
        org_id = notes.get("org_id")
        if org_id and sub_id:
            plan = get_or_create_org_plan(org_id, db)
            plan.razorpay_subscription_id = cast(Any, sub_id)
            plan.tier = cast(Any, notes.get("tier", "pro"))
            plan.runs_limit = cast(Any, -1)
            db.commit()

    elif event == "subscription.cancelled":
        sub_id = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")
        if sub_id:
            plan = db.query(OrganizationPlan).filter(
                OrganizationPlan.razorpay_subscription_id == sub_id
            ).first()
            if plan:
                plan.tier = cast(Any, "free")
                plan.runs_limit = cast(Any, TIER_RUN_LIMITS["free"])
                plan.razorpay_subscription_id = cast(Any, None)
                db.commit()

    elif event == "payment.captured":
        notes = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
        org_id = notes.get("org_id")
        topup_usd = float(notes.get("amount_usd", 0.0))
        if org_id and topup_usd > 0:
            topup_credit_balance(org_id, topup_usd, db)

    return {"status": "processed", "event": event}


@router.get("/executions")
def list_agent_executions(agent_slug: Optional[str] = None, db: Session = Depends(get_db)):
    """Return execution history records for a given agent or organization."""
    from app.models.billing_models import ExecutionRecord
    from app.models.agent_listing import AgentListing

    query = db.query(ExecutionRecord)
    if agent_slug:
        listing = db.query(AgentListing).filter(AgentListing.slug == agent_slug).first()
        if listing:
            query = query.filter(ExecutionRecord.listing_id == listing.id)

    records = query.order_by(ExecutionRecord.id.desc()).limit(100).all()
    return [
        {
            "id": f"run-{r.id}",
            "session_id": f"sess_{r.id * 13 + 1000}",
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else "recently",
            "duration_ms": r.duration_ms,
            "tokens": r.tokens_used,
            "cost_usd": r.cost_usd,
            "status": "success" if r.billed else "blocked",
            "trigger": "api",
            "input_summary": f"Execution request on listing #{r.listing_id}",
            "output_summary": f"Metered execution completed successfully. Cost: ${r.cost_usd:.4f}",
            "policy_decision": "ALLOW" if r.billed else "BLOCKED",
        }
        for r in records
    ]


