"""SQLAlchemy ORM models for all AgentGovern OS modules."""

import uuid
from datetime import datetime
from decimal import Decimal

from database import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym


# ============================================================
# MULTI-TENANCY & RBAC MODULE
# ============================================================
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), default="nuuvixx", index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_region: Mapped[str] = mapped_column(String(20), default="us-east-1")
    notification_channels: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Usually an OIDC sub
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


# ============================================================
# GENESIS MODULE: Agent Identity & DNA Registry
# ============================================================
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    did: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    agent_code = synonym("did")
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    crewai_role: Mapped[str] = mapped_column(Text, nullable=False)
    crewai_backstory: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    trust_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.5000"))
    authority_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    tier: Mapped[str] = mapped_column(String(10), default="T4")
    generation: Mapped[int] = mapped_column(Integer, default=1)
    parent_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    employed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_decisions: Mapped[int] = mapped_column(Integer, default=0)
    total_escalations: Mapped[int] = mapped_column(Integer, default=0)
    total_overrides: Mapped[int] = mapped_column(Integer, default=0)
    dna_profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    social_contract: Mapped[dict] = mapped_column(JSONB, default=dict)
    platform_bindings: Mapped[list] = mapped_column(JSONB, default=list)
    daily_budget_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    genes: Mapped[list["AgentGene"]] = relationship(back_populates="agent", cascade="all, delete-orphan", foreign_keys="[AgentGene.agent_id]")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="agent")
    trust_events: Mapped[list["TrustEvent"]] = relationship(back_populates="agent")
    contracts: Mapped[list["SocialContract"]] = relationship(back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agents_status", "status"),
        Index("idx_agents_trust", "trust_score"),
        Index("idx_agents_tier", "tier"),
        Index("idx_agents_role", "role"),
    )


class TokenLedger(Base):
    __tablename__ = "token_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentGene(Base):
    __tablename__ = "agent_genes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    gene_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gene_type: Mapped[str] = mapped_column(String(30), nullable=False)
    acquired_from: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    strength: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.50"))
    mutation_log: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="genes", foreign_keys=[agent_id])


class DIDDocument(Base):
    __tablename__ = "did_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    did: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    document_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DIDKey(Base):
    __tablename__ = "did_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    did: Mapped[str] = mapped_column(String(100), ForeignKey("did_documents.did", ondelete="CASCADE"), nullable=False)
    key_type: Mapped[str] = mapped_column(String(20), default="Ed25519VerificationKey2020")
    public_key_multibase: Mapped[str] = mapped_column(String(200), nullable=False)
    private_key_multibase: Mapped[str | None] = mapped_column(String(200), nullable=True) # Usually stored in Vault, but optional here
    status: Mapped[str] = mapped_column(String(20), default="active") # active, revoked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# ============================================================
# ANCESTOR MODULE: Immutable Decision Ledger
# ============================================================
class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dispute_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    input_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning_trace: Mapped[str] = mapped_column(Text, nullable=False)
    crewai_task_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_used: Mapped[list] = mapped_column(JSONB, default=list)
    delegation_chain: Mapped[list] = mapped_column(JSONB, default=list)
    output_action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    amount_involved: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    policy_rules_applied: Mapped[list] = mapped_column(JSONB, default=list)
    policy_violations: Mapped[list] = mapped_column(JSONB, default=list)
    sentinel_assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prophecy_paths: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    human_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="decisions")

    __table_args__ = (
        Index("idx_decisions_agent", "agent_id"),
        Index("idx_decisions_type", "decision_type"),
        Index("idx_decisions_time", "timestamp"),
    )


# ============================================================
# PULSE MODULE: Trust Events
# ============================================================
class TrustEvent(Base):
    __tablename__ = "trust_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Plain UUID — no FK since decisions is a TimescaleDB hypertable with composite PK
    trigger_decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    delta: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    previous_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    new_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    authority_change: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="trust_events")

    __table_args__ = (
        Index("idx_trust_agent", "agent_id"),
    )


# ============================================================
# SENTINEL MODULE: Policies
# ============================================================
class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    policy_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    policy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    applies_to_roles: Mapped[list] = mapped_column(JSONB, default=lambda: ["*"])
    applies_to_tiers: Mapped[list] = mapped_column(JSONB, default=lambda: ["*"])
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    action_on_violation: Mapped[str] = mapped_column(String(30), default="block")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ============================================================
# CONTRACT MODULE: Social Contracts
# ============================================================
class SocialContract(Base):
    __tablename__ = "social_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active")
    rights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    responsibilities: Mapped[dict] = mapped_column(JSONB, nullable=False)
    authority_bounds: Mapped[dict] = mapped_column(JSONB, nullable=False)
    career_path: Mapped[dict] = mapped_column(JSONB, nullable=False)
    review_schedule: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mentor_assignments: Mapped[list] = mapped_column(JSONB, default=list)
    performance_benchmarks: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="contracts")


# ============================================================
# ECLIPSE MODULE: Escalation Cases
# ============================================================
class EscalationCase(Base):
    __tablename__ = "escalation_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Plain UUID — no FK since decisions is a TimescaleDB hypertable with composite PK
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    escalation_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_package: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prophecy_recommendation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    human_decision: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_to_agent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# QICACHE MODULE: Query Intelligence Cache
# ============================================================
class QueryCache(Base):
    __tablename__ = "query_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    query_context_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    save_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CacheAnalytics(Base):
    __tablename__ = "cache_analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0)
    tokens_saved: Mapped[int] = mapped_column(Integer, default=0)
    cost_saved: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0"))
    evicted_entries: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )


# ============================================================
# VAULT MODULE: Secrets Request Audit
# ============================================================
class SecretRequest(Base):
    __tablename__ = "secret_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_did: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    secret_path: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="granted")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ============================================================
# PROTOCOL MODULE: A2A Interactions
# ============================================================
class DelegationRequest(Base):
    __tablename__ = "delegation_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caller_did: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_did: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    intent_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DelegationAttestation(Base):
    __tablename__ = "delegation_attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("delegation_requests.id", ondelete="CASCADE"), nullable=False)
    caller_trust_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    target_trust_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    policy_violations: Mapped[list] = mapped_column(JSONB, default=list)
    attestation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


