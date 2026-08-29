"""
Trust Score Engine — Weighted composite score (0-100).

Weights:
  Security scan result      30%  (max 30 pts)
  Schema validity           25%  (pass/fail)
  Builder KYC status        15%  (unverified=0, submitted=8, approved=15)
  Active compliance badges  10%  (up to 10 pts)
  Version stability         10%  (no retracted versions = full pts)
  Listing completeness      10%  (description + tags + capabilities)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.security_scanner import ScanResult


KYC_SCORES = {
    "unverified": 0,
    "submitted": 8,
    "approved": 15,
    "rejected": 0,
}

INCIDENT_SEVERITY_PENALTY = {
    "low": 3,
    "medium": 8,
    "high": 15,
    "critical": 30,
}


def compute_trust_score(
    listing,
    scan_result: "ScanResult",
    builder_profile=None,
    compliance_badge_count: int = 0,
    has_retracted_version: bool = False,
    schema_valid: bool = True,
) -> float:
    """
    Compute a 0-100 trust score based on weighted criteria.
    Returns the final score (floored at 0).
    """
    score = 0.0

    # 1. Security scan (30 pts max)
    security_pts = max(0.0, 30.0 - scan_result.score_deduction)
    score += security_pts

    # 2. Schema validity (25 pts)
    score += 25.0 if schema_valid else 0.0

    # 3. Builder KYC status (15 pts max)
    kyc_status = "unverified"
    if builder_profile:
        kyc_status = getattr(builder_profile, "kyc_status", "unverified")
    score += KYC_SCORES.get(kyc_status, 0)

    # 4. Compliance badges (10 pts max, 2.5 per badge, max 4 badges)
    badge_pts = min(compliance_badge_count * 2.5, 10.0)
    score += badge_pts

    # 5. Version stability (10 pts — deduct if retracted versions exist)
    score += 0.0 if has_retracted_version else 10.0

    # 6. Listing completeness (10 pts)
    completeness_pts = 0.0
    if hasattr(listing, "description") and listing.description and len(listing.description) >= 20:
        completeness_pts += 4.0
    if hasattr(listing, "tags") and listing.tags and len(listing.tags) > 0:
        completeness_pts += 3.0
    if hasattr(listing, "capabilities") and listing.capabilities and len(listing.capabilities) > 0:
        completeness_pts += 3.0
    score += completeness_pts

    return round(max(0.0, min(score, 100.0)), 2)


def apply_incident_penalty(current_score: float, severity: str) -> float:
    """Reduce trust score on incident report."""
    penalty = INCIDENT_SEVERITY_PENALTY.get(severity, 0)
    return round(max(0.0, current_score - penalty), 2)
