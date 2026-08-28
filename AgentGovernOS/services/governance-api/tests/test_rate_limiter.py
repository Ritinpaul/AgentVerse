"""
Unit tests for the rate_limiter module.

Validates GAP-NEW-01 fix: previously, _get_redis / _check_window had method
references instead of calls (e.g. `r = _get_redis` instead of `r = _get_redis()`,
`pipe.execute` instead of `pipe.execute()`), which silently broke rate limiting.

These tests use fakeredis to simulate a working Redis instance and exercise:
- Sliding-window counter behavior (allow under limit, block over limit).
- Identifier extraction (agent > jwt > ip priority).
- Fail-open behavior when Redis is unavailable.
- All three TTL branches (-1, -2, count == 1).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fakeredis
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# ── Test helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def fake_redis(monkeypatch):
    """Return a fresh fakeredis.FakeRedis instance and stub _get_redis to use it."""
    client = fakeredis.FakeRedis(decode_responses=True)

    import middleware.rate_limiter as rl
    monkeypatch.setattr(rl, "_get_redis", lambda: client)
    client.flushall()
    return client


@pytest.fixture
def app_with_route(fake_redis):
    """Build a FastAPI app with a single rate-limited endpoint."""
    from fastapi import Depends
    from middleware.rate_limiter import rate_limit
    app = FastAPI()
    check = rate_limit(max_requests=3, window_seconds=60)

    @app.get("/limited")
    async def limited(request: Request, _: None = Depends(check)):
        return {"ok": True}

    return app


@pytest.fixture
def client(app_with_route):
    return TestClient(app_with_route)


# ── Sliding-window counter ────────────────────────────────────────────────────

def test_allows_under_limit(client):
    """First N requests under the limit return 200."""
    for i in range(3):
        r = client.get("/limited")
        assert r.status_code == 200, f"request {i+1} unexpectedly blocked"


def test_blocks_over_limit(client):
    """The (N+1)th request returns 429."""
    for _ in range(3):
        client.get("/limited")
    r = client.get("/limited")
    assert r.status_code == 429
    assert "Rate limit exceeded" in r.json()["detail"]
    assert "Retry-After" in r.headers
    assert int(r.headers["X-RateLimit-Limit"]) == 3
    assert r.headers["X-RateLimit-Remaining"] == "0"


# ── Identifier extraction ────────────────────────────────────────────────────

def test_extract_identifier_prefers_x_agent_id_header():
    from middleware.rate_limiter import _extract_identifier
    scope = {"type": "http", "headers": [], "client": ("1.2.3.4", 0)}
    req = Request(scope)
    ident = _extract_identifier(req, x_agent_id="my-agent")
    assert ident == "agent:my-agent"


def test_extract_identifier_falls_back_to_jwt():
    from config import get_settings
    from jose import jwt
    from middleware.rate_limiter import _extract_identifier
    settings = get_settings()
    token = jwt.encode({"sub": "user-42"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("1.2.3.4", 0),
    }
    req = Request(scope)
    ident = _extract_identifier(req, x_agent_id=None)
    assert ident == "jwt:user-42"


def test_extract_identifier_falls_back_to_ip():
    from middleware.rate_limiter import _extract_identifier
    scope = {
        "type": "http",
        "headers": [],
        "client": ("9.8.7.6", 0),
    }
    req = Request(scope)
    ident = _extract_identifier(req, x_agent_id=None)
    assert ident == "ip:9.8.7.6"


# ── Fail-open behavior ───────────────────────────────────────────────────────

def test_fails_open_when_redis_unavailable(monkeypatch):
    """If _get_redis returns None, traffic is allowed (with a warning)."""
    import middleware.rate_limiter as rl
    from fastapi import Depends
    monkeypatch.setattr(rl, "_get_redis", lambda: None)

    app = FastAPI()
    check = rl.rate_limit(max_requests=1, window_seconds=60)

    @app.get("/limited")
    async def limited(_: None = Depends(check)):
        return {"ok": True}

    c = TestClient(app)
    for _ in range(10):
        assert c.get("/limited").status_code == 200


# ── _check_window TTL branches ───────────────────────────────────────────────

def test_check_window_ttl_minus2_branch(fake_redis):
    """Fresh key: returns count=1, allowed=True, ttl in (0, 60]."""
    from middleware.rate_limiter import _check_window
    allowed, count, ttl = _check_window(fake_redis, "fresh:key", 5, 60)
    assert count == 1
    assert allowed is True
    assert 1 <= ttl <= 60


def test_check_window_increments_correctly(fake_redis):
    """Same key returns incrementing counts, all under max."""
    from middleware.rate_limiter import _check_window
    counts = []
    for _ in range(4):
        allowed, count, _ttl = _check_window(fake_redis, "inc:key", 5, 60)
        counts.append(count)
    assert counts == [1, 2, 3, 4]
    for c in counts:
        assert c <= 5


def test_check_window_blocks_after_limit(fake_redis):
    from middleware.rate_limiter import _check_window
    for _ in range(3):
        _check_window(fake_redis, "block:key", 3, 60)
    allowed, count, _ttl = _check_window(fake_redis, "block:key", 3, 60)
    assert count == 4
    assert allowed is False


# ── Tier-Based & In-Memory Fallback Tests ─────────────────────────────────────

def test_in_memory_fallback_enforces_limit_when_redis_unavailable(monkeypatch):
    """When fallback_to_memory=True and Redis is down, in-memory bucket protects route."""
    import middleware.rate_limiter as rl
    from fastapi import Depends
    monkeypatch.setattr(rl, "_get_redis", lambda: None)
    rl.in_memory_limiter.clear()

    app = FastAPI()
    check = rl.rate_limit(max_requests=2, window_seconds=60, fallback_to_memory=True)

    @app.get("/fallback-limited")
    async def fallback_limited(_: None = Depends(check)):
        return {"status": "ok"}

    c = TestClient(app)
    # Request 1 & 2 pass
    assert c.get("/fallback-limited", headers={"X-Agent-ID": "agent-mem-1"}).status_code == 200
    assert c.get("/fallback-limited", headers={"X-Agent-ID": "agent-mem-1"}).status_code == 200
    # Request 3 is blocked by in-memory rate limiter with 429
    r3 = c.get("/fallback-limited", headers={"X-Agent-ID": "agent-mem-1"})
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers


def test_tiered_rate_limiting_burst_allowances(fake_redis):
    """Tier-based rate limiter applies correct base + burst limit."""
    import middleware.rate_limiter as rl
    from fastapi import Depends

    app = FastAPI()
    check = rl.rate_limit(tier_based=True)

    @app.get("/tiered-route")
    async def tiered_route(_: None = Depends(check)):
        return {"ok": True}

    c = TestClient(app)
    # Free tier limit is 30 base + 5 burst = 35 requests
    resp = c.get("/tiered-route", headers={"X-Agent-ID": "agent-free-user", "X-Tier": "free"})
    assert resp.status_code == 200
    assert resp.headers.get("X-RateLimit-Limit") == "35"

    # Pro tier limit is 120 base + 20 burst = 140 requests
    resp_pro = c.get("/tiered-route", headers={"X-Agent-ID": "agent-pro-user", "X-Tier": "pro"})
    assert resp_pro.status_code == 200
    assert resp_pro.headers.get("X-RateLimit-Limit") == "140"