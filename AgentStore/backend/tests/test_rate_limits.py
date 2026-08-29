"""
Unit tests for SlowAPI per-route mutation rate limiting (GAP-NEW-02).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.base_class import Base
from app.db.session import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(fastapi_app)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    Base.metadata.create_all(bind=engine)
    import app.db.session
    monkeypatch.setattr(app.db.session, "SessionLocal", TestingSessionLocal)
    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    fastapi_app.dependency_overrides.pop(get_db, None)


def test_rate_limit_policy_resolution():
    from app.core.rate_limit import limit_for, WRITE_LIMITS
    assert limit_for("publish_agent") == "5/minute"
    assert limit_for("settle_payment") == "10/minute"
    assert limit_for("unknown_route") == WRITE_LIMITS["default_write"]


def test_slowapi_rate_limiter_active_when_enabled():
    from app.core.rate_limit import mutation_limiter
    mutation_limiter.enabled = True
    try:
        # Request trigger_scan endpoint 6 times with 5/minute limit
        for i in range(5):
            res = client.post("/api/v1/verification/agents/testbuilder/testagent/scan/trigger")
            # 404 or 200 means request passed rate limiter
            assert res.status_code != 429
        
        # 6th request must trigger 429
        res = client.post("/api/v1/verification/agents/testbuilder/testagent/scan/trigger")
        assert res.status_code == 429
    finally:
        mutation_limiter.enabled = False
