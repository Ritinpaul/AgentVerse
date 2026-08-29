"""
Phase 2 — Trust & Verification Models
SecurityScan, ComplianceBadge, BuilderProfile, IncidentReport
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, JSON, DateTime, Boolean
from app.db.base_class import Base


class SecurityScan(Base):
    """Per-scan record produced by the static ASI security scanner."""
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    scanner_version = Column(String, nullable=False, default="1.0.0")
    findings = Column(JSON, default=list)       # List of {check, severity, message, passed}
    severity = Column(String, default="none")   # none, low, medium, high, critical
    score_deduction = Column(Float, default=0.0)
    passed = Column(Boolean, default=True)
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


class ComplianceBadge(Base):
    """Builder-declared compliance certifications (SOC2, HIPAA, GDPR, ISO42001)."""
    __tablename__ = "compliance_badges"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_type = Column(String, nullable=False)   # soc2, hipaa, gdpr, iso42001
    declared_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    evidence_url = Column(String, nullable=True)
    admin_verified = Column(Boolean, default=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)


class BuilderProfile(Base):
    """Extended builder identity — KYC status for commercial publishers."""
    __tablename__ = "builder_profiles"

    id = Column(Integer, primary_key=True, index=True)
    builder_id = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    website = Column(String, nullable=True)
    github_handle = Column(String, nullable=True)
    kyc_status = Column(String, default="unverified")  # unverified, submitted, approved, rejected
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class IncidentReport(Base):
    """Vulnerability / abuse reports against published agents."""
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="low")  # low, medium, high, critical
    description = Column(Text, nullable=False)
    status = Column(String, default="open")  # open, investigating, resolved, revoked
    score_penalty = Column(Float, default=0.0)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
