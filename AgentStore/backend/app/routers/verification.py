"""
Verification Router — /api/v1/verification
Security scans, compliance badges, builder profiles.
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
from app.models.trust_models import SecurityScan, ComplianceBadge, BuilderProfile
from app.services.verification_pipeline import run_verification

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class BadgeDeclareRequest(BaseModel):
    badge_type: str         # soc2, hipaa, gdpr, iso42001
    evidence_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class BuilderProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    website: Optional[str] = None
    github_handle: Optional[str] = None
    kyc_status: Optional[str] = None  # submitted (builder triggers), approved/rejected (admin)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/agents/{builder}/{agent}/scan/trigger")
@mutation_limit("5/minute")
def trigger_scan(request: Request, builder: str, agent: str, db: Session = Depends(get_db)):
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")
    result = run_verification(listing.id, db)
    return result


@router.get("/agents/{builder}/{agent}/scan")
def get_latest_scan(builder: str, agent: str, db: Session = Depends(get_db)):
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")
    scan = (
        db.query(SecurityScan)
        .filter(SecurityScan.listing_id == listing.id)
        .order_by(SecurityScan.id.desc())
        .first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="No scan results found. Trigger a scan first.")
    return {
        "listing_id": listing.id,
        "slug": slug,
        "trust_score": listing.trust_score,
        "verification_status": listing.verification_status,
        "verified_at": listing.verified_at,
        "scanner_version": scan.scanner_version,
        "passed": scan.passed,
        "severity": scan.severity,
        "score_deduction": scan.score_deduction,
        "findings": scan.findings,
        "completed_at": scan.completed_at,
    }


@router.get("/agents/{builder}/{agent}/badges")
def list_badges(builder: str, agent: str, db: Session = Depends(get_db)):
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")
    badges = db.query(ComplianceBadge).filter(
        ComplianceBadge.listing_id == listing.id,
        ComplianceBadge.revoked == False,
    ).all()
    return [
        {
            "id": b.id,
            "badge_type": b.badge_type,
            "declared_at": b.declared_at,
            "expires_at": b.expires_at,
            "evidence_url": b.evidence_url,
            "admin_verified": b.admin_verified,
        }
        for b in badges
    ]


@router.post("/agents/{builder}/{agent}/badges", status_code=201)
@mutation_limit("10/minute")
def declare_badge(request: Request, builder: str, agent: str, req: BadgeDeclareRequest, db: Session = Depends(get_db)):
    slug = f"{builder}/{agent}"
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found.")

    valid_types = {"soc2", "hipaa", "gdpr", "iso42001"}
    if req.badge_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"badge_type must be one of {valid_types}.")

    badge = ComplianceBadge(
        listing_id=listing.id,
        badge_type=req.badge_type,
        evidence_url=req.evidence_url,
        expires_at=req.expires_at,
        admin_verified=False,
        revoked=False,
    )
    db.add(badge)
    db.commit()
    db.refresh(badge)
    return {"id": badge.id, "badge_type": badge.badge_type, "status": "declared_pending_review"}


@router.get("/builders/{builder_id}/profile")
def get_builder_profile(builder_id: str, db: Session = Depends(get_db)):
    profile = db.query(BuilderProfile).filter(BuilderProfile.builder_id == builder_id).first()
    if not profile:
        # Return empty profile rather than 404
        return {"builder_id": builder_id, "kyc_status": "unverified", "display_name": None}
    return {
        "builder_id": profile.builder_id,
        "display_name": profile.display_name,
        "website": profile.website,
        "github_handle": profile.github_handle,
        "kyc_status": profile.kyc_status,
        "kyc_submitted_at": profile.kyc_submitted_at,
        "kyc_approved_at": profile.kyc_approved_at,
    }


@router.put("/builders/{builder_id}/profile")
@mutation_limit("10/minute")
def update_builder_profile(request: Request, builder_id: str, req: BuilderProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(BuilderProfile).filter(BuilderProfile.builder_id == builder_id).first()
    if not profile:
        profile = BuilderProfile(builder_id=builder_id)
        db.add(profile)

    if req.display_name is not None:
        profile.display_name = req.display_name
    if req.website is not None:
        profile.website = req.website
    if req.github_handle is not None:
        profile.github_handle = req.github_handle
    if req.kyc_status == "submitted" and profile.kyc_status == "unverified":
        profile.kyc_status = "submitted"
        profile.kyc_submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)
    return {"builder_id": profile.builder_id, "kyc_status": profile.kyc_status, "updated": True}
