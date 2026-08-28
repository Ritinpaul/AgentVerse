"""Security headers + comprehensive API access logging middleware.

Two Starlette middleware classes:

1. SecurityHeadersMiddleware
   Injects hardened HTTP response headers on every response:
     - X-Content-Type-Options: nosniff
     - X-Frame-Options: DENY
     - X-XSS-Protection: 1; mode=block
     - Strict-Transport-Security: max-age=31536000; includeSubDomains
     - Referrer-Policy: strict-origin-when-cross-origin
     - Content-Security-Policy: default-src 'self'  (docs pages get relaxed CSP)
     - Permissions-Policy: geolocation=, microphone=, camera=
     - Cache-Control: no-store  (prevents caching of sensitive API responses)
     - X-RateLimit-* headers (populated by rate_limiter if available)

2. APIAccessLogMiddleware
   Logs every inbound API call as a structured record:
     - timestamp, method, path, status_code, duration_ms
     - agent_id (from X-Agent-ID header or JWT sub)
     - Writes to Python logger (structured) — can be piped to Loki / ELK
     - Also persists a compact record to the audit_log table for traceability
"""

import json
import logging
import time
from datetime import UTC
from typing import Any

# pyre-ignore[21]
from starlette.middleware.base import BaseHTTPMiddleware  # pyre-ignore[21]
from starlette.requests import Request  # pyre-ignore[21]
from starlette.responses import Response  # pyre-ignore[21]
from starlette.types import ASGIApp  # pyre-ignore[21]

logger = logging.getLogger(__name__)

# ── Paths exempt from strict CSP (Swagger UI / ReDoc need inline scripts) ───
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}

# ── Paths excluded from access log to reduce noise ───────────────────────────
_LOG_EXCLUDE = {"/health", "/metrics", "/favicon.ico"}


# ──────────────────────────────────────────────────────────────────────────────
# 1. Security Headers Middleware
# ──────────────────────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardened security response headers to every API response."""

    def __init__(self, app: ASGIApp, hsts_enabled: bool = True):
        BaseHTTPMiddleware.__init__(self, app)
        self._hsts = hsts_enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        path = request.url.path

        # ── Universal security headers ──
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=, microphone=, camera="
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        # ── HSTS (only meaningful over HTTPS) ──
        if self._hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ── CSP: relax for Swagger / ReDoc, strict for everything else ──
        if path in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data: fastapi.tiangolo.com;"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none';"
            )

        # ── Propagate rate limit headers from request state ──
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

        # ── Remove server information ──
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response


# ──────────────────────────────────────────────────────────────────────────────
# 2. API Access Log Middleware
# ──────────────────────────────────────────────────────────────────────────────

class APIAccessLogMiddleware(BaseHTTPMiddleware):
    """Log every API call with timing, identity, and outcome.

    Structured log line example:
      {
        "ts": "2026-03-17T12:00:00Z",
        "method": "POST",
        "path": "/api/v1/sentinel/evaluate",
        "status": 200,
        "duration_ms": 42,
        "agent_id": "X-Agent-ID header value",
        "sub": "jwt-subject",
        "ip": "127.0.0.1"
      }
    """

    def __init__(self, app: ASGIApp, persist_to_db: bool = True):
        BaseHTTPMiddleware.__init__(self, app)
        self._persist = persist_to_db

    def _extract_identity(self, request: Request) -> dict[str, str | None]:
        """Best-effort extract caller identity without blocking."""
        agent_id = request.headers.get("x-agent-id")
        sub = None

        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                from config import get_settings  # pyre-ignore[21]
                from jose import jwt  # pyre-ignore[21]
                settings = get_settings()
                claims = jwt.decode(
                    auth[7:],
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_exp": False},
                )
                sub = claims.get("sub")
                if not agent_id:
                    agent_id = claims.get("agent_id")
            except Exception:
                pass

        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        return {"agent_id": agent_id, "sub": sub, "ip": client_ip}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip noise paths
        if path in _LOG_EXCLUDE:
            return await call_next(request)

        start = time.monotonic()
        identity = self._extract_identity(request)

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                json.dumps({
                    "ts": _now_iso(),
                    "method": request.method,
                    "path": path,
                    "status": 500,
                    "duration_ms": duration_ms,
                    **identity,
                    "error": str(exc),
                })
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)

        log_record: dict[str, Any] = {
            "ts": _now_iso(),
            "method": request.method,
            "path": path,
            "status": status_code,
            "duration_ms": duration_ms,
            **identity,
        }

        if status_code >= 500:
            logger.error(json.dumps(log_record))
        elif status_code >= 400:
            logger.warning(json.dumps(log_record))
        else:
            logger.info(json.dumps(log_record))

        # ── Persist to audit_log for governance-relevant mutations ──
        if self._persist and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            await _persist_access_log(log_record, request)

        return response


async def _persist_access_log(record: dict, request: Request) -> None:
    """Write a compact access log entry to the audit_log table."""
    try:
        import uuid

        from database import async_session_factory  # pyre-ignore[21]
        from models import AuditLog  # pyre-ignore[21]

        async with async_session_factory() as db:
            entry = AuditLog(
                id=uuid.uuid4(),
                action=f"{record['method']} {record['path']}",
                actor=record.get("sub") or record.get("agent_id") or record.get("ip") or "anonymous",
                target_resource=record["path"],
                details={
                    "method": record["method"],
                    "status_code": record["status"],
                    "duration_ms": record["duration_ms"],
                    "ip": record.get("ip"),
                    "agent_id": record.get("agent_id"),
                },
                outcome="success" if record["status"] < 400 else "failure",
            )
            db.add(entry)
            await db.commit()
    except Exception as exc:
        logger.debug(f"[ACCESS_LOG] Persist skipped: {exc}")


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now(UTC).isoformat()
