from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class AgentListing(Base):
    __tablename__ = "agent_listings"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)  # format: builder/agent-name
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    builder_id = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False, default="general")
    tags = Column(JSON, default=list)
    capabilities = Column(JSON, default=list)
    current_version = Column(String, nullable=False, default="0.1.0")
    status = Column(String, default="active")  # active, deprecated, revoked
    trust_score = Column(Float, default=100.0)

    # Phase 2 — Verification & Trust
    verification_status = Column(String, default="pending")  # pending, scanning, verified, failed, revoked
    verified_at = Column(DateTime, nullable=True)
    security_scan_results = Column(JSON, default=dict)
    compliance_badges = Column(JSON, default=list)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    versions = relationship("AgentVersion", back_populates="listing", cascade="all, delete-orphan")


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("agent_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    version_semver = Column(String, nullable=False, index=True)
    agent_yaml = Column(Text, nullable=False)
    changelog = Column(Text, default="")
    status = Column(String, default="published")  # published, retracted, under_review
    published_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    listing = relationship("AgentListing", back_populates="versions")
