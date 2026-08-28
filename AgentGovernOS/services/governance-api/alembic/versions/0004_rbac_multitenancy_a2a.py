"""rbac_multitenancy_a2a

Revision ID: b77e7fbab6eb
Revises: 0003
Create Date: 2026-07-14 21:43:32.469547
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b77e7fbab6eb'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Multi-tenancy: Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('data_region', sa.String(length=20), server_default='us-east-1', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. RBAC: Roles, Permissions, UserRoles
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.UUID, nullable=False),
        sa.Column('permission_id', sa.UUID, nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    op.create_table(
        'user_roles',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('org_id', sa.UUID, nullable=False),
        sa.Column('role_id', sa.UUID, nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_roles_user_id'), 'user_roles', ['user_id'], unique=False)

    # 3. Add org_id to existing tables
    op.add_column('agents', sa.Column('org_id', sa.UUID, nullable=True))
    op.create_foreign_key(None, 'agents', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_agents_org_id'), 'agents', ['org_id'], unique=False)

    op.add_column('decisions', sa.Column('org_id', sa.UUID, nullable=True))
    op.create_foreign_key(None, 'decisions', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_decisions_org_id'), 'decisions', ['org_id'], unique=False)

    op.add_column('policies', sa.Column('org_id', sa.UUID, nullable=True))
    op.create_foreign_key(None, 'policies', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_policies_org_id'), 'policies', ['org_id'], unique=False)

    # 4. A2A: Delegation Requests & Attestations
    op.create_table(
        'delegation_requests',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('caller_did', sa.String(length=100), nullable=False),
        sa.Column('target_did', sa.String(length=100), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False),
        sa.Column('depth', sa.Integer, server_default='0', nullable=False),
        sa.Column('intent_signature', sa.Text, nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delegation_requests_caller_did'), 'delegation_requests', ['caller_did'], unique=False)
    op.create_index(op.f('ix_delegation_requests_target_did'), 'delegation_requests', ['target_did'], unique=False)

    op.create_table(
        'delegation_attestations',
        sa.Column('id', sa.UUID, nullable=False),
        sa.Column('request_id', sa.UUID, nullable=False),
        sa.Column('caller_trust_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('target_trust_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('policy_violations', postgresql.JSONB(astext_type=sa.Text), nullable=False),
        sa.Column('attestation_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['delegation_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop A2A tables
    op.drop_table('delegation_attestations')
    op.drop_index(op.f('ix_delegation_requests_target_did'), table_name='delegation_requests')
    op.drop_index(op.f('ix_delegation_requests_caller_did'), table_name='delegation_requests')
    op.drop_table('delegation_requests')

    # Drop org_id columns
    op.drop_constraint(None, 'policies', type_='foreignkey')  # type: ignore
    op.drop_index(op.f('ix_policies_org_id'), table_name='policies')
    op.drop_column('policies', 'org_id')

    op.drop_constraint(None, 'decisions', type_='foreignkey')  # type: ignore
    op.drop_index(op.f('ix_decisions_org_id'), table_name='decisions')
    op.drop_column('decisions', 'org_id')

    op.drop_constraint(None, 'agents', type_='foreignkey')  # type: ignore
    op.drop_index(op.f('ix_agents_org_id'), table_name='agents')
    op.drop_column('agents', 'org_id')

    # Drop RBAC and Multi-tenancy
    op.drop_index(op.f('ix_user_roles_user_id'), table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('organizations')
