"""
Token Budget Service
====================
Enforces the 50,000 token/day per-user cap for the FreeBuff free AI tier.

Storage: Redis key  ``freebuff:budget:{user_id}:{YYYY-MM-DD}``
TTL:     The key expires at midnight UTC of the next day (rolling window stays
         aligned to calendar day, reset is predictable for users).

Usage:
    budget_svc = TokenBudgetService(redis_client)
    status = await budget_svc.check(user_id, estimated_tokens=500)
    if status.exceeded:
        raise HTTPException(429, ...)
    # ... stream response ...
    await budget_svc.commit(user_id, actual_tokens=487)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from models.freebuff import BudgetStatus

DAILY_LIMIT = 50_000
KEY_PREFIX = "freebuff:budget"


def _today_key(user_id: str) -> str:
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"{KEY_PREFIX}:{user_id}:{date_str}"


def _midnight_utc_ttl() -> int:
    """Seconds until next midnight UTC — used as Redis key TTL."""
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())


def _next_midnight_utc() -> datetime:
    now = datetime.now(UTC)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


class TokenBudgetService:
    """Per-user daily token budget backed by Redis."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get_status(self, user_id: str) -> BudgetStatus:
        """Return the current budget status without modifying it."""
        key = _today_key(user_id)
        raw = await self._redis.get(key)
        used = int(raw) if raw else 0
        remaining = max(0, DAILY_LIMIT - used)
        return BudgetStatus(
            used=used,
            remaining=remaining,
            limit=DAILY_LIMIT,
            resets_at=_next_midnight_utc(),
            exceeded=(used >= DAILY_LIMIT),
        )

    async def check(self, user_id: str, estimated_tokens: int = 0) -> BudgetStatus:
        """
        Check if adding ``estimated_tokens`` would exceed the limit.
        Does NOT modify the budget — call commit() after actual usage is known.
        """
        key = _today_key(user_id)
        raw = await self._redis.get(key)
        used = int(raw) if raw else 0
        projected = used + estimated_tokens
        remaining = max(0, DAILY_LIMIT - used)
        return BudgetStatus(
            used=used,
            remaining=remaining,
            limit=DAILY_LIMIT,
            resets_at=_next_midnight_utc(),
            exceeded=(projected > DAILY_LIMIT),
        )

    async def commit(self, user_id: str, actual_tokens: int) -> BudgetStatus:
        """
        Atomically increment the user's budget by ``actual_tokens``.
        Sets TTL on first write so the key expires at midnight UTC.
        Returns the updated status.
        """
        key = _today_key(user_id)
        ttl = _midnight_utc_ttl()

        pipe = self._redis.pipeline()
        pipe.incr(key, actual_tokens)
        pipe.expire(key, ttl, xx=False)  # only set if no TTL yet (first write of the day)
        results = await pipe.execute()

        used = int(results[0])
        remaining = max(0, DAILY_LIMIT - used)
        return BudgetStatus(
            used=used,
            remaining=remaining,
            limit=DAILY_LIMIT,
            resets_at=_next_midnight_utc(),
            exceeded=(used > DAILY_LIMIT),
        )

    async def reset(self, user_id: str) -> None:
        """Admin-only: manually reset a user's daily budget (e.g. for testing)."""
        key = _today_key(user_id)
        await self._redis.delete(key)
