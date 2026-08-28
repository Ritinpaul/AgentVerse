"""
Pytest configuration and shared fixtures for AgentGovern OS tests.

Fixtures:
    - qicache_engine: QICACHE engine with in-memory mock Redis
    - cache_settings: Default QICacheSettings
    - mock_redis: fakeredis instance
    - api_client: FastAPI test client
    - db_engine / db_session: In-memory SQLite for fast tests
"""

import pytest
import sys
import os
import asyncio
import importlib.util
from pathlib import Path

# ── Add service roots to path ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREWAI_ENGINE = os.path.join(ROOT, "services", "crewai-engine")
GOVERNANCE_API = os.path.join(ROOT, "services", "governance-api")
SAP_BTP_ADAPTER = os.path.join(ROOT, "services", "sap-btp-adapter")

for path in (SAP_BTP_ADAPTER, CREWAI_ENGINE, GOVERNANCE_API):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)


# ──────────────────────────────────────────────
# Mock Redis using fakeredis (no real Redis needed)
# ──────────────────────────────────────────────
@pytest.fixture
def mock_redis():
    """In-memory Redis mock — no real Redis server required."""
    try:
        import fakeredis
        return fakeredis.FakeRedis()
    except ImportError:
        pytest.skip("fakeredis not installed — run: pip install fakeredis")


# ──────────────────────────────────────────────
# QICACHE Engine
# ──────────────────────────────────────────────
@pytest.fixture
def qicache_engine(mock_redis):
    """QICACHE engine wired up to fake Redis, no DB (unit test mode)."""
    from cache.qicache_engine import QICacheEngine
    return QICacheEngine(redis_client=mock_redis, db_session=None)


@pytest.fixture
def cache_settings():
    from cache.qicache_engine import QICacheSettings
    return QICacheSettings(cache_enabled=True, save_enabled=True, bypass=False, ttl_days=3)


# ──────────────────────────────────────────────
# FastAPI Test Client
# ──────────────────────────────────────────────
@pytest.fixture
def api_client():
    """FastAPI test client using SQLite test DB."""
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_gov.db"
    os.environ["APP_ENV"] = "development"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    try:
        from config import get_settings
        get_settings.cache_clear()
    except Exception:
        pass

    import database
    import models
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    database.engine = create_async_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    database.async_session = async_sessionmaker(database.engine, class_=AsyncSession, expire_on_commit=False)
    try:
        asyncio.run(database.init_db())
    except Exception:
        pass

    import main
    return TestClient(main.app)
