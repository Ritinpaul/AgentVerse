"""
Centralized SlowAPI rate-limit configuration for AgentStore.

GAP-NEW-02 fix: previously, only a global SlowAPIMiddleware default of 100/minute
was wired, but it never fired on mutation routes because they don't accept
`request: Request`. This module centralizes per-route rate limiting so that
mutation endpoints can be decorated with `@mutation_limit("30/minute")` and the
underlying Limiter is shared with main.py's exception handler.

Usage in a router:
    from fastapi import Request
    from app.core.rate_limit import mutation_limit

    @router.post("/publish")
    @mutation_limit("5/minute")
    async def publish_agent(
        request: Request,
        payload: PublishRequest,
        ...
    ):
        ...

The `request: Request` parameter is REQUIRED by SlowAPI — without it, the
decorator silently no-ops on that route.
"""
from __future__ import annotations

import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared Limiter instance. main.py wires this into app.state.limiter
# and registers the RateLimitExceeded exception handler.
mutation_limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("APP_ENV") != "test"
)


def mutation_limit(times: str = "30/minute"):
    """
    Decorator factory for write endpoints.

    Default limit is 30/minute per IP. Override per-route for high-cost or
    financial endpoints (see WRITE_LIMITS).
    """
    return mutation_limiter.limit(times)


# ── Per-route policy registry ─────────────────────────────────────────────────
# Used by tests and by future ops dashboards; the decorator string is the
# source of truth at the call site.

WRITE_LIMITS = {
    "publish_agent": "5/minute",       # expensive + risky
    "create_version": "10/minute",
    "settle_payment": "10/minute",     # financial
    "topup_credits": "10/minute",      # financial
    "request_payout": "5/minute",      # financial
    "confirm_payout": "5/minute",
    "advertise": "10/minute",
    "negotiate": "10/minute",
    "trigger_scan": "5/minute",
    "default_write": "30/minute",
}


def limit_for(name: str) -> str:
    """Resolve the rate-limit string for a named endpoint, falling back to default."""
    return WRITE_LIMITS.get(name, WRITE_LIMITS["default_write"])