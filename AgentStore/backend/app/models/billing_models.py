"""
Phase 3 — Monetization Models
AgentPricing, ExecutionRecord, OrganizationPlan, BuilderPayout
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from app.db.base_class import Base


class AgentPricing(Base):
    """Pricing configuration set by the builder for each listing."""
    __tablename__ = "agent_pricing"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    free_tier_runs = Column(Integer, default=100)             # Free runs allowed per org per month
    price_per_run = Column(Float, default=0.0)                # USD per execution
    subscription_monthly_price = Column(Float, default=0.0)   # USD/month for unlimited
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ExecutionRecord(Base):
    """Single metered execution of an agent — called by AgentOS on every run."""
    __tablename__ = "execution_records"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String, nullable=False, index=True)
    caller_id = Column(String, nullable=False)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    billed = Column(Boolean, default=False)


class OrganizationPlan(Base):
    """Subscription tier and usage tracking per organization."""
    __tablename__ = "organization_plans"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, unique=True, index=True, nullable=False)
    tier = Column(String, default="free")                      # free, pro, enterprise
    razorpay_customer_id = Column(String, nullable=True)
    razorpay_subscription_id = Column(String, nullable=True)
    runs_used_this_month = Column(Integer, default=0)
    runs_limit = Column(Integer, default=100)                  # -1 = unlimited
    plan_started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    plan_expires_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BuilderPayout(Base):
    """Monthly payout record for a builder — 80% of gross revenue."""
    __tablename__ = "builder_payouts"

    id = Column(Integer, primary_key=True, index=True)
    builder_id = Column(String, index=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    gross_revenue_usd = Column(Float, default=0.0)
    platform_fee_usd = Column(Float, default=0.0)   # 20% Nuuvixx fee
    net_payout_usd = Column(Float, default=0.0)     # 80% to builder
    status = Column(String, default="pending")       # pending, processing, paid
    razorpay_payout_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CreditBalance(Base):
    """Credit balance in USD for an organization."""
    __tablename__ = "credit_balances"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, unique=True, index=True, nullable=False)
    balance_usd = Column(Float, default=0.0)
    total_deposited_usd = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PayoutRequest(Base):
    """Individual payout withdrawal request by a builder."""
    __tablename__ = "payout_requests"

    id = Column(Integer, primary_key=True, index=True)
    builder_id = Column(String, index=True, nullable=False)
    amount_usd = Column(Float, nullable=False)
    payout_method = Column(String, default="bank_transfer")  # bank_transfer, upi, razorpay
    status = Column(String, default="pending")               # pending, approved, processing, completed, rejected
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

