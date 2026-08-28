"""Rate limiter middleware — per-agent / per-IP sliding-window rate limiting.

Supports:
1. Distributed Redis sliding-window & token counter per identifier.
2. Tier-based burst allowances (Free, Pro, Enterprise).
3. Resilient in-memory sliding-window fallback when Redis is degraded or unavailable.
4. Per-route limits wired via FastAPI dependency injection.

Identifier resolution order:
  1. X-Agent-ID request header
  2. JWT sub claim (if Bearer token present)
  3. Client IP address

Tier resolution order:
  1. X-Tier or X-Plan header
  2. JWT tier claim
  3. Default: 'free'

Tier default limits:
  - Free:       30 req / 60s, +5 burst allowance
  - Pro:        120 req / 60s, +20 burst allowance
  - Enterprise: 600 req / 60s, +100 burst allowance
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Annotated

from fastapi import Header, HTTPException, Request, Response, status

logger = logging.getLogger(__name__)

# ── Tier Definitions ──────────────────────────────────────────────────────────

TIER_LIMITS: dict[str, tuple[int, int, int]] = {
    # (max_requests, window_seconds, burst_allowance)
    "free": (30, 60, 5),
    "pro": (120, 60, 20),
    "enterprise": (600, 60, 100),
}


# ── In-Memory Sliding-Window Fallback ─────────────────────────────────────────

class InMemorySlidingWindowBucket:
    """Thread-safe in-memory sliding window rate limiter for degraded fallback."""

    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: dict[str, collections.deque] = {}

    def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = collections.deque()
            q = self._buckets[key]

            # Evict timestamps older than window
            while q and q[0] < cutoff:
                q.popleft()

            count = len(q) + 1
            if count <= max_requests:
                q.append(now)
                ttl = int(window_seconds - (now - q[0])) if q else window_seconds
                return True, count, max(1, ttl)
            else:
                ttl = int(window_seconds - (now - q[0])) if q else window_seconds
                return False, count, max(1, ttl)

    def clear(self):
        with self._lock:
            self._buckets.clear()


in_memory_limiter = InMemorySlidingWindowBucket()


# ── Redis helper with connection caching and failure cooldown ───────────────

_cached_redis = None
_redis_last_failure = 0.0

def _get_redis():
    global _cached_redis, _redis_last_failure
    now = time.time()
    # If connection failed recently, avoid blocking reconnect loops (5s cooldown)
    if _redis_last_failure and (now - _redis_last_failure < 5.0):
        return None

    if _cached_redis is not None:
        return _cached_redis

    try:
        import redis
        from config import get_settings
        settings = get_settings()
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=0.2)
        client.ping()
        _cached_redis = client
        return client
    except Exception:
        _redis_last_failure = now
        _cached_redis = None
        return None


# ── Core sliding-window counter ───────────────────────────────────────────────

def _check_window(redis_client, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
    """Increment a Redis counter for the given key within the window.

    Returns (allowed, current_count, ttl_seconds).
    """
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    count, ttl = pipe.execute()

    if ttl == -1:
        # Key exists but has no expiry — set it (race-condition guard)
        redis_client.expire(key, window_seconds)
        ttl = window_seconds
    elif ttl == -2 or count == 1:
        # Key was just created by INCR — set expiry
        redis_client.expire(key, window_seconds)
        ttl = window_seconds

    allowed = count <= max_requests
    return allowed, count, ttl


# ── Identifier & Tier extractors ──────────────────────────────────────────────

def _extract_identifier(request: Request, x_agent_id: str | None) -> str:
    """Resolve the best available identifier for rate-limiting."""
    if x_agent_id:
        return f"agent:{x_agent_id}"

    # Try JWT sub claim from Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            from config import get_settings
            from jose import jwt
            settings = get_settings()
            token = auth_header[7:]
            claims = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            sub = claims.get("sub")
            if sub:
                return f"jwt:{sub}"
        except Exception:
            pass

    # Fall back to client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    return f"ip:{client_ip}"


def _extract_tier(request: Request) -> str:
    """Resolve user tier from header or JWT claim, default to 'free'."""
    tier_header = request.headers.get("x-tier") or request.headers.get("x-plan")
    if tier_header:
        t = tier_header.lower().strip()
        if t in TIER_LIMITS:
            return t

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            from config import get_settings
            from jose import jwt
            settings = get_settings()
            token = auth_header[7:]
            claims = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            tier_claim = str(claims.get("tier") or claims.get("plan", "")).lower().strip()
            if tier_claim in TIER_LIMITS:
                return tier_claim
        except Exception:
            pass

    return "free"


# ── Dependency factory ────────────────────────────────────────────────────────

def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    burst_allowance: int = 0,
    tier_based: bool = False,
    fallback_to_memory: bool = False,
):
    """Return a FastAPI dependency that enforces a custom or tier-based rate limit.

    Args:
        max_requests:        Maximum number of requests allowed in the window.
        window_seconds:      Size of the rolling window in seconds.
        burst_allowance:     Extra burst requests permitted above max_requests.
        tier_based:          If True, calculates limit dynamically from caller's tier.
        fallback_to_memory:  If True, uses in-memory bucket fallback when Redis is down.
    """
    async def _limiter(
        request: Request,
        response: Response,
        x_agent_id: Annotated[str | None, Header(alias="X-Agent-ID")] = None,
    ) -> None:
        from config import get_settings
        settings = get_settings()

        # Skip rate limiting in development unless explicitly enabled
        if settings.app_env == "development" and not settings.rate_limit_enabled:
            return

        effective_max = max_requests
        effective_window = window_seconds
        effective_burst = burst_allowance

        if tier_based:
            tier = _extract_tier(request)
            tier_cfg = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            effective_max = tier_cfg[0]
            effective_window = tier_cfg[1]
            effective_burst = tier_cfg[2]

        total_allowed_requests = effective_max + effective_burst
        identifier = _extract_identifier(request, x_agent_id)
        window_key = f"rl:{identifier}:{effective_window}"

        r = _get_redis()
        if not r:
            should_fallback = fallback_to_memory or getattr(settings, "rate_limit_memory_fallback", False)
            if should_fallback:
                allowed, count, ttl = in_memory_limiter.check(
                    window_key, total_allowed_requests, effective_window
                )
            else:
                # Redis unavailable and memory fallback not configured — fail open with a warning
                logger.warning("[RATE_LIMIT] Redis unavailable — rate limiting skipped")
                return
        else:
            allowed, count, ttl = _check_window(
                r, window_key, total_allowed_requests, effective_window
            )

        # Inject rate limit info into request state and response headers
        request.state.rate_limit_limit = total_allowed_requests
        request.state.rate_limit_remaining = max(0, total_allowed_requests - count)
        request.state.rate_limit_reset = int(time.time()) + ttl

        if response is not None:
            response.headers["X-RateLimit-Limit"] = str(total_allowed_requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, total_allowed_requests - count))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)

        if not allowed:
            logger.warning(
                f"[RATE_LIMIT] Limit exceeded for {identifier}: "
                f"{count}/{total_allowed_requests} in {effective_window}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: {count} requests in {effective_window}s "
                    f"(max {total_allowed_requests}). Retry after {ttl}s."
                ),
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(total_allowed_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + ttl),
                },
            )

    return _limiter


# ── Pre-built standard dependencies ──────────────────────────────────────────

# 100 req/min — general API endpoints
check_rate_limit = rate_limit(max_requests=100, window_seconds=60)

# 20 req/min — heavy compute endpoints (governance evaluate, CrewAI kickoff)
check_rate_limit_strict = rate_limit(max_requests=20, window_seconds=60)

# 200 req/min — read-only / cheap endpoints
check_rate_limit_relaxed = rate_limit(max_requests=200, window_seconds=60)

# Global Tier-Based Rate Limiting with In-Memory Degraded Fallback
check_rate_limit_tiered = rate_limit(tier_based=True, fallback_to_memory=True)
