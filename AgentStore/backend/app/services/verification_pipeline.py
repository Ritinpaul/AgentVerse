"""
Verification Pipeline — Orchestrates security scanning + trust score recompute.
Called on publish and on manual trigger.
"""
from __future__ import annotations
import yaml
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.agent_listing import AgentListing, AgentVersion
from app.models.trust_models import SecurityScan, BuilderProfile, ComplianceBadge
from app.services.security_scanner import run_security_scan
from app.services.trust_engine import compute_trust_score


def run_verification(listing_id: int, db: Session) -> dict:
    """
    Full verification pipeline:
    1. Fetch listing + latest YAML version
    2. Parse YAML
    3. Run security scanner (ASI01-ASI10)
    4. Fetch builder profile
    5. Count active compliance badges
    6. Detect retracted versions
    7. Compute trust score
    8. Persist SecurityScan record
    9. Update listing.verification_status + trust_score
    """
    listing: AgentListing | None = db.query(AgentListing).filter(AgentListing.id == listing_id).first()
    if not listing:
        return {"error": f"Listing {listing_id} not found"}

    # Mark as scanning
    listing.verification_status = "scanning"
    db.commit()

    # Fetch latest published YAML
    latest_version: AgentVersion | None = (
        db.query(AgentVersion)
        .filter(AgentVersion.listing_id == listing_id, AgentVersion.status == "published")
        .order_by(AgentVersion.id.desc())
        .first()
    )

    parsed_yaml = {}
    schema_valid = True
    if latest_version:
        try:
            parsed_yaml = yaml.safe_load(latest_version.agent_yaml) or {}
            if not isinstance(parsed_yaml, dict):
                schema_valid = False
                parsed_yaml = {}
        except yaml.YAMLError:
            schema_valid = False
    else:
        schema_valid = False

    # Run ASI scanner
    scan_result = run_security_scan(parsed_yaml)

    # Builder profile
    builder_profile: BuilderProfile | None = (
        db.query(BuilderProfile).filter(BuilderProfile.builder_id == listing.builder_id).first()
    )

    # Compliance badges
    badge_count = db.query(ComplianceBadge).filter(
        ComplianceBadge.listing_id == listing_id,
        ComplianceBadge.revoked == False,
    ).count()

    # Retracted version check
    has_retracted = db.query(AgentVersion).filter(
        AgentVersion.listing_id == listing_id,
        AgentVersion.status == "retracted",
    ).count() > 0

    # Compute trust score
    trust_score = compute_trust_score(
        listing=listing,
        scan_result=scan_result,
        builder_profile=builder_profile,
        compliance_badge_count=badge_count,
        has_retracted_version=has_retracted,
        schema_valid=schema_valid,
    )

    # Persist scan record
    scan_record = SecurityScan(
        listing_id=listing_id,
        scanner_version="1.0.0",
        findings=scan_result.to_dict()["findings"],
        severity=scan_result.severity,
        score_deduction=scan_result.score_deduction,
        passed=scan_result.passed,
        triggered_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(scan_record)

    # Update listing
    listing.trust_score = trust_score
    listing.security_scan_results = scan_result.to_dict()
    listing.verification_status = "verified" if scan_result.passed else "failed"
    listing.verified_at = datetime.now(timezone.utc) if scan_result.passed else None
    db.commit()
    db.refresh(listing)

    return {
        "listing_id": listing_id,
        "slug": listing.slug,
        "verification_status": listing.verification_status,
        "trust_score": trust_score,
        "scan": scan_result.to_dict(),
    }
