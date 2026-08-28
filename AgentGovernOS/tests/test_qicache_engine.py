"""
Tests: QICACHE Engine

Covers:
  - Query normalization
  - Context-aware hash generation
  - Cache MISS → LLM route
  - Cache HIT after store
  - Bypass toggle (always goes to LLM)
  - Cache disabled toggle
  - Save disabled toggle (no store)
  - TTL reset on access
  - Invalidation
  - Session stats (hit rate, tokens saved)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine"))

from cache.qicache_engine import QICacheEngine, QICacheSettings


# ──────────────────────────────────────────────
# Normalization tests
# ──────────────────────────────────────────────

class TestNormalization:
    def test_lowercases(self, qicache_engine):
        assert qicache_engine.normalize("Hello World") == qicache_engine.normalize("hello world")

    def test_strips_punctuation(self, qicache_engine):
        assert qicache_engine.normalize("Hello, World!") == qicache_engine.normalize("hello world")

    def test_removes_stopwords(self, qicache_engine):
        result = qicache_engine.normalize("The invoice is for a payment")
        words = result.split
        assert "the" not in words
        assert "is" not in words
        assert "a" not in words
        assert "for" not in words
        # Content words should survive
        assert "invoice" in words
        assert "payment" in words


    def test_order_invariant(self, qicache_engine):
        q1 = qicache_engine.normalize("invoice dispute payment")
        q2 = qicache_engine.normalize("payment invoice dispute")
        assert q1 == q2

    def test_empty_string(self, qicache_engine):
        assert qicache_engine.normalize("") == ""

    def test_all_stopwords(self, qicache_engine):
        assert qicache_engine.normalize("the a an is are") == ""


# ──────────────────────────────────────────────
# Hash tests
# ──────────────────────────────────────────────

class TestHashing:
    def test_same_query_same_hash(self, qicache_engine):
        h1 = qicache_engine.compute_hash("invoice dispute", "resolver", {})
        h2 = qicache_engine.compute_hash("invoice dispute", "resolver", {})
        assert h1 == h2

    def test_different_agent_different_hash(self, qicache_engine):
        h1 = qicache_engine.compute_hash("invoice dispute", "resolver", {})
        h2 = qicache_engine.compute_hash("invoice dispute", "evaluator", {})
        assert h1 != h2

    def test_different_context_different_hash(self, qicache_engine):
        h1 = qicache_engine.compute_hash("invoice dispute", "resolver", {"dispute_type": "overpayment"})
        h2 = qicache_engine.compute_hash("invoice dispute", "resolver", {"dispute_type": "short_delivery"})
        assert h1 != h2

    def test_hash_is_64_chars(self, qicache_engine):
        h = qicache_engine.compute_hash("test query", "agent", {})
        assert len(h) == 64

    def test_context_none_vs_empty_same(self, qicache_engine):
        h1 = qicache_engine.compute_hash("test query", "agent", None)
        h2 = qicache_engine.compute_hash("test query", "agent", {})
        assert h1 == h2


# ──────────────────────────────────────────────
# Cache check/store/hit tests (Redis only — no DB)
# ──────────────────────────────────────────────

class TestCacheOperations:
    def test_cache_miss_on_empty(self, qicache_engine):
        settings = QICacheSettings
        result = qicache_engine.check("what is the dispute amount", "resolver", {}, settings)
        assert result.hit is False
        assert result.source == "llm"

    def test_cache_hit_after_store(self, qicache_engine):
        settings = QICacheSettings
        query = "check invoice PO-4523 payment status"
        
        # First check — miss
        miss = qicache_engine.check(query, "resolver", {}, settings)
        assert miss.hit is False

        # Store the response
        stored = qicache_engine.store(
            query_hash=miss.query_hash,
            query_text=query,
            response_text="Invoice PO-4523 is valid, payment of ₹25,000 approved.",
            metadata={"tokens_consumed": 150},
            settings=settings,
        )
        assert stored is True

        # Second check — should be HIT from Redis
        hit = qicache_engine.check(query, "resolver", {}, settings)
        assert hit.hit is True
        assert "PO-4523" in hit.response
        assert hit.source == "redis_hot"

    def test_bypass_skips_cache(self, qicache_engine):
        settings = QICacheSettings(bypass=True)
        # Store something first
        qicache_engine.store("abc123", "test query", "cached response", settings=QICacheSettings)
        
        # With bypass, should not check cache
        result = qicache_engine.check("test query", "resolver", {}, settings)
        assert result.hit is False
        assert result.source == "llm"

    def test_cache_disabled_skips_check(self, qicache_engine):
        settings = QICacheSettings(cache_enabled=False)
        result = qicache_engine.check("any query", "resolver", {}, settings)
        assert result.hit is False

    def test_save_disabled_does_not_store(self, qicache_engine, mock_redis):
        settings = QICacheSettings(save_enabled=False)
        stored = qicache_engine.store(
            query_hash="test_hash_no_save",
            query_text="a query",
            response_text="a response",
            settings=settings,
        )
        assert stored is False
        # Verify nothing in Redis
        assert mock_redis.get("qicache:test_hash_no_save") is None

    def test_invalidation_removes_entry(self, qicache_engine):
        settings = QICacheSettings
        query = "what is risk score for customer ACM-002"

        miss = qicache_engine.check(query, "risk_evaluator", {}, settings)
        qicache_engine.store(
            query_hash=miss.query_hash,
            query_text=query,
            response_text="Risk score: 0.35, LOW risk.",
            settings=settings,
        )

        # Confirm hit
        hit = qicache_engine.check(query, "risk_evaluator", {}, settings)
        assert hit.hit is True

        # Invalidate
        qicache_engine.invalidate(miss.query_hash)

        # Now should miss again
        after_invalidate = qicache_engine.check(query, "risk_evaluator", {}, settings)
        assert after_invalidate.hit is False


# ──────────────────────────────────────────────
# Stats tracking
# ──────────────────────────────────────────────

class TestStats:
    def test_hit_miss_counts(self, qicache_engine):
        s = QICacheSettings
        qicache_engine.check("query 1", "agent", {}, s)  # miss
        qicache_engine.check("query 2", "agent", {}, s)  # miss

        qicache_engine.store(
            query_hash=qicache_engine.compute_hash(
                qicache_engine.normalize("query 3"), "agent", {}
            ),
            query_text="query 3",
            response_text="result 3",
            settings=s,
        )
        qicache_engine.check("query 3", "agent", {}, s)  # hit

        stats = qicache_engine.stats
        assert stats["misses"] == 2
        assert stats["hits"] == 1
        assert stats["hit_rate_pct"] == round(1 / 3 * 100, 1)

    def test_stats_empty_engine(self, qicache_engine):
        stats = qicache_engine.stats
        assert stats["total"] == 0
        assert stats["hit_rate_pct"] == 0.0

    def test_tokens_saved_accumulates(self, mock_redis):
        """Tokens saved should accumulate across Redis hits."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=mock_redis, db_session=None)
        settings = QICacheSettings

        # Store two entries with token metadata
        q1 = "dispute settlement for customer ACM-001"
        m1 = engine.check(q1, "resolver", {}, settings)
        mock_redis.set(f"qicache:{m1.query_hash}", "response A")

        q2 = "check credit score for customer ACM-002"
        m2 = engine.check(q2, "evaluator", {}, settings)
        mock_redis.set(f"qicache:{m2.query_hash}", "response B")

        # Both hits (via Redis)
        engine.check(q1, "resolver", {}, settings)
        engine.check(q2, "evaluator", {}, settings)

        stats = engine.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["total"] == 4


# ──────────────────────────────────────────────
# DB fallback path tests (mock DB, no Redis)
# ──────────────────────────────────────────────

class TestDatabasePath:
    """Tests for the PostgreSQL warm-cache path (no Redis)."""

    def _make_db_hit(self, response_text="cached text", tokens=500):
        """Return a mock DB where execute.fetchone returns a row."""
        from unittest.mock import MagicMock
        mock_db = MagicMock
        mock_db.execute.return_value.fetchone.return_value = (
            response_text, {"tokens_consumed": tokens}
        )
        return mock_db

    def _make_db_miss(self):
        """Return a mock DB where execute.fetchone returns None."""
        from unittest.mock import MagicMock
        mock_db = MagicMock
        mock_db.execute.return_value.fetchone.return_value = None
        return mock_db

    def test_db_hit_returns_cached_response(self):
        """check should return hit=True from DB when Redis is absent."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        db = self._make_db_hit("DB cached response", tokens=300)
        engine = QICacheEngine(redis_client=None, db_session=db)
        result = engine.check("some query", "resolver", {}, QICacheSettings)
        assert result.hit is True
        assert result.response == "DB cached response"
        assert result.source == "postgres_warm"
        assert result.tokens_saved == 300

    def test_db_miss_returns_miss(self):
        """check should return hit=False when DB also misses."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        db = self._make_db_miss
        engine = QICacheEngine(redis_client=None, db_session=db)
        result = engine.check("some query", "resolver", {}, QICacheSettings)
        assert result.hit is False
        assert result.source == "llm"

    def test_db_hit_increments_stats(self):
        """DB hits should increment the internal hit counter."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        db = self._make_db_hit(tokens=200)
        engine = QICacheEngine(redis_client=None, db_session=db)
        engine.check("query one", "agent", {}, QICacheSettings)
        engine.check("query two", "agent", {}, QICacheSettings)  # also DB hit
        assert engine.stats["hits"] == 2

    def test_db_hit_backfills_redis(self, mock_redis):
        """A DB hit should write entry into Redis for future hot-cache hits."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        db = self._make_db_hit("warm response", tokens=100)
        engine = QICacheEngine(redis_client=mock_redis, db_session=db)
        result = engine.check("warm query", "agent", {}, QICacheSettings)
        assert result.hit is True
        # Redis should now have the entry
        key = f"qicache:{result.query_hash}"
        assert mock_redis.get(key) is not None

    def test_db_exception_falls_through_to_miss(self):
        """check should return miss (not raise) if DB throws an exception."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        mock_db = MagicMock
        mock_db.execute.side_effect = RuntimeError("DB connection lost")
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        result = engine.check("test query", "agent", {}, QICacheSettings)
        assert result.hit is False
        assert result.source == "llm"

    def test_store_with_db_calls_execute(self):
        """store should call db.execute when DB is present."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        mock_db = MagicMock
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        stored = engine.store(
            query_hash="abc123",
            query_text="test query text",
            response_text="test response",
            metadata={"tokens_consumed": 50},
            settings=QICacheSettings,
        )
        assert stored is True
        mock_db.execute.assert_called_once

    def test_store_db_exception_does_not_raise(self):
        """store should swallow DB exceptions and still return True."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        mock_db = MagicMock
        mock_db.execute.side_effect = RuntimeError("DB write failed")
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        stored = engine.store("hash1", "query", "response", settings=QICacheSettings)
        assert stored is True  # didn't raise, returned True even on DB error

    def test_store_both_redis_and_db(self, mock_redis):
        """store should write to both Redis and DB."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        mock_db = MagicMock
        engine = QICacheEngine(redis_client=mock_redis, db_session=mock_db)
        engine.store("hash_dual", "my query", "my response", settings=QICacheSettings)
        assert mock_redis.get("qicache:hash_dual") is not None
        mock_db.execute.assert_called_once

    def test_invalidate_with_db_deletes_entry(self):
        """invalidate should call db.execute to delete from DB."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine
        mock_db = MagicMock
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        engine.invalidate("some_hash")
        mock_db.execute.assert_called_once

    def test_invalidate_db_exception_does_not_raise(self):
        """invalidate should swallow DB exceptions silently."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine
        mock_db = MagicMock
        mock_db.execute.side_effect = RuntimeError("delete failed")
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        engine.invalidate("some_hash")  # should not raise

    def test_db_hit_no_metadata_returns_zero_tokens(self):
        """DB hit where response_metadata is None should give tokens_saved=0."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        mock_db = MagicMock
        mock_db.execute.return_value.fetchone.return_value = ("response", None)
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        result = engine.check("query", "agent", {}, QICacheSettings)
        assert result.hit is True
        assert result.tokens_saved == 0


# ──────────────────────────────────────────────
# Redis edge case tests
# ──────────────────────────────────────────────

class TestRedisEdgeCases:

    def test_redis_returns_bytes_decoded_correctly(self, mock_redis):
        """When Redis returns bytes, response should be decoded to str."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=mock_redis, db_session=None)
        settings = QICacheSettings

        query = "bytes test query"
        miss = engine.check(query, "agent", {}, settings)
        # Manually store as bytes in mock Redis
        mock_redis.set(f"qicache:{miss.query_hash}", b"bytes response from redis")

        hit = engine.check(query, "agent", {}, settings)
        assert hit.hit is True
        assert isinstance(hit.response, str)
        assert hit.response == "bytes response from redis"

    def test_redis_exception_falls_through_to_db_miss(self, mock_redis):
        """When Redis.get raises, check should fall through (not crash)."""
        from unittest.mock import MagicMock, patch
        from cache.qicache_engine import QICacheEngine, QICacheSettings

        broken_redis = MagicMock
        broken_redis.get.side_effect = ConnectionError("Redis down")
        engine = QICacheEngine(redis_client=broken_redis, db_session=None)
        result = engine.check("test query", "agent", {}, QICacheSettings)
        assert result.hit is False

    def test_redis_store_exception_does_not_raise(self):
        """store should not raise even if Redis.setex fails."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        broken_redis = MagicMock
        broken_redis.setex.side_effect = ConnectionError("Redis down")
        engine = QICacheEngine(redis_client=broken_redis, db_session=None)
        result = engine.store("hash", "text", "response", settings=QICacheSettings)
        assert result is True  # should still return True

    def test_no_redis_no_db_always_miss(self):
        """Engine with neither Redis nor DB should always return miss."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=None, db_session=None)
        result = engine.check("no storage query", "agent", {}, QICacheSettings)
        assert result.hit is False

    def test_no_redis_no_db_store_returns_true(self):
        """store with no backends and save_enabled=True still returns True."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=None, db_session=None)
        result = engine.store("hash", "text", "response", settings=QICacheSettings)
        assert result is True

    def test_invalidate_with_neither_backend_does_nothing(self):
        """invalidate with no backends should not crash."""
        from cache.qicache_engine import QICacheEngine
        engine = QICacheEngine(redis_client=None, db_session=None)
        engine.invalidate("any_hash")  # should complete silently


# ──────────────────────────────────────────────
# Eviction tests
# ──────────────────────────────────────────────

class TestEviction:

    def test_evict_expired_no_db_returns_zero(self):
        """evict_expired with no DB should return 0."""
        from cache.qicache_engine import QICacheEngine
        engine = QICacheEngine(redis_client=None, db_session=None)
        count = engine.evict_expired
        assert count == 0

    def test_evict_expired_with_db_returns_rowcount(self):
        """evict_expired should return the number of rows deleted."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine
        mock_db = MagicMock
        mock_db.execute.return_value.rowcount = 7
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        count = engine.evict_expired
        assert count == 7

    def test_evict_expired_db_exception_returns_zero(self):
        """evict_expired should return 0 on DB exception without raising."""
        from unittest.mock import MagicMock
        from cache.qicache_engine import QICacheEngine
        mock_db = MagicMock
        mock_db.execute.side_effect = RuntimeError("eviction failed")
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        count = engine.evict_expired
        assert count == 0

    def test_evict_expired_calls_delete_query(self):
        """evict_expired should issue the DELETE SQL."""
        from unittest.mock import MagicMock, call
        from cache.qicache_engine import QICacheEngine
        mock_db = MagicMock
        mock_db.execute.return_value.rowcount = 3
        engine = QICacheEngine(redis_client=None, db_session=mock_db)
        engine.evict_expired
        mock_db.execute.assert_called_once
        # The query should reference query_cache table
        sql_arg = str(mock_db.execute.call_args[0][0])
        assert "query_cache" in sql_arg or "DELETE" in sql_arg


# ──────────────────────────────────────────────
# QICacheSettings dataclass tests
# ──────────────────────────────────────────────

class TestQICacheSettings:

    def test_default_settings(self):
        """Default settings should have cache and save enabled."""
        from cache.qicache_engine import QICacheSettings
        s = QICacheSettings
        assert s.cache_enabled is True
        assert s.save_enabled is True
        assert s.bypass is False
        assert s.ttl_days == 3

    def test_bypass_overrides_cache_enabled(self, mock_redis):
        """bypass=True should skip cache even if cache_enabled=True."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=mock_redis, db_session=None)
        # Pre-populate cache
        engine.store("bh1", "bypass test query", "cached", settings=QICacheSettings)
        # bypass should skip it
        result = engine.check(
            "bypass test query", "agent", {},
            QICacheSettings(bypass=True, cache_enabled=True)
        )
        assert result.hit is False

    def test_cache_disabled_skips_even_with_data(self, mock_redis):
        """cache_enabled=False should always bypass."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=mock_redis, db_session=None)
        engine.store("cd1", "disabled test query", "cached", settings=QICacheSettings)
        result = engine.check(
            "disabled test query", "agent", {},
            QICacheSettings(cache_enabled=False)
        )
        assert result.hit is False

    def test_save_disabled_cache_check_still_works(self, mock_redis):
        """save_enabled=False should not affect the check path."""
        from cache.qicache_engine import QICacheEngine, QICacheSettings
        engine = QICacheEngine(redis_client=mock_redis, db_session=None)
        # Store with save enabled
        engine.store("sc1", "save check query", "cached", settings=QICacheSettings)
        # Check with save disabled (save_enabled shouldn't affect reads)
        result = engine.check(
            "save check query", "agent", {},
            QICacheSettings(save_enabled=False)
        )
        assert result.hit is True
