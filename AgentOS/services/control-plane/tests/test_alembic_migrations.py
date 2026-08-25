"""
tests/test_alembic_migrations.py

Tests that Alembic can apply the initial schema migration and downgrade cleanly.
"""

import contextlib
import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config


def test_alembic_upgrade_and_downgrade():
    control_plane_dir = Path(__file__).resolve().parents[1]
    ini_path = control_plane_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Run upgrade head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(sqlite_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        assert "agent" in tables
        assert "agentversion" in tables
        assert "runrecord" in tables
        assert "releaserecord" in tables
        assert "alembic_version" in tables

        # Verify agent columns
        agent_cols = {c["name"] for c in inspector.get_columns("agent")}
        assert {"id", "name", "entrypoint", "status", "env_vars", "created_at"}.issubset(agent_cols)

        # 2. Run downgrade base
        command.downgrade(alembic_cfg, "base")

        inspector_after = inspect(engine)
        tables_after = set(inspector_after.get_table_names())
        assert "agent" not in tables_after
        assert "agentversion" not in tables_after
        assert "runrecord" not in tables_after
        assert "releaserecord" not in tables_after

        # 3. Idempotent re-upgrade
        command.upgrade(alembic_cfg, "head")
        tables_reup = set(inspect(engine).get_table_names())
        assert "agent" in tables_reup

    finally:
        engine.dispose()
        if os.path.exists(db_path):
            with contextlib.suppress(OSError):
                os.remove(db_path)
