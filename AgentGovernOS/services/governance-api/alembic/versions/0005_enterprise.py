"""enterprise

Revision ID: enterprise
Revises: rbac_multitenancy_a2a
Create Date: 2026-07-14 22:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'enterprise'
down_revision: str | None = 'b77e7fbab6eb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Organization: add notification_channels
    op.add_column('organizations', sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text), server_default='{}', nullable=True))
    
    # 2. Agent: add budget fields
    op.add_column('agents', sa.Column('daily_budget_usd', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))
    op.add_column('agents', sa.Column('current_spend_usd', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))
    
    # 3. Decision: add sla_deadline
    op.add_column('decisions', sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True))
    
    # 4. TokenLedger: new table
    op.create_table(
        'token_ledger',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('agent_id', sa.UUID, nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer, server_default='0', nullable=False),
        sa.Column('completion_tokens', sa.Integer, server_default='0', nullable=False),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), server_default='0.000000', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_ledger_agent_id'), 'token_ledger', ['agent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_token_ledger_agent_id'), table_name='token_ledger')
    op.drop_table('token_ledger')
    
    op.drop_column('decisions', 'sla_deadline')
    op.drop_column('agents', 'current_spend_usd')
    op.drop_column('agents', 'daily_budget_usd')
    op.drop_column('organizations', 'notification_channels')
