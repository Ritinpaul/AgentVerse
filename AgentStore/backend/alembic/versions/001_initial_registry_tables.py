"""initial registry tables

Revision ID: 001_initial_registry_tables
Revises: 
Create Date: 2026-07-25 16:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_registry_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('builder_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('capabilities', sa.JSON(), nullable=True),
        sa.Column('current_version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_listings_id'), 'agent_listings', ['id'], unique=False)
    op.create_index(op.f('ix_agent_listings_slug'), 'agent_listings', ['slug'], unique=True)
    op.create_index(op.f('ix_agent_listings_name'), 'agent_listings', ['name'], unique=False)
    op.create_index(op.f('ix_agent_listings_builder_id'), 'agent_listings', ['builder_id'], unique=False)
    op.create_index(op.f('ix_agent_listings_category'), 'agent_listings', ['category'], unique=False)

    op.create_table(
        'agent_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('version_semver', sa.String(), nullable=False),
        sa.Column('agent_yaml', sa.Text(), nullable=False),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['listing_id'], ['agent_listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_versions_id'), 'agent_versions', ['id'], unique=False)
    op.create_index(op.f('ix_agent_versions_listing_id'), 'agent_versions', ['listing_id'], unique=False)
    op.create_index(op.f('ix_agent_versions_version_semver'), 'agent_versions', ['version_semver'], unique=False)

    op.create_table(
        'mcp_server_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('builder_id', sa.String(), nullable=False),
        sa.Column('transport', sa.String(), nullable=True),
        sa.Column('command', sa.String(), nullable=True),
        sa.Column('args', sa.JSON(), nullable=True),
        sa.Column('env_keys', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('current_version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mcp_server_listings_id'), 'mcp_server_listings', ['id'], unique=False)
    op.create_index(op.f('ix_mcp_server_listings_slug'), 'mcp_server_listings', ['slug'], unique=True)
    op.create_index(op.f('ix_mcp_server_listings_name'), 'mcp_server_listings', ['name'], unique=False)
    op.create_index(op.f('ix_mcp_server_listings_builder_id'), 'mcp_server_listings', ['builder_id'], unique=False)


def downgrade() -> None:
    op.drop_table('mcp_server_listings')
    op.drop_table('agent_versions')
    op.drop_table('agent_listings')
