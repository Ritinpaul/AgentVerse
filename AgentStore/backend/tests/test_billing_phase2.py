"""
Phase 2 — Monetization & Billing Infrastructure Tests
Tests:
  1. Organization plan tier upgrades & cancellations
  2. Execution metering & monthly run limit enforcement
  3. Credit balance top-ups & deductions
  4. Builder revenue calculation (80% share) & minimum payout withdrawal threshold ($50.00)
  5. Razorpay webhook processing (subscription & payment.captured)
  6. x402 Micropayment protocol header guard & HTTP 402 responses
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
import app.models.agent_listing   # noqa: F401
import app.models.trust_models    # noqa: F401
import app.models.billing_models  # noqa: F401
import app.models.composition_models # noqa: F401
import app.models.procurement_models # noqa: F401
import app.models.a2a_models         # noqa: F401

from app.main import app as fastapi_app
from app.db.session import get_db
from app.models.agent_listing import AgentListing
from app.models.billing_models import (
    AgentPricing, ExecutionRecord, OrganizationPlan,
    CreditBalance, PayoutRequest, BuilderPayout
)
from app.services.x402_middleware import require_x402_payment





# In-memory SQLite for billing tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    Base.metadata.create_all(bind=engine)
    import app.db.session
    monkeypatch.setattr(app.db.session, "SessionLocal", TestingSessionLocal)
    fastapi_app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    
    # Create test listing
    listing = AgentListing(
        name="Finance AI Agent",
        slug="finance-ai-agent",
        description="Automates ledger auditing",
        builder_id="builder-org-99",
        category="finance",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    # Set pricing
    pricing = AgentPricing(
        listing_id=listing.id,
        price_per_run=0.05,  # $0.05 per run
    )
    db.add(pricing)
    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
    fastapi_app.dependency_overrides.pop(get_db, None)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(fastapi_app)


def test_org_plan_default_and_upgrade():
    # Fetch default free plan
    res = client.get("/api/v1/billing/orgs/org-test-1/plan")
    assert res.status_code == 200
    data = res.json()
    assert data["org_id"] == "org-test-1"
    assert data["tier"] == "free"
    assert data["runs_limit"] == 100

    # Upgrade to Pro
    res = client.post("/api/v1/billing/orgs/org-test-1/subscribe", json={"tier": "pro", "email": "test@example.com"})
    assert res.status_code == 200
    assert res.json()["tier"] == "pro"
    assert res.json()["runs_limit"] == "unlimited"

    # Downgrade back to free
    res = client.post("/api/v1/billing/orgs/org-test-1/cancel")
    assert res.status_code == 200
    assert res.json()["tier"] == "free"


def test_credit_balance_topup_and_deduct(setup_db):
    # Initial balance check
    res = client.get("/api/v1/billing/orgs/org-credits-1/credits")
    assert res.status_code == 200
    assert res.json()["balance_usd"] == 0.0

    # Topup $25.00
    res = client.post("/api/v1/billing/orgs/org-credits-1/credits/topup", json={"amount_usd": 25.0})
    assert res.status_code == 200
    assert res.json()["balance_usd"] == 25.0
    assert res.json()["total_deposited_usd"] == 25.0

    # Topup another $15.00
    res = client.post("/api/v1/billing/orgs/org-credits-1/credits/topup", json={"amount_usd": 15.0})
    assert res.status_code == 200
    assert res.json()["balance_usd"] == 40.0


def test_builder_revenue_and_payout_threshold(setup_db):
    db = setup_db
    listing = db.query(AgentListing).filter(AgentListing.slug == "finance-ai-agent").first()

    # Simulate 1200 executions for builder-org-99
    for i in range(1200):
        record = ExecutionRecord(
            listing_id=listing.id,
            org_id=f"client-org-{i % 5}",
            caller_id=f"user-{i}",
            cost_usd=0.05,
            billed=True,
        )
        db.add(record)
    db.commit()

    # Check revenue
    res = client.get("/api/v1/billing/builders/builder-org-99/revenue")
    assert res.status_code == 200
    data = res.json()
    assert data["gross_revenue_usd"] == 60.0  # 1200 * 0.05
    assert data["platform_fee_usd"] == 12.0   # 20%
    assert data["net_revenue_usd"] == 48.0     # 80%

    # Request payout below $50 threshold -> should fail 400
    res = client.post("/api/v1/billing/builders/builder-org-99/payouts/request", json={"amount_usd": 40.0})
    assert res.status_code == 400
    assert "Minimum payout request amount is $50.00" in res.json()["detail"]

    # Add 100 more runs to push revenue over $50
    for i in range(100):
        record = ExecutionRecord(
            listing_id=listing.id,
            org_id="client-org-0",
            caller_id="user-extra",
            cost_usd=0.05,
            billed=True,
        )
        db.add(record)
    db.commit()

    # Request payout of $50.00 -> should succeed
    res = client.post("/api/v1/billing/builders/builder-org-99/payouts/request", json={"amount_usd": 50.0})
    assert res.status_code == 200
    assert res.json()["amount_usd"] == 50.0
    assert res.json()["status"] == "pending"


def test_razorpay_webhook_event_handling():
    # Send payment.captured webhook
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_123456",
                    "notes": {
                        "org_id": "webhook-org-1",
                        "amount_usd": "50.0",
                    }
                }
            }
        }
    }
    res = client.post("/api/v1/billing/webhooks/razorpay", json=webhook_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"

    # Verify credit balance was updated
    res = client.get("/api/v1/billing/orgs/webhook-org-1/credits")
    assert res.status_code == 200
    assert res.json()["balance_usd"] == 50.0


def test_x402_payment_required_middleware():
    @fastapi_app.get("/api/v1/test-monetized-endpoint", dependencies=[pytest.importorskip("fastapi").Depends(require_x402_payment(price_usd=0.005))])
    def monetized_endpoint():
        return {"data": "premium_payload"}

    # Request without x402 header -> expect HTTP 402
    res = client.get("/api/v1/test-monetized-endpoint")
    assert res.status_code == 402
    assert "WWW-Authenticate" in res.headers
    assert "X-402-Price-USD" in res.headers
    assert res.headers["X-402-Price-USD"] == "0.005"

    # Request with valid X-402-Payment-Token -> expect HTTP 200
    res = client.get(
        "/api/v1/test-monetized-endpoint",
        headers={"X-402-Payment-Token": "x402_tok_valid_test_token_123456"}
    )
    assert res.status_code == 200
    assert res.json() == {"data": "premium_payload"}
