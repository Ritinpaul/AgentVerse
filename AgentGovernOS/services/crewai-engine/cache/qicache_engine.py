"""
QICACHE Callback — CrewAI integration layer.

Intercepts every LLM call in CrewAI. On the way in, checks the cache.
On the way out, stores the response (if save_enabled).

Usage in crews:
    crew = Crew(..., callbacks=[QICacheCallback(redis_client, db_session)])
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

STOPWORDS = frozenset({"the", "a", "an", "is", "are", "was", "were", "for", "of", "to", "in", "on"})


@dataclass
class CacheResult:
    hit: bool
    response: str | None = None
    source: str = "llm"
    tokens_saved: int = 0
    query_hash: str = ""


@dataclass
class QICacheSettings:
    """Per-request cache controls — passed through crew context."""
    cache_enabled: bool = True
    save_enabled: bool = True
    bypass: bool = False
    ttl_days: int = 3


class QICacheEngine:
    """
    Pure-Python QICACHE engine. Works with both async (FastAPI)
    and sync (CrewAI callback) contexts.

    Two-tier storage:
        Hot  → Redis  (<1ms, key: qicache:{hash})
        Warm → PostgreSQL (<10ms, persisted)

    Three user controls:
        cache_enabled: master toggle (ON = use cache; OFF = always LLM)
        save_enabled:  ON = save new responses; OFF = ephemeral mode
        bypass:        True = skip cache for this call, get fresh LLM response

    TTL logic:
        - Every cache HIT resets the TTL timer (last_accessed_at)
        - Entries unused for ttl_days are evicted by the hourly Celery task
        - is_pinned = True entries never expire
    """

    TTL_DAYS = 3

    def __init__(self, redis_client=None, db_session=None):
        self.redis = redis_client
        self.db = db_session
        self._stats = {"hits": 0, "misses": 0, "tokens_saved": 0}

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def normalize(self, text: str) -> str:
        """Canonical form: lowercase → strip punctuation → remove stopwords → sort words."""
        text = text.lower.strip
        text = re.sub(r"[^\w\s]", "", text)
        words = [w for w in text.split if w not in STOPWORDS]
        return " ".join(sorted(words))

    def compute_hash(self, normalized: str, agent_role: str = "", context: dict | None = None) -> str:
        """Context-aware SHA-256 hash. Same query + different agent = different key."""
        ctx = context or {}
        payload = (
            f"{normalized}|{agent_role}"
            f"|{ctx.get('dispute_type', '')}"
            f"|{ctx.get('amount_range', '')}"
        )
        return hashlib.sha256(payload.encode).hexdigest

    def check(
        self,
        query_text: str,
        agent_role: str = "",
        context: dict | None = None,
        settings: QICacheSettings | None = None,
    ) -> CacheResult:
        """Synchronous cache lookup — for use inside CrewAI callbacks."""
        s = settings or QICacheSettings
        normalized = self.normalize(query_text)
        qhash = self.compute_hash(normalized, agent_role, context)

        if s.bypass or not s.cache_enabled:
            return CacheResult(hit=False, query_hash=qhash, source="llm")

        # --- Redis hot cache ---
        if self.redis:
            try:
                cached = self.redis.get(f"qicache:{qhash}")
                if cached:
                    self.redis.expire(f"qicache:{qhash}", s.ttl_days * 86400)
                    self._stats["hits"] += 1
                    response = cached.decode if isinstance(cached, bytes) else cached
                    return CacheResult(hit=True, response=response, source="redis_hot", query_hash=qhash)
            except Exception as e:
                logger.warning(f"Redis check failed: {e}")

        # --- PostgreSQL warm cache (sync via SQLAlchemy) ---
        if self.db:
            try:
                from sqlalchemy import text
                now = datetime.now(UTC)
                result = self.db.execute(
                    text(
                        "SELECT response_text, response_metadata FROM query_cache "
                        "WHERE query_hash = :qhash AND expires_at > :now LIMIT 1"
                    ),
                    {"qhash": qhash, "now": now},
                ).fetchone
                if result:
                    self.db.execute(
                        text(
                            "UPDATE query_cache SET hit_count = hit_count + 1, "
                            "last_accessed_at = :now, "
                            "expires_at = :new_exp "
                            "WHERE query_hash = :qhash"
                        ),
                        {"qhash": qhash, "now": now,
                         "new_exp": now + timedelta(days=s.ttl_days)},
                    )
                    tokens = result[1].get("tokens_consumed", 0) if result[1] else 0
                    self._stats["hits"] += 1
                    self._stats["tokens_saved"] += tokens
                    if self.redis:
                        self.redis.setex(f"qicache:{qhash}", s.ttl_days * 86400, result[0])
                    return CacheResult(hit=True, response=result[0], source="postgres_warm",
                                       tokens_saved=tokens, query_hash=qhash)
            except Exception as e:
                logger.warning(f"Postgres cache check failed: {e}")

        self._stats["misses"] += 1
        return CacheResult(hit=False, query_hash=qhash, source="llm")

    def store(
        self,
        query_hash: str,
        query_text: str,
        response_text: str,
        metadata: dict | None = None,
        settings: QICacheSettings | None = None,
    ) -> bool:
        """Sync cache write. Returns True if stored, False if skipped."""
        s = settings or QICacheSettings
        if not s.save_enabled or not s.cache_enabled:
            return False

        normalized = self.normalize(query_text)
        expires = datetime.now(UTC) + timedelta(days=s.ttl_days)

        if self.redis:
            try:
                self.redis.setex(f"qicache:{query_hash}", s.ttl_days * 86400, response_text)
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")

        if self.db:
            try:
                from sqlalchemy import text
                self.db.execute(
                    text(
                        "INSERT INTO query_cache "
                        "(query_hash, query_text, query_normalized, response_text, "
                        "response_metadata, expires_at) "
                        "VALUES (:qhash, :qtext, :qnorm, :resp, :meta::jsonb, :exp) "
                        "ON CONFLICT (query_hash) DO UPDATE "
                        "SET response_text = EXCLUDED.response_text, "
                        "    last_accessed_at = NOW, "
                        "    expires_at = EXCLUDED.expires_at"
                    ),
                    {
                        "qhash": query_hash,
                        "qtext": query_text,
                        "qnorm": normalized,
                        "resp": response_text,
                        "meta": str(metadata or {}),
                        "exp": expires,
                    },
                )
            except Exception as e:
                logger.warning(f"Postgres store failed: {e}")

        return True

    def invalidate(self, query_hash: str) -> None:
        """Remove a cache entry (used by Regenerate)."""
        if self.redis:
            try:
                self.redis.delete(f"qicache:{query_hash}")
            except Exception:
                pass
        if self.db:
            try:
                from sqlalchemy import text
                self.db.execute(
                    text("DELETE FROM query_cache WHERE query_hash = :qhash"),
                    {"qhash": query_hash},
                )
            except Exception as e:
                logger.warning(f"Invalidate failed: {e}")

    def evict_expired(self) -> int:
        """Remove all non-pinned entries past their TTL. Returns count evicted."""
        if not self.db:
            return 0
        try:
            from sqlalchemy import text
            result = self.db.execute(
                text(
                    "DELETE FROM query_cache "
                    "WHERE expires_at < NOW AND is_pinned = false"
                )
            )
            return result.rowcount
        except Exception as e:
            logger.warning(f"Eviction failed: {e}")
            return 0

    @property
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = round(self._stats["hits"] / total * 100, 1) if total else 0.0
        return {
            "total": total,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_pct": hit_rate,
            "tokens_saved": self._stats["tokens_saved"],
        }
