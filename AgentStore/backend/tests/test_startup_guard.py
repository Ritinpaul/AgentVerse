"""
Unit tests for production startup guard (GAP-NEW-03).
"""
import pytest
from app.core.startup_guard import refuse_sqlite_in_production


def test_refuses_sqlite_in_production():
    with pytest.raises(RuntimeError) as exc_info:
        refuse_sqlite_in_production("sqlite:///./agentstore.db", "production")
    assert "APP_ENV=production but DATABASE_URL points to SQLite" in str(exc_info.value)


def test_allows_postgres_in_production():
    # Should not raise
    refuse_sqlite_in_production("postgresql+asyncpg://user:pass@localhost:5432/db", "production")


def test_allows_sqlite_in_development():
    # Should not raise
    refuse_sqlite_in_production("sqlite:///./agentstore.db", "development")
