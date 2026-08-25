"""
app/models/version.py

SQLModel definitions for immutable AgentVersion and RunRecord models.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class AgentVersionBase(SQLModel):
    agent_name: str = Field(index=True)
    version: str = Field(default="1.0.0")
    manifest_hash: str = Field(index=True, unique=True)  # "sha256:..."
    schema_version: str = Field(default="agentstudio/v1")
    manifest_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AgentVersion(AgentVersionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunRecordBase(SQLModel):
    agent_version_id: uuid.UUID = Field(foreign_key="agentversion.id", index=True)
    status: str = Field(
        default="QUEUED"
    )  # QUEUED|VALIDATING|POLICY_CHECK|SCHEDULING|SANDBOX_PROVISIONING|RUNNING|COMPLETED|FAILED|CANCELLED|BLOCKED|ESCALATED
    policy_verdict: str | None = None  # ALLOW|DENY|ESCALATE
    policy_bundle: str | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None
    denial_reason: str | None = None


class RunRecord(RunRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ReleaseRecordBase(SQLModel):
    agent_slug: str = Field(index=True)  # "org_slug/agent_name"
    agent_name: str = Field(index=True)
    org_slug: str = Field(default="nuuvixx", index=True)
    version: str = Field(default="1.0.0", index=True)
    manifest_hash: str = Field(index=True)  # "sha256:..."
    schema_version: str = Field(default="agentstudio/v1")
    status: str = Field(default="PUBLISHED")  # PUBLISHED, DEPRECATED, REVOKED
    policy_verdict: str = Field(default="APPROVED")
    policy_bundle: str | None = "nuuvixx-standard-2026.09"
    signature: str = Field(..., description="Digital signature of (agent_slug:version:manifest_hash)")
    sbom_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    manifest_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class ReleaseRecord(ReleaseRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    published_at: datetime = Field(default_factory=datetime.utcnow)
