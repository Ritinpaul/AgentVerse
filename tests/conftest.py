"""
Shared Pytest fixtures for AgentsEcosystem (GAP-NEW-04).
"""
import os
import pytest
import fakeredis


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Ensure tests run in 'test' APP_ENV by default."""
    os.environ["APP_ENV"] = "test"
    yield


@pytest.fixture
def fakeredis_client():
    """Return an isolated FakeRedis client instance with automatic cleanup."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset SlowAPI rate limiter storage between tests so test suites can run without hit limits."""
    try:
        from app.core.rate_limit import mutation_limiter
        if hasattr(mutation_limiter, "_storage") and hasattr(mutation_limiter._storage, "storage"):
            mutation_limiter._storage.storage.clear()
        if hasattr(mutation_limiter, "storage") and hasattr(mutation_limiter.storage, "storage"):
            mutation_limiter.storage.storage.clear()
        mutation_limiter.reset()
    except Exception:
        pass
    yield
