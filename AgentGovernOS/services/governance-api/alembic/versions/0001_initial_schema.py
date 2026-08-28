"""Initial schema — all AgentGovern OS tables.

Creates all 9 tables for the full platform:
  - agents, agent_genes          (GENESIS)
  - decisions, trust_events      (ANCESTOR / PULSE) — TimescaleDB hypertables
  - policies                     (SENTINEL)
  - social_contracts             (CONTRACT)
  - escalation_cases             (ECLIPSE)
  - query_cache, cache_analytics (QICACHE)

Also enables the TimescaleDB extension and promotes both time-series tables
to hypertables (decisions, trust_events, cache_analytics).

Revision ID: 0001
Revises: None
Create Date: 2025-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enable TimescaleDB extension ──────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # ── Enable uuid-ossp for server-side UUID generation ─────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── GENESIS: agents ───────────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("agent_code", sa.String(20), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("crewai_role", sa.Text, nullable=False),
        sa.Column("crewai_backstory", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("trust_score", sa.Numeric(5, 4), nullable=False, server_default="0.5000"),
        sa.Column("authority_limit", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("tier", sa.String(10), nullable=False, server_default="T4"),
        sa.Column("generation", sa.Integer, nullable=False, server_default="1"),
        sa.Column("parent_agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("employed_date", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("last_review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_decisions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_escalations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_overrides", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dna_profile", postgresql.JSONB, nullable=False, server_default="'{}'"),
        sa.Column("social_contract", postgresql.JSONB, nullable=False, server_default="'{}'"),
        sa.Column("platform_bindings", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="'{}'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
    )
    op.create_index("idx_agents_status", "agents", ["status"])
    op.create_index("idx_agents_trust", "agents", ["trust_score"])
    op.create_index("idx_agents_tier", "agents", ["tier"])
    op.create_index("idx_agents_role", "agents", ["role"])

    # ── GENESIS: agent_genes ─────────────────────────────────────────────────
    op.create_table(
        "agent_genes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gene_name", sa.String(100), nullable=False),
        sa.Column("gene_type", sa.String(30), nullable=False),
        sa.Column("acquired_from", sa.String(50), nullable=True),
        sa.Column("source_agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("strength", sa.Numeric(3, 2), nullable=False, server_default="0.50"),
        sa.Column("mutation_log", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
    )
    op.create_index("idx_genes_agent", "agent_genes", ["agent_id"])
    op.create_index("idx_genes_type", "agent_genes", ["gene_type"])
    op.create_index("idx_genes_strength", "agent_genes", ["strength"])

    # ── ANCESTOR: decisions ───────────────────────────────────────────────────
    # Composite PK (id, timestamp) required for TimescaleDB hypertable partitioning.
    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dispute_id", sa.String(50), nullable=True),
        sa.Column("decision_type", sa.String(30), nullable=False),
        sa.Column("input_context", postgresql.JSONB, nullable=False),
        sa.Column("reasoning_trace", sa.Text, nullable=False),
        sa.Column("crewai_task_output", sa.Text, nullable=True),
        sa.Column("tools_used", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("delegation_chain", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("output_action", postgresql.JSONB, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("amount_involved", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'INR'"),
        sa.Column("policy_rules_applied", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("policy_violations", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("sentinel_assessment", postgresql.JSONB, nullable=True),
        sa.Column("prophecy_paths", postgresql.JSONB, nullable=True),
        sa.Column("human_override", postgresql.JSONB, nullable=True),
        sa.Column("outcome_feedback", postgresql.JSONB, nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW")),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index("idx_decisions_agent", "decisions", ["agent_id"])
    op.create_index("idx_decisions_type", "decisions", ["decision_type"])
    op.create_index("idx_decisions_time", "decisions", ["timestamp"])
    op.create_index("idx_decisions_dispute", "decisions", ["dispute_id"])
    # Promote to hypertable (partitioned by time)
    op.execute(
        "SELECT create_hypertable('decisions', 'timestamp', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )

    # ── PULSE: trust_events ───────────────────────────────────────────────────
    op.create_table(
        "trust_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("trigger_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delta", sa.Numeric(5, 4), nullable=False),
        sa.Column("previous_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("new_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("authority_change", postgresql.JSONB, nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="'{}'"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW")),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index("idx_trust_agent", "trust_events", ["agent_id"])
    op.create_index("idx_trust_time", "trust_events", ["timestamp"])
    op.execute(
        "SELECT create_hypertable('trust_events', 'timestamp', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )

    # ── SENTINEL: policies ────────────────────────────────────────────────────
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("policy_code", sa.String(50), nullable=False, unique=True),
        sa.Column("policy_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("rule_definition", postgresql.JSONB, nullable=False),
        sa.Column("applies_to_roles", postgresql.JSONB, nullable=False,
                  server_default="'[\"*\"]'"),
        sa.Column("applies_to_tiers", postgresql.JSONB, nullable=False,
                  server_default="'[\"*\"]'"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="'medium'"),
        sa.Column("action_on_violation", sa.String(30), nullable=False, server_default="'block'"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
    )
    op.create_index("idx_policies_active", "policies", ["is_active"])
    op.create_index("idx_policies_category", "policies", ["category"])

    # ── CONTRACT: social_contracts ────────────────────────────────────────────
    op.create_table(
        "social_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'active'"),
        sa.Column("rights", postgresql.JSONB, nullable=False),
        sa.Column("responsibilities", postgresql.JSONB, nullable=False),
        sa.Column("authority_bounds", postgresql.JSONB, nullable=False),
        sa.Column("career_path", postgresql.JSONB, nullable=False),
        sa.Column("review_schedule", postgresql.JSONB, nullable=False),
        sa.Column("mentor_assignments", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("performance_benchmarks", postgresql.JSONB, nullable=False),
        sa.Column("signed_by", sa.String(100), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
    )
    op.create_index("idx_contracts_agent", "social_contracts", ["agent_id"])
    op.create_index("idx_contracts_status", "social_contracts", ["status"])

    # ── ECLIPSE: escalation_cases ─────────────────────────────────────────────
    op.create_table(
        "escalation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),  # No FK — hypertable
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("escalation_reason", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False, server_default="'medium'"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("context_package", postgresql.JSONB, nullable=False),
        sa.Column("prophecy_recommendation", postgresql.JSONB, nullable=True),
        sa.Column("human_decision", postgresql.JSONB, nullable=True),
        sa.Column("resolution_time_ms", sa.Integer, nullable=True),
        sa.Column("feedback_to_agent", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_escalations_agent", "escalation_cases", ["agent_id"])
    op.create_index("idx_escalations_status", "escalation_cases", ["status"])
    op.create_index("idx_escalations_priority", "escalation_cases", ["priority"])

    # ── QICACHE: query_cache ──────────────────────────────────────────────────
    op.create_table(
        "query_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("query_normalized", sa.Text, nullable=False),
        sa.Column("query_context_hash", sa.String(64), nullable=True),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("response_metadata", postgresql.JSONB, nullable=False, server_default="'{}'"),
        sa.Column("agent_role", sa.String(50), nullable=True),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("save_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_cache_hash", "query_cache", ["query_hash"])
    op.create_index("idx_cache_context_hash", "query_cache", ["query_context_hash"])
    op.create_index("idx_cache_expires", "query_cache", ["expires_at"])
    op.create_index("idx_cache_pinned", "query_cache", ["is_pinned"])

    # ── QICACHE: cache_analytics ──────────────────────────────────────────────
    op.create_table(
        "cache_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4")),
        sa.Column("total_queries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cache_hits", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cache_misses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_saved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_saved", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("evicted_entries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW")),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index("idx_cache_analytics_time", "cache_analytics", ["timestamp"])
    op.execute(
        "SELECT create_hypertable('cache_analytics', 'timestamp', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("cache_analytics")
    op.drop_table("query_cache")
    op.drop_table("escalation_cases")
    op.drop_table("social_contracts")
    op.drop_table("policies")
    op.drop_table("trust_events")
    op.drop_table("decisions")
    op.drop_table("agent_genes")
    op.drop_table("agents")
