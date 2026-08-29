"""
Phase 3 Tests — Billing Engine
Tests metering, plan limits, cost computation, and payout aggregation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
# Register all models
import app.models.agent_listing   # noqa: F401
import app.models.trust_models    # noqa: F401
import app.models.billing_models  # noqa: F401

from app.models.agent_listing import AgentListing
from app.models.billing_models import AgentPricing, ExecutionRecord
from app.services.billing_engine import (
    meter_execution, get_org_usage, get_builder_revenue,
    get_or_create_org_plan, compute_execution_cost,
    aggregate_builder_payouts,
)


# ── Test DB setup ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_listing(db):
    listing = AgentListing(
        slug="acme/support-agent",
        name="support-agent",
        description="Enterprise support agent.",
        builder_id="acme",
        category="support",
        tags=["support"],
        capabilities=["tool:get-ticket"],
        current_version="1.0.0",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@pytest.fixture
def priced_listing(db, sample_listing):
    pricing = AgentPricing(
        listing_id=sample_listing.id,
        free_tier_runs=100,
        price_per_run=0.05,
        subscription_monthly_price=49.0,
    )
    db.add(pricing)
    db.commit()
    return sample_listing


# ── Test: get_or_create_org_plan ─────────────────────────────────────────────

def test_creates_free_plan_on_first_access(db):
    plan = get_or_create_org_plan("new-org", db)
    assert plan.org_id == "new-org"
    assert plan.tier == "free"
    assert plan.runs_limit == 100
    assert plan.runs_used_this_month == 0


def test_returns_existing_plan(db):
    get_or_create_org_plan("org-alpha", db)
    plan2 = get_or_create_org_plan("org-alpha", db)
    assert plan2.tier == "free"  # no duplicate creation


# ── Test: compute_execution_cost ─────────────────────────────────────────────

def test_cost_zero_when_no_pricing(db, sample_listing):
    cost = compute_execution_cost(sample_listing.id, 1000, db)
    assert cost == 0.0


def test_cost_computed_from_pricing(db, priced_listing):
    cost = compute_execution_cost(priced_listing.id, 0, db)
    assert cost == pytest.approx(0.05, rel=1e-4)


def test_cost_includes_token_surcharge(db, priced_listing):
    cost = compute_execution_cost(priced_listing.id, 10_000, db)
    # $0.05 base + 10000 * $0.000001 = $0.05 + $0.01 = $0.06
    assert cost == pytest.approx(0.06, rel=1e-4)


# ── Test: meter_execution ─────────────────────────────────────────────────────

def test_meter_execution_allowed(db, sample_listing):
    result = meter_execution(sample_listing.id, "org-1", "user-1", 1000, 500, db)
    assert result["allowed"] is True
    assert result["record_id"] is not None


def test_meter_increments_usage(db, sample_listing):
    meter_execution(sample_listing.id, "org-2", "user-1", 500, 100, db)
    plan = get_or_create_org_plan("org-2", db)
    assert plan.runs_used_this_month == 1


def test_meter_free_tier_exceeded(db, sample_listing):
    """101st run on free tier should be denied."""
    # Manually set usage to limit
    plan = get_or_create_org_plan("org-limited", db)
    plan.runs_used_this_month = 100
    db.commit()

    result = meter_execution(sample_listing.id, "org-limited", "user-1", 500, 100, db)
    assert result["allowed"] is False
    assert "limit" in result["reason"].lower()


def test_pro_tier_no_limit(db, sample_listing):
    """Pro tier orgs have unlimited runs."""
    plan = get_or_create_org_plan("org-pro", db)
    plan.tier = "pro"
    plan.runs_limit = -1
    plan.runs_used_this_month = 9999
    db.commit()

    result = meter_execution(sample_listing.id, "org-pro", "user-1", 500, 100, db)
    assert result["allowed"] is True


# ── Test: get_org_usage ───────────────────────────────────────────────────────

def test_org_usage_returns_correct_runs(db, sample_listing):
    meter_execution(sample_listing.id, "org-usage", "user-1", 1000, 500, db)
    meter_execution(sample_listing.id, "org-usage", "user-2", 800, 300, db)
    usage = get_org_usage("org-usage", db)
    assert usage["runs_used"] == 2
    assert usage["org_id"] == "org-usage"
    assert usage["tier"] == "free"


# ── Test: get_builder_revenue ─────────────────────────────────────────────────

def test_builder_revenue_no_runs(db, sample_listing):
    revenue = get_builder_revenue("acme", db)
    assert revenue["gross_revenue_usd"] == 0.0
    assert revenue["net_revenue_usd"] == 0.0
    assert revenue["total_runs"] == 0


def test_builder_revenue_with_runs(db, priced_listing):
    meter_execution(priced_listing.id, "org-a", "user-1", 1000, 0, db)
    meter_execution(priced_listing.id, "org-b", "user-2", 1200, 0, db)
    revenue = get_builder_revenue("acme", db)
    # 2 runs × $0.05 = $0.10 gross; 80% = $0.08 net
    assert revenue["total_runs"] == 2
    assert revenue["gross_revenue_usd"] == pytest.approx(0.10, rel=1e-3)
    assert revenue["net_revenue_usd"] == pytest.approx(0.08, rel=1e-3)
    assert revenue["platform_fee_usd"] == pytest.approx(0.02, rel=1e-3)


def test_builder_revenue_80_20_split(db, priced_listing):
    """Verify 80/20 revenue split is always correct."""
    meter_execution(priced_listing.id, "org-c", "user-1", 500, 0, db)
    revenue = get_builder_revenue("acme", db)
    gross = revenue["gross_revenue_usd"]
    if gross > 0:
        assert abs(revenue["net_revenue_usd"] - gross * 0.8) < 0.0001
        assert abs(revenue["platform_fee_usd"] - gross * 0.2) < 0.0001


# ── Test: aggregate_builder_payouts ──────────────────────────────────────────

def test_payout_aggregation(db, priced_listing):
    """Billed executions generate payout records."""
    # Create billed execution records manually
    record = ExecutionRecord(
        listing_id=priced_listing.id,
        org_id="org-x",
        caller_id="user-1",
        run_at=datetime.now(timezone.utc),
        duration_ms=1000,
        tokens_used=0,
        cost_usd=0.05,
        billed=True,  # marked as billed
    )
    db.add(record)
    db.commit()

    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = now + timedelta(days=1)

    results = aggregate_builder_payouts(period_start, period_end, db)
    assert len(results) == 1
    assert results[0]["builder_id"] == "acme"
    assert results[0]["net_payout_usd"] == pytest.approx(0.04, rel=1e-3)


def test_payout_empty_when_no_billed_runs(db, sample_listing):
    """Unbilled executions do not generate payouts."""
    meter_execution(sample_listing.id, "org-y", "user-1", 500, 0, db)
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = now + timedelta(days=1)
    results = aggregate_builder_payouts(period_start, period_end, db)
    assert results == []
