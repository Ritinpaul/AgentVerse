"""
Phase 5 Tests — Enterprise Procurement Workflow & Budget Checks
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base

from app.models.agent_listing import AgentListing
from app.services.procurement_engine import (
    submit_procurement_request, advance_procurement_workflow,
    check_department_budget, get_or_create_private_marketplace
)


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
def agent_listing(db):
    a = AgentListing(
        slug="acme/sales-assistant",
        name="sales-assistant",
        description="Enterprise sales assistant agent.",
        builder_id="acme",
    )
    db.add(a)
    db.commit()
    return a


def test_procurement_request_submission(db, agent_listing):
    req = submit_procurement_request(
        org_id="corp-bank",
        requester_id="john.doe",
        agent_slug="acme/sales-assistant",
        tier="pro",
        justification="Automate lead qualification",
        db=db,
    )
    assert req.id is not None
    assert req.stage == "security_review"
    assert req.status == "pending"


def test_4_stage_procurement_workflow(db, agent_listing):
    req = submit_procurement_request(
        org_id="corp-bank",
        requester_id="john.doe",
        agent_slug="acme/sales-assistant",
        tier="pro",
        justification="Automate lead qualification",
        db=db,
    )

    # 1. Advance from security_review -> policy_check
    res1 = advance_procurement_workflow(req.id, "sec-admin", "approve", db=db)
    assert res1["stage"] == "policy_check"
    assert res1["status"] == "pending"

    # 2. Advance from policy_check -> cost_approval
    res2 = advance_procurement_workflow(req.id, "policy-admin", "approve", db=db)
    assert res2["stage"] == "cost_approval"
    assert res2["status"] == "pending"

    # 3. Advance from cost_approval -> approved
    res3 = advance_procurement_workflow(req.id, "cfo", "approve", db=db)
    assert res3["stage"] == "approved"
    assert res3["status"] == "approved"

    # Check auto-added to private catalog
    cat = get_or_create_private_marketplace("corp-bank", db)
    assert "acme/sales-assistant" in cat.approved_slugs


def test_procurement_rejection(db, agent_listing):
    req = submit_procurement_request(
        org_id="corp-bank",
        requester_id="john.doe",
        agent_slug="acme/sales-assistant",
        tier="pro",
        justification="Test",
        db=db,
    )
    res = advance_procurement_workflow(req.id, "sec-admin", "reject", reason="Failed data residency check", db=db)
    assert res["status"] == "rejected"
    assert res["reason"] == "Failed data residency check"


def test_department_budget_check(db):
    allowed, b_info = check_department_budget("corp-bank", "sales", 500.0, db)
    assert allowed is True

    # Exceed limit
    allowed_over, _ = check_department_budget("corp-bank", "sales", 3000.0, db)
    assert allowed_over is False
