"""
Phase 5 — Enterprise Procurement Models
PrivateMarketplace, ProcurementRequest, DepartmentBudget
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime
from app.db.base_class import Base


class PrivateMarketplace(Base):
    """Enterprise organization curated catalog."""
    __tablename__ = "private_marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False, default="Internal Agent Catalog")
    approved_slugs = Column(JSON, default=list)       # List of approved agent slugs
    restricted_slugs = Column(JSON, default=list)     # List of explicitly blocked slugs
    data_residency_region = Column(String, default="us-east-1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ProcurementRequest(Base):
    """4-stage procurement workflow for enterprise deployment."""
    __tablename__ = "procurement_requests"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, index=True, nullable=False)
    requester_id = Column(String, nullable=False)
    agent_slug = Column(String, nullable=False)
    tier = Column(String, default="pro")               # pro, enterprise
    justification = Column(Text, nullable=True)

    # Workflow stages: security_review -> policy_check -> cost_approval -> approved / rejected
    stage = Column(String, default="security_review")
    status = Column(String, default="pending")         # pending, approved, rejected
    approver_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DepartmentBudget(Base):
    """Departmental monthly spend limits and tracking."""
    __tablename__ = "department_budgets"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, index=True, nullable=False)
    department_name = Column(String, nullable=False)
    monthly_budget_usd = Column(Float, default=1000.0)
    current_spend_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
