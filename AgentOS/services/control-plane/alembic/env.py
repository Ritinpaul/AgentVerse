"""
Alembic env.py — migration environment for AgentOS Control Plane.

Supports both offline (SQL generation) and online (direct DB) modes.
DATABASE_URL env var overrides alembic.ini setting.
"""

import os
import sys
from logging.config import fileConfig

# Add control-plane root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Register all SQLModel ORM models
import app.models.agent  # noqa: F401
import app.models.version  # noqa: F401

# Alembic Config object
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override DB URL from environment if present
db_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
# Strip async drivers for Alembic sync migration runner
db_url_sync = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")
config.set_main_option("sqlalchemy.url", db_url_sync)

# Target metadata from SQLModel
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — emit SQL without a live DB connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects directly to the DB.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
