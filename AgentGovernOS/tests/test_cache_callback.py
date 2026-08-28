"""
Tests: QICACHE Callback (CrewAI integration layer)

Covers:
  - on_agent_action: cache miss → pending hash stored
  - on_agent_action: cache hit → logged, no pending (no LLM needed)
  - on_agent_finish: pending → stored in cache
  - on_agent_finish: no pending → no store (idempotent)
  - bypass toggle propagated to engine
  - save_enabled=False: finish does not store
  - stats exposed correctly
"""

import pytest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "crewai-engine"))

from cache.qicache_engine import QICacheSettings
from cache.cache_callback import QICacheCallback


class TestCacheCallbackMiss:
    """When the cache misses, LLM is called and result should be stored."""

    def test_action_stores_pending_hash_on_miss(self, qicache_engine):
        cb = QICacheCallback(engine=qicache_engine, settings=QICacheSettings)
        cb.on_agent_action("Evaluate risk for customer ACM-001", agent_role="risk_evaluator")
        assert "risk_evaluator" in cb._pending

    def test_finish_stores_response_after_miss(self, qicache_engine, mock_redis):
        cb = QICacheCallback(engine=qicache_engine, settings=QICacheSettings(save_enabled=True))
        cb.on_agent_action("Evaluate risk for customer ACM-001", agent_role="risk_evaluator")
        cb.on_agent_finish("Risk score: 0.35, LOW risk.", agent_role="risk_evaluator")

        # Verify pending was cleared
        assert "risk_evaluator" not in cb._pending

        # Verify something was stored in Redis
        keys = list(mock_redis.scan_iter("qicache:*"))
        assert len(keys) >= 1

    def test_finish_with_no_pending_is_harmless(self, qicache_engine):
        cb = QICacheCallback(engine=qicache_engine)
        # No on_agent_action called — should not raise
        cb.on_agent_finish("some output", agent_role="historian")


class TestCacheCallbackHit:
    """When cache hits, LLM should be skipped (hit logged, no pending)."""

    def test_hit_does_not_add_pending(self, qicache_engine, mock_redis):
        settings = QICacheSettings
        cb = QICacheCallback(engine=qicache_engine, settings=settings)

        # Pre-populate the cache
        query = "Evidence collection for dispute DISP-001"
        miss = qicache_engine.check(query, "evidence_collector", {}, settings)
        qicache_engine.store(
            query_hash=miss.query_hash,
            query_text=query,
            response_text="Documents found: INV-001, PO-123",
            settings=settings,
        )

        # Now action should be a cache HIT
        cb.on_agent_action(query, agent_role="evidence_collector")
        assert "evidence_collector" not in cb._pending


class TestCacheCallbackToggles:
    """Toggle behavior: bypass and save_enabled respected."""

    def test_bypass_still_adds_pending(self, qicache_engine):
        """Bypass means no cache check, but LLM WILL be called → pending needed."""
        settings = QICacheSettings(bypass=True)
        cb = QICacheCallback(engine=qicache_engine, settings=settings)
        cb.on_agent_action("any query", agent_role="negotiation_agent")
        # bypass → check returns miss → pending added
        assert "negotiation_agent" in cb._pending

    def test_save_disabled_finish_does_not_store(self, qicache_engine, mock_redis):
        settings = QICacheSettings(save_enabled=False)
        cb = QICacheCallback(engine=qicache_engine, settings=settings)
        cb.on_agent_action("some query", agent_role="compliances")
        cb.on_agent_finish("some response", agent_role="compliances")

        # With save_enabled=False, nothing should be in Redis
        keys = list(mock_redis.scan_iter("qicache:*"))
        assert len(keys) == 0


class TestCallbackStats:
    def test_stats_accessible(self, qicache_engine):
        cb = QICacheCallback(engine=qicache_engine)
        stats = cb.get_stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate_pct" in stats
        assert stats["total"] == 0
