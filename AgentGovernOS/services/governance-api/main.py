"""
AgentGovern OS — Governance API
================================
Enterprise-grade Digital Colleague Governance Platform.

This is the central FastAPI service that provides:
- GENESIS:   Agent Identity & DNA Registry
- PULSE:     Dynamic Trust Scoring Engine
- SENTINEL:  Policy Engine & Pre-Execution Evaluation
- ANCESTOR:  Immutable Decision Ledger
- CONTRACT:  Social Contracts
- ECLIPSE:   Human-in-the-Loop Workbench
- QICACHE:   Query Intelligence Cache
- AUTH:      JWT / API-Key Authentication 
- GDPR:      Data Export & Right-to-Erasure 

Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from contextlib import asynccontextmanager

from config import get_settings
from database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

settings = get_settings()

if settings.app_env.lower() == "production" and ("sqlite" in settings.database_url.lower()):
    raise RuntimeError(
        f"APP_ENV=production but DATABASE_URL points to SQLite ({settings.database_url}). "
        "Refusing to start. Set DATABASE_URL to a PostgreSQL connection string."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "development":
        try:
            await init_db()
            try:
                from seed import seed_data
                await seed_data()
            except Exception as se:
                import logging
                logging.getLogger("uvicorn").info(f"Seed info: {se}")
        except Exception as e:
            import logging
            logging.getLogger("uvicorn").warning(
                f"DB not reachable at startup (running without DB): {e}"
            )
    yield


app = FastAPI(
    title="AgentGovern OS — Governance API",
    description=(
        "Enterprise-grade Digital Colleague Governance Platform. "
        "Manages agent identity, trust scoring, policy enforcement, "
        "decision auditing, and human-in-the-loop escalations."
    ),
    version="0.5.0",
    lifespan=lifespan,
)

# ── Security Headers + Comprehensive API Access Log ─────────────────
from middleware.rbac import RBACMiddleware
from middleware.security_headers import APIAccessLogMiddleware, SecurityHeadersMiddleware
from middleware.tenant import TenantMiddleware

app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=(settings.app_env != "development"))
app.add_middleware(APIAccessLogMiddleware, persist_to_db=True)
app.add_middleware(TenantMiddleware)
app.add_middleware(RBACMiddleware)

# ── CORS (must be registered after SecurityHeaders for correct ordering) ──────
allowed_origins_list = [
    "*",
    "https://agentverse.nuuvixx.com",
    "https://agentstore.nuuvixx.com",
    "https://app.nuuvixx.com",
    "https://store.nuuvixx.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3051",
    "http://127.0.0.1:3051",
    "http://localhost:8050",
    "http://127.0.0.1:8050",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*", "X-API-Key", "X-Agent-ID", "X-Timestamp", "X-Signature", "Authorization", "Content-Type"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from routers import (
    a2a,  # A2A Protocol
    audit,
    auth,  # JWT / API-Key Auth
    cache,
    catalog_gate,  # Bridge 4: AgentStore Enterprise Catalog Gate
    compliance,  # Compliance Dashboard
    contract,  # Social Contracts
    cost,  # Cost Governance
    debug,  # Remote Production Debugger
    did,  # Decentralized Identity
    eclipse,
    eval,  # Red-Team Evaluation
    freebuff,  # Free AI tier for AgentVerse IDE
    gateways,  # Live Gateways dashboard data
    gdpr,  # GDPR Data Export & Erasure
    genesis,
    governance,  # Universal Connector
    graph,  # Agent Dependency Graph
    iam,  # AWS IAM & STS Token Service
    orgs,  # Multi-tenant Organization Management
    owasp,  # OWASP ASI Coverage Map
    policies,  # Policy Revisions & Version History
    pulse,
    realtime,  # WebSocket live telemetry
    secrets,  # Secret Vault Management
    sentinel,
)

app.include_router(genesis.router)
app.include_router(pulse.router)
app.include_router(sentinel.router)
app.include_router(cache.router)
app.include_router(audit.router)
app.include_router(eclipse.router)
app.include_router(governance.router)
app.include_router(contract.router)
app.include_router(auth.router)   # POST /auth/token, GET /auth/me
app.include_router(gdpr.router)   # GET /gdpr/export, DELETE /gdpr/forget
app.include_router(gateways.router)
app.include_router(realtime.router)
app.include_router(owasp.router)  # GET /governance/owasp-coverage
app.include_router(a2a.router)    # A2A Protocol
app.include_router(cost.router)   # Cost Governance
app.include_router(graph.router)  # Agent Dependency Graph
app.include_router(eval.router)   # Red-Team Evaluation
app.include_router(debug.router)  # Remote Production Debugger
app.include_router(compliance.router)
app.include_router(did.router)
app.include_router(secrets.router)
app.include_router(catalog_gate.router)  # Bridge 4: AgentStore Catalog Gate
app.include_router(policies.router)      # Policy Revisions & Rollbacks
app.include_router(orgs.router)          # Multi-tenant Organization API
app.include_router(iam.router)           # AWS IAM STS & Policy Engine
app.include_router(freebuff.router)      # Free AI tier for AgentVerse IDE

# ── Metrics  ─────────────────────────────────────────────────────
try:
    import prometheus_fastapi_instrumentator.routing as pfi_routing
    _orig_get_route_name = pfi_routing._get_route_name
    def _safe_get_route_name(scope, routes, *args, **kwargs):
        safe_routes = [r for r in routes if hasattr(r, "path")]
        return _orig_get_route_name(scope, safe_routes)
    pfi_routing._get_route_name = _safe_get_route_name
except Exception:
    pass

Instrumentator(should_group_status_codes=True, should_ignore_untemplated=True).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ── Root & Health ─────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    return {
        "name": "AgentGovern OS",
        "version": "0.5.0",
        "status": "operational",
        "modules": [
            "GENESIS", "PULSE", "SENTINEL", "QICACHE",
            "ANCESTOR", "ECLIPSE", "CONTRACT",
            "AUTH", "GDPR", "FREEBUFF",
        ],
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    db_ok = True
    redis_ok = True

    try:
        from database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        import redis
        r = redis.from_url(settings.redis_url, socket_timeout=1)
        r.ping()
    except Exception:
        redis_ok = False

    overall = "ok" if db_ok and redis_ok else "degraded"

    return {
        "status": overall,
        "version": "0.5.0",
        "services": {
            "api": "up",
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }
