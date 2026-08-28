"""Add audit_log table — SENTINEL runtime ledger for /governance/evaluate writes.

The audit_log table stores every evaluation decision made by the Universal
Governance Engine (POST /governance/evaluate). It is the primary data source
for the Command Center metrics dashboard (/governance/metrics).

Columns match the raw SQL INSERT in routers/governance.py exactly.

Revision ID: 0002
Revises: 0001
Create Date: 2025-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── SENTINEL: audit_log ────────────────────────────────────────────────────
    # Flat audit table written by POST /governance/evaluate. Not an ORM model —
    # governance.py writes to it via raw SQL text for speed and simplicity.
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("agent_code", sa.String(30), nullable=False),
        sa.Column("action_requested", sa.String(200), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),      # APPROVED | BLOCKED | ESCALATED
        sa.Column("risk_score", sa.String(20), nullable=True),     # LOW | MEDIUM | HIGH | CRITICAL
        sa.Column("policy_matched", sa.String(100), nullable=True),
        sa.Column("amount_requested", sa.Numeric(15, 2), nullable=True),
        sa.Column("agent_source", sa.String(50), nullable=True),   # crewai | langchain | openai …
        sa.Column("calling_system", sa.String(100), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW")),
    )
    op.create_index("idx_audit_log_verdict", "audit_log", ["verdict"])
    op.create_index("idx_audit_log_agent_code", "audit_log", ["agent_code"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("idx_audit_log_risk_score", "audit_log", ["risk_score"])
    op.create_index("idx_audit_log_action", "audit_log", ["action_requested"])


def downgrade() -> None:
    op.drop_table("audit_log")
