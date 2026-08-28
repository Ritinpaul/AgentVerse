"""
Tests: QICACHE Router — routers/cache.py

Covers all 8 endpoints:
  POST   /api/v1/cache/query              — cache check (bypass, disable, miss, hit)
  POST   /api/v1/cache/store              — store LLM response
  POST   /api/v1/cache/regenerate/{hash}  — invalidate entry
  DELETE /api/v1/cache/{hash}             — manual delete
  GET    /api/v1/cache/analytics          — performance metrics
  POST   /api/v1/cache/settings           — per-agent toggle
  GET    /api/v1/cache/settings/{agent_id} — read per-agent settings
  POST   /api/v1/cache/evict-expired      — TTL purge

Strategy:
  - Create a minimal FastAPI app per test with dependency override for get_db.
  - Redis is unavailable in tests → _get_redis returns None gracefully.
  - Per-agent _settings_cache (module-level dict) is cleared between tests.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

# ── Path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "governance-api"))

# Set env vars BEFORE any imports from governance-api (settings loaded on first import)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_cache_router.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_ENV", "test")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_settings_cache:
    """Reset the module-level _settings_cache between tests to avoid state leakage."""
    import routers.cache as cache_mod
    cache_mod._settings_cache.clear
    yield
    cache_mod._settings_cache.clear


def _make_empty_db:
    """Async DB mock that returns no rows and accepts writes silently."""
    mock_db = AsyncMock
    mock_db.flush = AsyncMock
    mock_db.add = MagicMock
    result = MagicMock
    result.scalar_one_or_none = MagicMock(return_value=None)
    result.scalar = MagicMock(return_value=0)
    result.rowcount = 0
    result.all = MagicMock(return_value=[])
    mock_db.execute = AsyncMock(return_value=result)
    return mock_db


def _make_hit_entry(
    response_text="cached answer",
    tokens_consumed=200,
    hit_count=3,
):
    """Fake QueryCache ORM row with realistic attributes."""
    entry = MagicMock
    entry.response_text = response_text
    entry.response_metadata = {"tokens_consumed": tokens_consumed}
    entry.hit_count = hit_count
    entry.last_accessed_at = datetime.now(timezone.utc)
    entry.expires_at = datetime.now(timezone.utc) + timedelta(days=3)
    return entry


def _build_client(mock_db=None, no_redis=True):
    """
    Build a TestClient with only the cache router mounted.
    Optionally inject a mock DB via FastAPI dependency_overrides.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.cache import router
    from database import get_db

    app = FastAPI
    app.include_router(router)

    if mock_db is not None:
        async def override_db:
            yield mock_db

        app.dependency_overrides[get_db] = override_db

    if no_redis:
        # Patch Redis at the module level so _get_redis always returns None
        # (no real Redis server in tests)
        pass  # _get_redis already returns None when ping fails — handled below

    return TestClient(app, raise_server_exceptions=True)


# ── POST /api/v1/cache/query ──────────────────────────────────────────────────

class TestQueryEndpoint:

    def test_bypass_returns_miss(self):
        """bypass=True skips cache lookup and returns hit=False, source=llm."""
        db = _make_empty_db
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "check invoice PO-999",
                "agent_role": "resolver",
                "bypass": True,
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["hit"] is False
        assert body["source"] == "llm"
        assert len(body["query_hash"]) == 64

    def test_cache_enabled_false_returns_miss(self):
        """cache_enabled=False short-circuits to miss."""
        db = _make_empty_db
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "check invoice",
                "agent_role": "resolver",
                "cache_enabled": False,
            })
        assert resp.status_code == 200
        assert resp.json()["hit"] is False

    def test_qicache_globally_disabled_returns_miss(self):
        """When settings.qicache_enabled=False, always return miss."""
        db = _make_empty_db
        import routers.cache as cache_mod
        original = cache_mod.settings.qicache_enabled
        try:
            cache_mod.settings.qicache_enabled = False
            with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
                client = _build_client(mock_db=db)
                resp = client.post("/api/v1/cache/query", json={
                    "query_text": "check invoice",
                    "agent_role": "resolver",
                })
            assert resp.status_code == 200
            assert resp.json()["hit"] is False
        finally:
            cache_mod.settings.qicache_enabled = original

    def test_db_cache_miss_returns_miss(self):
        """No matching DB row → hit=False, source=llm."""
        db = _make_empty_db
        # scalar_one_or_none returns None (miss)
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "what is the contract value for ACM-007",
                "agent_role": "evidence_collector",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["hit"] is False
        assert body["source"] == "llm"

    def test_db_cache_hit_returns_response(self):
        """Matching DB row → hit=True with correct response and tokens_saved."""
        entry = _make_hit_entry("Settlement approved for $25k", tokens_consumed=450)
        db = _make_empty_db
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=entry)

        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "settle dispute for ACM-007",
                "agent_role": "resolver",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["hit"] is True
        assert body["response"] == "Settlement approved for $25k"
        assert body["source"] == "postgres_warm"
        assert body["tokens_saved"] == 450

    def test_db_hit_no_metadata_tokens_zero(self):
        """Hit with response_metadata=None returns tokens_saved=0."""
        entry = _make_hit_entry
        entry.response_metadata = None
        db = _make_empty_db
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=entry)

        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "query with no meta",
                "agent_role": "resolver",
            })
        assert resp.status_code == 200
        assert resp.json()["tokens_saved"] == 0

    def test_agent_override_disabled_returns_miss(self):
        """Per-agent override with cache_enabled=False forces miss even if DB would hit."""
        import routers.cache as cache_mod
        # Pre-populate the in-process settings cache to disable caching for this agent
        cache_mod._settings_cache["risk_eval"] = {"cache_enabled": False}

        entry = _make_hit_entry("should not be returned")
        db = _make_empty_db
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=entry)

        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post("/api/v1/cache/query", json={
                "query_text": "risk score for customer",
                "agent_role": "risk_eval",
            })
        assert resp.status_code == 200
        assert resp.json()["hit"] is False


# ── POST /api/v1/cache/store ──────────────────────────────────────────────────

class TestStoreEndpoint:

    def test_store_success(self):
        """Valid request stores entry and returns stored=True."""
        db = _make_empty_db
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post(
                "/api/v1/cache/store",
                params={
                    "query_hash": "abc123def456",
                    "query_text": "what is the outstanding balance",
                    "response_text": "Balance is $12,500, last payment on 2026-01-15",
                    "agent_role": "evidence_collector",
                    "save_enabled": True,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stored"] is True
        assert body["query_hash"] == "abc123def456"

    def test_store_save_disabled_returns_false(self):
        """save_enabled=False returns stored=False without touching DB."""
        db = _make_empty_db
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post(
                "/api/v1/cache/store",
                params={
                    "query_hash": "nohash",
                    "query_text": "ephemeral query",
                    "response_text": "ephemeral response",
                    "save_enabled": False,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["stored"] is False

    def test_store_qicache_globally_disabled(self):
        """settings.qicache_enabled=False prevents storage."""
        db = _make_empty_db
        import routers.cache as cache_mod
        original = cache_mod.settings.qicache_enabled
        try:
            cache_mod.settings.qicache_enabled = False
            with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
                client = _build_client(mock_db=db)
                resp = client.post(
                    "/api/v1/cache/store",
                    params={
                        "query_hash": "gh789",
                        "query_text": "some query",
                        "response_text": "some response",
                        "save_enabled": True,
                    },
                )
            assert resp.status_code == 200
            assert resp.json()["stored"] is False
        finally:
            cache_mod.settings.qicache_enabled = original

    def test_store_agent_save_disabled(self):
        """Per-agent save_enabled=False prevents storage for that agent."""
        import routers.cache as cache_mod
        cache_mod._settings_cache["notary_bot"] = {"save_enabled": False}

        db = _make_empty_db
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client(mock_db=db)
            resp = client.post(
                "/api/v1/cache/store",
                params={
                    "query_hash": "xyz",
                    "query_text": "notary query",
                    "response_text": "notary response",
                    "agent_role": "notary_bot",
                    "save_enabled": True,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["stored"] is False
        assert resp.json()["reason"] == "agent_save_disabled"


# ── POST /api/v1/cache/regenerate/{hash} ─────────────────────────────────────

class TestRegenerateEndpoint:

    def test_regenerate_returns_invalidated_true(self):
        """Regenerate invalidates the entry and returns invalidated=True."""
        db = _make_empty_db
        client = _build_client(mock_db=db)
        resp = client.post("/api/v1/cache/regenerate/deadbeef1234")
        assert resp.status_code == 200
        body = resp.json()
        assert body["invalidated"] is True
        assert body["query_hash"] == "deadbeef1234"

    def test_regenerate_calls_db_delete(self):
        """Regenerate calls db.execute (for the DELETE statement)."""
        db = _make_empty_db
        client = _build_client(mock_db=db)
        client.post("/api/v1/cache/regenerate/myhash123")
        db.execute.assert_awaited


# ── DELETE /api/v1/cache/{hash} ───────────────────────────────────────────────

class TestDeleteEndpoint:

    def test_delete_returns_deleted_true(self):
        """DELETE endpoint returns deleted=True."""
        db = _make_empty_db
        client = _build_client(mock_db=db)
        resp = client.delete("/api/v1/cache/somehash9999")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_calls_db_execute(self):
        """DELETE triggers a DB execute call."""
        db = _make_empty_db
        client = _build_client(mock_db=db)
        client.delete("/api/v1/cache/anotherhash")
        db.execute.assert_awaited


# ── GET /api/v1/cache/analytics ───────────────────────────────────────────────

class TestAnalyticsEndpoint:

    def test_analytics_empty_db(self):
        """Empty DB returns all-zero metrics without error."""
        db = AsyncMock
        db.flush = AsyncMock

        # Execute call sequence:
        # 1 → total_entries (scalar = 0)
        # 2 → total_hits    (scalar = 0)
        # 3 → JSONB tokens query raises → fallback also raises → tokens_saved = 0
        responses = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
        ]
        response_iter = iter(responses)

        async def execute_side(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                raise RuntimeError("SQLite does not support JSONB")

        db.execute = execute_side

        client = _build_client(mock_db=db)
        resp = client.get("/api/v1/cache/analytics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_queries"] == 0
        assert body["cache_hits"] == 0
        assert body["cache_misses"] == 0
        assert body["hit_rate"] == 0.0
        assert body["tokens_saved"] == 0

    def test_analytics_with_data(self):
        """Analytics returns correct computed metrics from DB counters."""
        responses = [
            MagicMock(scalar=MagicMock(return_value=20)),    # total_entries
            MagicMock(scalar=MagicMock(return_value=80)),    # total_hits
            MagicMock(scalar=MagicMock(return_value=12000)), # tokens_saved
        ]
        db = AsyncMock
        db.flush = AsyncMock
        response_iter = iter(responses)

        async def execute_side(*args, **kwargs):
            return next(response_iter)

        db.execute = execute_side

        client = _build_client(mock_db=db)
        resp = client.get("/api/v1/cache/analytics")
        assert resp.status_code == 200
        body = resp.json()
        # total_queries = total_entries + total_hits = 20 + 80 = 100
        assert body["total_queries"] == 100
        assert body["cache_hits"] == 80
        assert body["cache_misses"] == 20
        assert body["tokens_saved"] == 12000
        # cost_saved = 12000 * 0.000002 = 0.024
        assert float(body["cost_saved"]) == pytest.approx(0.024, abs=1e-4)

    def test_analytics_hit_rate_calculated(self):
        """hit_rate = hits / (hits + entries) * 100, rounded to 2 decimals."""
        responses = [
            MagicMock(scalar=MagicMock(return_value=25)),  # entries
            MagicMock(scalar=MagicMock(return_value=75)),  # hits
            MagicMock(scalar=MagicMock(return_value=0)),   # tokens
        ]
        db = AsyncMock
        db.flush = AsyncMock
        it = iter(responses)

        async def exe(*a, **kw):
            return next(it)

        db.execute = exe
        client = _build_client(mock_db=db)
        resp = client.get("/api/v1/cache/analytics")
        assert resp.status_code == 200
        # 75 / (75 + 25) = 75%
        assert resp.json()["hit_rate"] == pytest.approx(75.0, abs=0.1)


# ── POST /api/v1/cache/settings ───────────────────────────────────────────────

class TestSettingsUpdateEndpoint:

    def test_update_settings_returns_correct_values(self):
        """POST /settings stores and echoes back the provided settings."""
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            resp = client.post("/api/v1/cache/settings", json={
                "agent_id": "agent-alpha-001",
                "cache_enabled": False,
                "save_enabled": True,
                "ttl_days": 7,
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "agent-alpha-001"
        assert body["cache_enabled"] is False
        assert body["save_enabled"] is True
        assert body["ttl_days"] == 7
        assert "updated_at" in body

    def test_update_settings_persists_in_memory(self):
        """After POST /settings, the in-process cache reflects new values."""
        import routers.cache as cache_mod
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            client.post("/api/v1/cache/settings", json={
                "agent_id": "agent-beta-002",
                "cache_enabled": False,
                "save_enabled": False,
                "ttl_days": 1,
            })
        stored = cache_mod._settings_cache.get("agent-beta-002")
        assert stored is not None
        assert stored["cache_enabled"] is False
        assert stored["save_enabled"] is False
        assert stored["ttl_days"] == 1

    def test_update_settings_defaults(self):
        """POST with minimal payload uses schema defaults."""
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            resp = client.post("/api/v1/cache/settings", json={
                "agent_id": "agent-gamma-003",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["cache_enabled"] is True
        assert body["save_enabled"] is True
        assert body["ttl_days"] == 3


# ── GET /api/v1/cache/settings/{agent_id} ────────────────────────────────────

class TestSettingsReadEndpoint:

    def test_get_settings_defaults_for_unknown_agent(self):
        """Unknown agent returns defaults: cache=True, save=True, ttl=3."""
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            resp = client.get("/api/v1/cache/settings/unknown-agent-xyz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "unknown-agent-xyz"
        assert body["cache_enabled"] is True
        assert body["save_enabled"] is True
        # ttl_days defaults to settings.qicache_ttl_days (3)
        assert body["ttl_days"] == 3

    def test_get_settings_returns_stored_values(self):
        """GET returns previously stored per-agent settings."""
        import routers.cache as cache_mod
        cache_mod._settings_cache["my-special-agent"] = {
            "cache_enabled": False,
            "save_enabled": True,
            "ttl_days": 14,
            "updated_at": "2026-03-17T10:00:00+00:00",
        }
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            resp = client.get("/api/v1/cache/settings/my-special-agent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "my-special-agent"
        assert body["cache_enabled"] is False
        assert body["ttl_days"] == 14

    def test_settings_roundtrip_post_then_get(self):
        """POST then GET returns the same values."""
        with patch("routers.cache._get_redis", new=AsyncMock(return_value=None)):
            client = _build_client
            client.post("/api/v1/cache/settings", json={
                "agent_id": "rt-agent",
                "cache_enabled": True,
                "save_enabled": False,
                "ttl_days": 5,
            })
            resp = client.get("/api/v1/cache/settings/rt-agent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cache_enabled"] is True
        assert body["save_enabled"] is False
        assert body["ttl_days"] == 5


# ── POST /api/v1/cache/evict-expired ─────────────────────────────────────────

class TestEvictExpiredEndpoint:

    def test_evict_returns_evicted_count(self):
        """evict-expired returns evicted=N based on rowcount."""
        db = _make_empty_db
        mock_result = MagicMock
        mock_result.rowcount = 5
        db.execute = AsyncMock(return_value=mock_result)

        client = _build_client(mock_db=db)
        resp = client.post("/api/v1/cache/evict-expired")
        assert resp.status_code == 200
        assert resp.json()["evicted"] == 5

    def test_evict_zero_when_no_expired(self):
        """When no entries are expired, returns evicted=0."""
        db = _make_empty_db
        mock_result = MagicMock
        mock_result.rowcount = 0
        db.execute = AsyncMock(return_value=mock_result)

        client = _build_client(mock_db=db)
        resp = client.post("/api/v1/cache/evict-expired")
        assert resp.status_code == 200
        assert resp.json()["evicted"] == 0

    def test_evict_calls_db_execute(self):
        """evict-expired issues a db.execute DELETE call."""
        db = _make_empty_db
        client = _build_client(mock_db=db)
        client.post("/api/v1/cache/evict-expired")
        db.execute.assert_awaited


# ── Standalone helper function tests ─────────────────────────────────────────

class TestHelperFunctions:
    """Unit tests for router-private helpers (imported directly)."""

    def test_normalize_query_lowercases_and_sorts(self):
        from routers.cache import _normalize_query
        result = _normalize_query("Invoice DISPUTE Payment")
        words = result.split
        # All lowercase
        assert all(w == w.lower for w in words)
        # Sorted alphabetically
        assert words == sorted(words)

    def test_normalize_query_removes_stopwords(self):
        from routers.cache import _normalize_query
        result = _normalize_query("the invoice is for a payment")
        assert "the" not in result.split
        assert "is" not in result.split
        assert "for" not in result.split

    def test_normalize_query_strips_punctuation(self):
        from routers.cache import _normalize_query
        result = _normalize_query("check, invoice! payment?")
        assert "," not in result
        assert "!" not in result
        assert "?" not in result

    def test_compute_hash_is_64_chars(self):
        from routers.cache import _compute_hash
        h = _compute_hash("invoice dispute", "resolver", {})
        assert len(h) == 64

    def test_compute_hash_same_inputs_same_output(self):
        from routers.cache import _compute_hash
        h1 = _compute_hash("invoice dispute", "resolver", {"dispute_type": "overpayment"})
        h2 = _compute_hash("invoice dispute", "resolver", {"dispute_type": "overpayment"})
        assert h1 == h2

    def test_compute_hash_different_context_different_hash(self):
        from routers.cache import _compute_hash
        h1 = _compute_hash("invoice dispute", "resolver", {"dispute_type": "overpayment"})
        h2 = _compute_hash("invoice dispute", "resolver", {"dispute_type": "short_delivery"})
        assert h1 != h2

    def test_compute_hash_different_agent_different_hash(self):
        from routers.cache import _compute_hash
        h1 = _compute_hash("invoice", "resolver", {})
        h2 = _compute_hash("invoice", "evaluator", {})
        assert h1 != h2
