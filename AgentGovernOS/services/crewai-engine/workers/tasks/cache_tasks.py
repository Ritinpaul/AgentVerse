"""
Celery tasks: QICACHE eviction.
"""

import logging
from datetime import UTC

from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.cache_tasks.evict_expired_cache", bind=True, max_retries=3)
def evict_expired_cache(self):
    """Hourly task: remove expired cache entries from PostgreSQL and Redis."""
    try:
        import os
        from datetime import datetime

        # ── PostgreSQL eviction ──
        from sqlalchemy import create_engine, text

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://agentgovern:secret@localhost:5432/agentgovern",
        ).replace("+asyncpg", "")  # Celery uses sync SQLAlchemy

        engine = create_engine(db_url)
        with engine.connect as conn:
            result = conn.execute(
                text(
                    "DELETE FROM query_cache "
                    "WHERE expires_at < NOW AND is_pinned = false"
                )
            )
            conn.commit
            evicted = result.rowcount

        # ── Log analytics ──
        with engine.connect as conn:
            conn.execute(
                text(
                    "INSERT INTO cache_analytics (evicted_entries, timestamp) "
                    "VALUES (:n, NOW)"
                ),
                {"n": evicted},
            )
            conn.commit

        logger.info(f"[QICACHE] Evicted {evicted} expired entries")
        return {"evicted": evicted, "timestamp": datetime.now(UTC).isoformat}

    except Exception as exc:
        logger.error(f"[QICACHE] Eviction failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
