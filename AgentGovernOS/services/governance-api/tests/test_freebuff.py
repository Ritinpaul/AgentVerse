"""Integration tests for the FreeBuff proxy router."""
from __future__ import annotations

import os
import sys

import fakeredis.aioredis as fakeredis
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Fixtures ───────────────────────────────────────────────────────────────
from jose import jwt
from main import app

from services.auth import ALGORITHM, AuthService
from services.token_budget import DAILY_LIMIT

FAKE_USER_ID = "test-user-00000000"
FAKE_TOKEN = jwt.encode({"sub": FAKE_USER_ID, "roles": ["user"]}, AuthService.get_secret_key(), algorithm=ALGORITHM)


async def fake_get_user_id(request) -> str:
    """Override the auth dependency for tests."""
    return FAKE_USER_ID


async def fake_redis_gen():
    r = fakeredis.FakeRedis(decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()


@pytest.fixture
def app_with_overrides():
    from routers.freebuff import _get_current_user_id, _get_redis
    app.dependency_overrides[_get_current_user_id] = lambda: FAKE_USER_ID
    app.dependency_overrides[_get_redis] = fake_redis_gen
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(app_with_overrides):
    async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as c:
        yield c


# ── GET /budget ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_budget_initial(client):
    resp = await client.get(
        "/api/v1/freebuff/budget",
        headers={"Authorization": f"Bearer {FAKE_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["budget"]["used"] == 0
    assert data["budget"]["remaining"] == DAILY_LIMIT
    assert data["budget"]["exceeded"] is False


# ── POST /chat — budget enforcement ────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_rejected_when_budget_exceeded(client, app_with_overrides):
    """Pre-fill the budget to the limit, then expect 429."""
    from routers.freebuff import _get_redis

    from services.token_budget import TokenBudgetService

    # Exhaust the budget via direct service call against the fake redis
    redis = fakeredis.FakeRedis(decode_responses=True)
    svc = TokenBudgetService(redis)
    await svc.commit(FAKE_USER_ID, DAILY_LIMIT + 1)

    # Override the redis dependency to use this pre-filled instance
    async def exhausted_redis():
        yield redis

    app_with_overrides.dependency_overrides[_get_redis] = exhausted_redis

    resp = await client.post(
        "/api/v1/freebuff/chat",
        json={"messages": [{"role": "user", "content": "hello"}], "model_hint": "fast"},
        headers={"Authorization": f"Bearer {FAKE_TOKEN}"},
    )
    assert resp.status_code == 429
    detail = resp.json()["detail"]
    assert detail["error"] == "daily_token_limit_exceeded"
    assert detail["limit"] == DAILY_LIMIT


@pytest.mark.asyncio
async def test_chat_missing_token_returns_401(app_with_overrides):
    """Without the auth override, missing bearer should 401."""
    from routers.freebuff import _get_current_user_id
    # Remove the override so real auth runs
    app_with_overrides.dependency_overrides.pop(_get_current_user_id, None)

    async with AsyncClient(transport=ASGITransport(app=app_with_overrides), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/freebuff/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
    assert resp.status_code == 401
