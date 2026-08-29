"""
Phase 4 — Composability Models
AgentComposition, CompositionDependency
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class AgentComposition(Base):
    """Multi-agent pipeline / composition definition."""
    __tablename__ = "agent_compositions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)   # format: builder/composition-name
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    builder_id = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False, default="pipeline")
    version = Column(String, nullable=False, default="1.0.0")

    # Workflow steps structure: list of {step_id, agent_slug, version_constraint, depends_on: []}
    steps = Column(JSON, default=list)

    # Generated lockfile contents (agentstore.lock.json)
    version_lockfile = Column(JSON, default=dict)

    # Policy validation status
    policy_status = Column(String, default="valid")  # valid, policy_clash, unverified
    policy_clashes = Column(JSON, default=list)      # List of detected policy violations

    status = Column(String, default="active")        # active, deprecated, revoked
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    dependencies = relationship("CompositionDependency", back_populates="composition", cascade="all, delete-orphan")


class CompositionDependency(Base):
    """Dependency mapping for compositions and listings."""
    __tablename__ = "composition_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    composition_id = Column(Integer, ForeignKey("agent_compositions.id", ondelete="CASCADE"), nullable=False, index=True)
    dep_type = Column(String, nullable=False)  # agent, mcp_server, sub_pipeline
    target_slug = Column(String, nullable=False)
    version_constraint = Column(String, default=">=0.1.0")
    pinned_version = Column(String, nullable=True)

    composition = relationship("AgentComposition", back_populates="dependencies")
