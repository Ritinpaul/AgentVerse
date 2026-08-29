"""
Incidents Router — /api/v1/incidents
Report, track, and resolve security incidents against published agents.
"""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.rate_limit import mutation_limit
from app.db.session import get_db
from app.models.agent_listing import AgentListing
from app.models.trust_models import IncidentReport
from app.services.trust_engine import apply_incident_penalty

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


class IncidentCreateRequest(BaseModel):
    listing_id: int
    reporter_id: str
    severity: str            # low, medium, high, critical
    description: str


class IncidentStatusUpdate(BaseModel):
    status: str              # open, investigating, resolved, revoked
    admin_note: Optional[str] = None


@router.post("/", status_code=201)
@mutation_limit("10/minute")
def report_incident(request: Request, req: IncidentCreateRequest, db: Session = Depends(get_db)):
    listing = db.query(AgentListing).filter(AgentListing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Agent listing not found.")

    valid_severities = {"low", "medium", "high", "critical"}
    if req.severity not in valid_severities:
        raise HTTPException(status_code=422, detail=f"severity must be one of {valid_severities}.")

    # Compute penalty
    penalty = {"low": 3, "medium": 8, "high": 15, "critical": 30}.get(req.severity, 0)

    incident = IncidentReport(
        listing_id=req.listing_id,
        reporter_id=req.reporter_id,
        severity=req.severity,
        description=req.description,
        status="open",
        score_penalty=penalty,
    )
    db.add(incident)

    # Apply immediate score penalty
    listing.trust_score = apply_incident_penalty(listing.trust_score, req.severity)

    # Revoke listing if critical
    if req.severity == "critical":
        listing.status = "revoked"
        listing.verification_status = "revoked"

    db.commit()
    db.refresh(incident)

    return {
        "incident_id": incident.id,
        "listing_id": req.listing_id,
        "severity": incident.severity,
        "status": incident.status,
        "score_penalty_applied": penalty,
        "new_trust_score": listing.trust_score,
        "listing_revoked": req.severity == "critical",
    }


@router.get("/")
def list_incidents(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(IncidentReport)
    if status:
        query = query.filter(IncidentReport.status == status)
    incidents = query.order_by(IncidentReport.id.desc()).all()
    return [
        {
            "incident_id": i.id,
            "listing_id": i.listing_id,
            "reporter_id": i.reporter_id,
            "severity": i.severity,
            "status": i.status,
            "score_penalty": i.score_penalty,
            "created_at": i.created_at,
        }
        for i in incidents
    ]


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(IncidentReport).filter(IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    listing = db.query(AgentListing).filter(AgentListing.id == incident.listing_id).first()
    return {
        "incident_id": incident.id,
        "listing_id": incident.listing_id,
        "listing_slug": listing.slug if listing else None,
        "reporter_id": incident.reporter_id,
        "severity": incident.severity,
        "description": incident.description,
        "status": incident.status,
        "score_penalty": incident.score_penalty,
        "resolved_at": incident.resolved_at,
        "created_at": incident.created_at,
    }


@router.put("/{incident_id}/status")
@mutation_limit("10/minute")
def update_incident_status(request: Request, incident_id: int, req: IncidentStatusUpdate, db: Session = Depends(get_db)):
    incident = db.query(IncidentReport).filter(IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    valid_statuses = {"open", "investigating", "resolved", "revoked"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}.")

    incident.status = req.status
    incident.updated_at = datetime.now(timezone.utc)
    if req.status in ("resolved", "revoked"):
        incident.resolved_at = datetime.now(timezone.utc)

    db.commit()
    return {"incident_id": incident.id, "new_status": incident.status, "resolved_at": incident.resolved_at}
