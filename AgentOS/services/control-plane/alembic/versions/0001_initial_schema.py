"""Initial schema for AgentOS Control Plane

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-07 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agent Table
    op.create_table(
        "agent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("entrypoint", sa.String(), nullable=False),
        sa.Column("env_vars", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="STOPPED"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_name"), "agent", ["name"], unique=False)

    # 2. AgentVersion Table
    op.create_table(
        "agentversion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False, server_default="1.0.0"),
        sa.Column("manifest_hash", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="agentstudio/v1"),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agentversion_agent_name"), "agentversion", ["agent_name"], unique=False)
    op.create_index(op.f("ix_agentversion_manifest_hash"), "agentversion", ["manifest_hash"], unique=True)

    # 3. RunRecord Table
    op.create_table(
        "runrecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("policy_verdict", sa.String(), nullable=True),
        sa.Column("policy_bundle", sa.String(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("denial_reason", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agentversion.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runrecord_agent_version_id"), "runrecord", ["agent_version_id"], unique=False)

    # 4. ReleaseRecord Table
    op.create_table(
        "releaserecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_slug", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("org_slug", sa.String(), nullable=False, server_default="nuuvixx"),
        sa.Column("version", sa.String(), nullable=False, server_default="1.0.0"),
        sa.Column("manifest_hash", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="agentstudio/v1"),
        sa.Column("status", sa.String(), nullable=False, server_default="PUBLISHED"),
        sa.Column("policy_verdict", sa.String(), nullable=False, server_default="APPROVED"),
        sa.Column("policy_bundle", sa.String(), nullable=True, server_default="nuuvixx-standard-2026.09"),
        sa.Column("signature", sa.String(), nullable=False),
        sa.Column("sbom_json", sa.JSON(), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_releaserecord_agent_slug"), "releaserecord", ["agent_slug"], unique=False)
    op.create_index(op.f("ix_releaserecord_agent_name"), "releaserecord", ["agent_name"], unique=False)
    op.create_index(op.f("ix_releaserecord_org_slug"), "releaserecord", ["org_slug"], unique=False)
    op.create_index(op.f("ix_releaserecord_version"), "releaserecord", ["version"], unique=False)
    op.create_index(op.f("ix_releaserecord_manifest_hash"), "releaserecord", ["manifest_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_releaserecord_manifest_hash"), table_name="releaserecord")
    op.drop_index(op.f("ix_releaserecord_version"), table_name="releaserecord")
    op.drop_index(op.f("ix_releaserecord_org_slug"), table_name="releaserecord")
    op.drop_index(op.f("ix_releaserecord_agent_name"), table_name="releaserecord")
    op.drop_index(op.f("ix_releaserecord_agent_slug"), table_name="releaserecord")
    op.drop_table("releaserecord")

    op.drop_index(op.f("ix_runrecord_agent_version_id"), table_name="runrecord")
    op.drop_table("runrecord")

    op.drop_index(op.f("ix_agentversion_manifest_hash"), table_name="agentversion")
    op.drop_index(op.f("ix_agentversion_agent_name"), table_name="agentversion")
    op.drop_table("agentversion")

    op.drop_index(op.f("ix_agent_name"), table_name="agent")
    op.drop_table("agent")
