"""Compliance & Identity - DID, Vault, Policy Versioning

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-14 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. did_documents table
    op.create_table('did_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('did', sa.String(length=100), nullable=False),
        sa.Column('document_json', postgresql.JSONB(astext_type=sa.Text), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_did_documents_did'), 'did_documents', ['did'], unique=True)

    # 2. did_keys table
    op.create_table('did_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('did', sa.String(length=100), nullable=False),
        sa.Column('key_type', sa.String(length=20), nullable=False),
        sa.Column('public_key_multibase', sa.String(length=200), nullable=False),
        sa.Column('private_key_multibase', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['did'], ['did_documents.did'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. policy_versions table
    op.create_table('policy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text), nullable=False),
        sa.Column('diff', postgresql.JSONB(astext_type=sa.Text), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. secret_requests table
    op.create_table('secret_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_did', sa.String(length=100), nullable=False),
        sa.Column('secret_path', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_secret_requests_agent_did'), 'secret_requests', ['agent_did'], unique=False)

    # 5. Modify agents table: drop agent_code, add did
    op.add_column('agents', sa.Column('did', sa.String(length=100), nullable=True))
    
    # We must populate 'did' before making it non-nullable.
    # We will just copy 'agent_code' to 'did' temporarily, or set a dummy DID to prevent error on existing rows.
    op.execute("UPDATE agents SET did = 'did:nuuvixx:' || agent_code WHERE did IS NULL")
    
    op.alter_column('agents', 'did', nullable=False)
    op.create_index(op.f('ix_agents_did'), 'agents', ['did'], unique=True)
    
    op.drop_constraint('agents_agent_code_key', 'agents', type_='unique')
    op.drop_column('agents', 'agent_code')


def downgrade() -> None:
    # Reverse agent table modifications
    op.add_column('agents', sa.Column('agent_code', sa.String(length=20), autoincrement=False, nullable=True))
    op.execute("UPDATE agents SET agent_code = SUBSTRING(did FROM 13) WHERE agent_code IS NULL")
    op.alter_column('agents', 'agent_code', nullable=False)
    op.create_unique_constraint('agents_agent_code_key', 'agents', ['agent_code'])
    op.drop_index(op.f('ix_agents_did'), table_name='agents')
    op.drop_column('agents', 'did')

    op.drop_index(op.f('ix_secret_requests_agent_did'), table_name='secret_requests')
    op.drop_table('secret_requests')
    op.drop_table('policy_versions')
    op.drop_table('did_keys')
    op.drop_index(op.f('ix_did_documents_did'), table_name='did_documents')
    op.drop_table('did_documents')
