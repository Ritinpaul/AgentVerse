"""
Procurement Engine — Workflow state machine, spend budget check, private catalog management.
"""
from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.procurement_models import (
    PrivateMarketplace, ProcurementRequest, DepartmentBudget
)
from app.models.agent_listing import AgentListing


WORKFLOW_STAGES = ["security_review", "policy_check", "cost_approval", "approved"]


def get_or_create_private_marketplace(org_id: str, db: Session) -> PrivateMarketplace:
    cat = db.query(PrivateMarketplace).filter(PrivateMarketplace.org_id == org_id).first()
    if not cat:
        cat = PrivateMarketplace(org_id=org_id, approved_slugs=[], restricted_slugs=[])
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat


def submit_procurement_request(
    org_id: str, requester_id: str, agent_slug: str, tier: str, justification: str, db: Session
) -> ProcurementRequest:
    listing = db.query(AgentListing).filter(AgentListing.slug == agent_slug).first()
    if not listing:
        raise ValueError(f"Agent '{agent_slug}' not found.")

    req = ProcurementRequest(
        org_id=org_id,
        requester_id=requester_id,
        agent_slug=agent_slug,
        tier=tier,
        justification=justification,
        stage="security_review",
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def advance_procurement_workflow(
    request_id: int, approver_id: str, action: str, reason: str = "", db: Session = None
) -> dict:
    """
    Advance procurement workflow state machine.
    action="approve" advances to next stage or finishes approved.
    action="reject" sets status="rejected".
    """
    req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).first()
    if not req:
        return {"error": "Procurement request not found."}

    if req.status != "pending":
        return {"error": f"Request is already {req.status}."}

    if action == "reject":
        req.status = "rejected"
        req.approver_id = approver_id
        req.rejection_reason = reason
        db.commit()
        return {"id": req.id, "status": "rejected", "stage": req.stage, "reason": reason}

    curr_idx = WORKFLOW_STAGES.index(req.stage) if req.stage in WORKFLOW_STAGES else 0

    if curr_idx < len(WORKFLOW_STAGES) - 2:
        # Move to next stage (e.g. security_review -> policy_check -> cost_approval)
        req.stage = WORKFLOW_STAGES[curr_idx + 1]
    else:
        # Final approval stage (cost_approval -> approved)
        req.stage = "approved"
        req.status = "approved"
        req.approver_id = approver_id

        # Auto-add to private catalog approved_slugs
        cat = get_or_create_private_marketplace(req.org_id, db)
        approved = list(cat.approved_slugs or [])
        if req.agent_slug not in approved:
            approved.append(req.agent_slug)
            cat.approved_slugs = approved

    db.commit()
    return {"id": req.id, "status": req.status, "stage": req.stage}


def check_department_budget(org_id: str, department: str, requested_usd: float, db: Session) -> tuple[bool, dict]:
    b = db.query(DepartmentBudget).filter(
        DepartmentBudget.org_id == org_id, DepartmentBudget.department_name == department
    ).first()

    if not b:
        b = DepartmentBudget(org_id=org_id, department_name=department, monthly_budget_usd=2000.0, current_spend_usd=0.0)
        db.add(b)
        db.commit()
        db.refresh(b)

    allowed = (b.current_spend_usd + requested_usd) <= b.monthly_budget_usd
    return allowed, {
        "org_id": org_id,
        "department": department,
        "monthly_budget_usd": b.monthly_budget_usd,
        "current_spend_usd": b.current_spend_usd,
        "requested_usd": requested_usd,
        "allowed": allowed,
    }
