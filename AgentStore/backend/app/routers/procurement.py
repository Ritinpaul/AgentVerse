"""
Procurement Router — /api/v1/procurement
Private marketplace catalog, 4-step procurement request workflow, and CFO spend dashboards.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.rate_limit import mutation_limit
from app.db.session import get_db
from app.models.procurement_models import (
    ProcurementRequest, DepartmentBudget
)
from app.services.procurement_engine import (
    get_or_create_private_marketplace, submit_procurement_request,
    advance_procurement_workflow
)

router = APIRouter(prefix="/api/v1/procurement", tags=["procurement"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ProcurementSubmitRequest(BaseModel):
    org_id: str
    requester_id: str
    agent_slug: str
    tier: Optional[str] = "pro"
    justification: Optional[str] = "Required for enterprise workflow."


class WorkflowActionRequest(BaseModel):
    approver_id: str
    action: str                # approve, reject
    reason: Optional[str] = ""


class BudgetSetRequest(BaseModel):
    department: str
    monthly_budget_usd: float


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/requests", status_code=201)
@mutation_limit("10/minute")
def submit_request(request: Request, req: ProcurementSubmitRequest, db: Session = Depends(get_db)):
    """Submit an agent for enterprise procurement approval."""
    try:
        proc_req = submit_procurement_request(
            org_id=req.org_id,
            requester_id=req.requester_id,
            agent_slug=req.agent_slug,
            tier=req.tier or "pro",
            justification=req.justification or "",
            db=db,
        )
        return {
            "id": proc_req.id,
            "org_id": proc_req.org_id,
            "agent_slug": proc_req.agent_slug,
            "stage": proc_req.stage,
            "status": proc_req.status,
            "created_at": proc_req.created_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/requests")
def list_requests(org_id: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """List procurement requests for an organization."""
    query = db.query(ProcurementRequest)
    if org_id:
        query = query.filter(ProcurementRequest.org_id == org_id)
    if status:
        query = query.filter(ProcurementRequest.status == status)
    reqs = query.order_by(ProcurementRequest.id.desc()).all()
    return [
        {
            "id": r.id,
            "requester_id": r.requester_id,
            "agent_slug": r.agent_slug,
            "tier": r.tier,
            "stage": r.stage,
            "status": r.status,
            "justification": r.justification,
            "created_at": r.created_at,
        }
        for r in reqs
    ]


@router.put("/requests/{request_id}/advance")
@mutation_limit("10/minute")
def advance_workflow(request: Request, request_id: int, req: WorkflowActionRequest, db: Session = Depends(get_db)):
    """Advance or reject a procurement approval workflow."""
    res = advance_procurement_workflow(
        request_id=request_id,
        approver_id=req.approver_id,
        action=req.action,
        reason=req.reason or "",
        db=db,
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/private-catalog/{org_id}")
def get_private_catalog(org_id: str, db: Session = Depends(get_db)):
    """Get enterprise-curated private marketplace catalog."""
    cat = get_or_create_private_marketplace(org_id, db)
    return {
        "org_id": cat.org_id,
        "name": cat.name,
        "approved_slugs": cat.approved_slugs or [],
        "restricted_slugs": cat.restricted_slugs or [],
        "data_residency_region": cat.data_residency_region,
    }


@router.get("/cfo-dashboard/{org_id}")
def cfo_dashboard(org_id: str, db: Session = Depends(get_db)):
    """CFO dashboard — departmental spend, procurement requests, and budget limits."""
    budgets = db.query(DepartmentBudget).filter(DepartmentBudget.org_id == org_id).all()
    pending_count = db.query(ProcurementRequest).filter(
        ProcurementRequest.org_id == org_id, ProcurementRequest.status == "pending"
    ).count()
    approved_count = db.query(ProcurementRequest).filter(
        ProcurementRequest.org_id == org_id, ProcurementRequest.status == "approved"
    ).count()

    dept_data = [
        {
            "department": b.department_name,
            "monthly_budget_usd": b.monthly_budget_usd,
            "current_spend_usd": b.current_spend_usd,
            "utilization_pct": round((b.current_spend_usd / b.monthly_budget_usd * 100), 1) if b.monthly_budget_usd else 0,
        }
        for b in budgets
    ]

    total_budget = sum(b.monthly_budget_usd for b in budgets)
    total_spend = sum(b.current_spend_usd for b in budgets)

    return {
        "org_id": org_id,
        "total_monthly_budget_usd": total_budget,
        "total_current_spend_usd": total_spend,
        "pending_procurement_requests": pending_count,
        "approved_procurement_requests": approved_count,
        "departments": dept_data,
    }
