"""
Pricing Router — /api/v1/pricing
Builder sets per-run prices and subscription tiers. Public tier listing.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.rate_limit import mutation_limit
from app.db.session import get_db
from app.models.agent_listing import AgentListing
from app.models.billing_models import AgentPricing

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


class PricingUpdate(BaseModel):
    free_tier_runs: Optional[int] = None
    price_per_run: Optional[float] = None
    subscription_monthly_price: Optional[float] = None


SUBSCRIPTION_TIERS = [
    {
        "tier": "free",
        "name": "Community Free",
        "price_monthly_usd": 0,
        "runs_limit": 100,
        "features": [
            "100 agent runs/month per org",
            "Community catalog access",
            "Basic CLI integration",
            "Public trust scores",
        ],
    },
    {
        "tier": "pro",
        "name": "Pro",
        "price_monthly_usd": 49,
        "runs_limit": "unlimited",
        "features": [
            "Unlimited agent runs",
            "Priority execution queue",
            "Revenue dashboard",
            "Compliance badge declarations",
            "Builder KYC verification",
            "Razorpay billing integration",
        ],
    },
    {
        "tier": "enterprise",
        "name": "Enterprise",
        "price_monthly_usd": "custom",
        "runs_limit": "unlimited",
        "features": [
            "Everything in Pro",
            "Private marketplace catalog",
            "SSO / SAML integration",
            "Custom SLA & uptime guarantees",
            "AgentGovern policy enforcement",
            "Dedicated support & onboarding",
            "Audit logs & compliance exports",
        ],
    },
]


@router.get("/tiers")
def list_tiers():
    """Return all available subscription tier definitions."""
    return SUBSCRIPTION_TIERS


@router.get("/agents/{builder}/{agent}")
def get_agent_pricing(builder: str, agent: str, db: Session = Depends(get_db)):
    """Get the pricing config for a specific agent."""
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")

    pricing = db.query(AgentPricing).filter(AgentPricing.listing_id == listing.id).first()
    if not pricing:
        return {
            "slug": slug,
            "free_tier_runs": 100,
            "price_per_run": 0.0,
            "subscription_monthly_price": 0.0,
            "display": "Free · 100 runs/org/month",
        }

    display = f"Free up to {pricing.free_tier_runs} runs/month"
    if pricing.price_per_run > 0:
        display += f" · ${pricing.price_per_run:.4f}/run after"

    return {
        "slug": slug,
        "listing_id": listing.id,
        "free_tier_runs": pricing.free_tier_runs,
        "price_per_run": pricing.price_per_run,
        "subscription_monthly_price": pricing.subscription_monthly_price,
        "display": display,
        "updated_at": pricing.updated_at,
    }


@router.put("/agents/{builder}/{agent}")
@mutation_limit("10/minute")
def update_agent_pricing(request: Request, builder: str, agent: str, req: PricingUpdate, db: Session = Depends(get_db)):
    """Builder sets pricing for their agent."""
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")

    pricing = db.query(AgentPricing).filter(AgentPricing.listing_id == listing.id).first()
    if not pricing:
        pricing = AgentPricing(listing_id=listing.id)
        db.add(pricing)

    if req.free_tier_runs is not None:
        if req.free_tier_runs < 0:
            raise HTTPException(status_code=422, detail="free_tier_runs must be >= 0.")
        pricing.free_tier_runs = req.free_tier_runs

    if req.price_per_run is not None:
        if req.price_per_run < 0:
            raise HTTPException(status_code=422, detail="price_per_run must be >= 0.")
        pricing.price_per_run = req.price_per_run

    if req.subscription_monthly_price is not None:
        pricing.subscription_monthly_price = req.subscription_monthly_price

    db.commit()
    db.refresh(pricing)
    return {
        "slug": slug,
        "free_tier_runs": pricing.free_tier_runs,
        "price_per_run": pricing.price_per_run,
        "subscription_monthly_price": pricing.subscription_monthly_price,
        "message": "Pricing updated successfully.",
    }
