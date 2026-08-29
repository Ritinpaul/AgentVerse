from typing import cast, Any
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.config import settings
from app.routers import registry, search, cli_api, templates
from app.routers import verification, incidents, billing, pricing, compositions, overview, trust_api
from app.routers import procurement, a2a_commerce

from app.db.base_class import Base
from app.db.session import engine, get_db
from app.core.startup_guard import refuse_sqlite_in_production

refuse_sqlite_in_production(settings.DATABASE_URL, settings.APP_ENV)

# Import all models so SQLAlchemy registers them with Base before first use
import app.models.agent_listing        # noqa: F401
import app.models.trust_models         # noqa: F401
import app.models.billing_models       # noqa: F401
import app.models.composition_models   # noqa: F401
import app.models.procurement_models   # noqa: F401
import app.models.a2a_models           # noqa: F401

# Auto-create missing tables on startup
Base.metadata.create_all(bind=engine)

def _seed_demo_data():
    """
    Server-authoritative sync of real agents.
    Prunes legacy mock agents and ensures only real agents from the agents/ folder
    are published and active in the AgentStore registry.
    """
    import os
    import yaml as pyyaml
    from app.db.session import SessionLocal
    from app.models.agent_listing import AgentListing, AgentVersion
    from app.models.billing_models import AgentPricing
    from app.models.a2a_models import AgentCapabilityAdvertisement
    db = SessionLocal()
    try:
        # 1. Prune legacy mock and placeholder agents
        legacy_mock_slugs = ["nuuvixx/support-agent", "acme/sales-assistant"]
        for mock_slug in legacy_mock_slugs:
            mock_item = db.query(AgentListing).filter(AgentListing.slug == mock_slug).first()
            if mock_item:
                db.query(AgentVersion).filter(AgentVersion.listing_id == mock_item.id).delete()
                db.query(AgentPricing).filter(AgentPricing.listing_id == mock_item.id).delete()
                db.delete(mock_item)
                db.commit()

        db.query(AgentCapabilityAdvertisement).filter(
            AgentCapabilityAdvertisement.agent_slug.in_(legacy_mock_slugs)
        ).delete(synchronize_session=False)
        db.commit()

        # 2. Candidate real agent definitions (mirrors agents/ directory)
        real_agents = [
            {
                "slug": "nuuvixx/security-sentinel",
                "folder": "security_sentinel",
                "name": "security-sentinel",
                "description": "Autonomous DevSecOps agent that performs static vulnerability auditing, secret scanning, dependency CVE analysis, and automated PII redaction on codebases.",
                "builder_id": "nuuvixx",
                "category": "Security & DevSecOps",
                "tags": ["security", "devsecops", "secret-scanning", "pii-redaction"],
                "capabilities": ["code:audit", "secret:scan", "cve:check", "pii:redact"],
                "current_version": "1.0.0",
                "trust_score": 98.5,
                "free_tier_runs": 100,
                "price_per_run": 0.05,
                "a2a_capability": "security:audit",
                "yaml_default": """name: security-sentinel
slug: nuuvixx/security-sentinel
version: 1.0.0
description: Autonomous DevSecOps agent that performs static vulnerability auditing, secret scanning, dependency CVE analysis, and automated PII redaction on codebases.
author: Nuuvixx Security Labs
category: Security & DevSecOps
tags:
  - security
  - devsecops
  - secret-scanning
  - pii-redaction

model:
  name: gpt-4o-2024-08-06
  temperature: 0.1
  max_tokens: 8192
  fallback_model: groq/llama-3.1-70b

tools:
  - name: static_vulnerability_scanner
    type: mcp
    server: filesystem
  - name: identity_inspector
    type: mcp
    server: memory
  - name: pii_redactor
    type: mcp
    server: sequential-thinking

policies:
  sandbox:
    profile: strict
    network_mode: egress_filtered
    max_memory_mb: 512
  pii:
    redact_emails: true
    redact_ssn: true
  cost:
    max_cost_per_run_usd: 0.50

capabilities:
  - code:audit
  - identity:scan
  - cve:check
  - pii:redact
"""
            },
            {
                "slug": "nuuvixx/finops-cost-optimizer",
                "folder": "finops_cost_optimizer",
                "name": "finops-cost-optimizer",
                "description": "Autonomous cloud cost management agent that inspects Kubernetes workload telemetry, flags idle compute nodes, calculates scale-to-zero savings, and drafts microVM snapshotting recommendations.",
                "builder_id": "nuuvixx",
                "category": "Finance & Cloud Infra",
                "tags": ["finops", "cloud-cost", "kubernetes", "scale-to-zero"],
                "capabilities": ["infra:analyze", "cost:optimize", "k8s:scale-to-zero", "billing:forecast"],
                "current_version": "1.0.0",
                "trust_score": 96.0,
                "free_tier_runs": 50,
                "price_per_run": 0.10,
                "a2a_capability": "finops:cost-optimize",
                "yaml_default": """name: finops-cost-optimizer
slug: nuuvixx/finops-cost-optimizer
version: 1.0.0
description: Autonomous cloud cost management agent that inspects Kubernetes workload telemetry, flags idle compute nodes, calculates scale-to-zero savings, and drafts microVM snapshotting recommendations.
author: Nuuvixx Cloud FinOps Labs
category: Finance & Cloud Infra
tags:
  - finops
  - cloud-cost
  - kubernetes
  - scale-to-zero

model:
  name: claude-3-5-sonnet-20241022
  temperature: 0.2
  max_tokens: 16384
  fallback_model: gemini-2.5-pro

tools:
  - name: k8s_telemetry_collector
    type: mcp
    server: postgres
  - name: idle_pod_detector
    type: mcp
    server: sequential-thinking
  - name: scale_to_zero_planner
    type: mcp
    server: filesystem

policies:
  sandbox:
    profile: strict
    network_mode: egress_filtered
  cost:
    max_cost_per_run_usd: 1.00

capabilities:
  - infra:analyze
  - cost:optimize
  - k8s:scale-to-zero
  - billing:forecast
"""
            },
        ]

        # Locate agents directory on host or container filesystem
        repo_roots = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "agents")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agents")),
            os.path.abspath("agents"),
        ]
        found_agents_dir = next((d for d in repo_roots if os.path.isdir(d)), None)

        for item in real_agents:
            agent_yaml_str = item["yaml_default"]
            if found_agents_dir:
                candidate_yaml = os.path.join(found_agents_dir, item["folder"], "agent.yaml")
                if os.path.exists(candidate_yaml):
                    try:
                        with open(candidate_yaml, "r", encoding="utf-8") as yf:
                            agent_yaml_str = yf.read()
                    except Exception:
                        pass

            listing = db.query(AgentListing).filter(AgentListing.slug == item["slug"]).first()
            if not listing:
                listing = AgentListing(
                    slug=item["slug"],
                    name=item["name"],
                    description=item["description"],
                    builder_id=item["builder_id"],
                    category=item["category"],
                    tags=item["tags"],
                    capabilities=item["capabilities"],
                    current_version=item["current_version"],
                    trust_score=item["trust_score"],
                    verification_status="verified",
                )
                db.add(listing)
                db.commit()
                db.refresh(listing)
            else:
                listing.description = item["description"]
                listing.category = item["category"]
                listing.tags = item["tags"]
                listing.capabilities = item["capabilities"]
                listing.trust_score = item["trust_score"]
                db.commit()

            # Ensure version exists
            ver = db.query(AgentVersion).filter(
                AgentVersion.listing_id == listing.id,
                AgentVersion.version_semver == item["current_version"]
            ).first()
            if not ver:
                ver = AgentVersion(
                    listing_id=listing.id,
                    version_semver=item["current_version"],
                    agent_yaml=agent_yaml_str,
                    status="published",
                )
                db.add(ver)
                db.commit()

            # Ensure pricing exists
            pricing = db.query(AgentPricing).filter(AgentPricing.listing_id == listing.id).first()
            if not pricing:
                db.add(AgentPricing(
                    listing_id=listing.id,
                    free_tier_runs=item["free_tier_runs"],
                    price_per_run=item["price_per_run"]
                ))
                db.commit()

            # Ensure real A2A capability advertisement exists
            if not db.query(AgentCapabilityAdvertisement).filter(
                AgentCapabilityAdvertisement.agent_slug == item["slug"]
            ).first():
                db.add(AgentCapabilityAdvertisement(
                    agent_slug=item["slug"],
                    capability=item["a2a_capability"],
                    endpoint_url=f"http://127.0.0.1:8005/api/v1/a2a/{item['name']}",
                    price_per_call_x402=0.001,
                ))
                db.commit()
    finally:
        db.close()


_seed_demo_data()

from fastapi.openapi.docs import get_redoc_html

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import mutation_limiter as limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Verified marketplace and foundation registry for autonomous AI agents and MCP tools.",
    docs_url="/docs",
    redoc_url=None,  # Custom route below using reliable CDN
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))
app.add_middleware(SlowAPIMiddleware)

@app.get("/redoc", include_in_schema=False)
def custom_redoc(request: Request):
    return get_redoc_html(
        openapi_url=request.app.openapi_url,
        title=f"{request.app.title} - ReDoc",
        redoc_js_url="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js",
    )

import os
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3051",
        "http://127.0.0.1:3051",
        "http://localhost:8050",
        "http://127.0.0.1:8050",
        "https://app.nuuvixx.com",
        "https://store.nuuvixx.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 1 — Foundation Registry
app.include_router(registry.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(cli_api.router, prefix=settings.API_V1_STR)
app.include_router(templates.router, prefix=settings.API_V1_STR)
app.include_router(templates.router)

@app.get("/api/v1/agents", include_in_schema=False)
def list_agents_alias(request: Request, db: Session = Depends(get_db)):
    from app.routers.registry import list_agents
    return list_agents(category=None, skip=0, limit=50, db=db)


# Phase 2 — Verification & Trust
app.include_router(verification.router)
app.include_router(trust_api.router)
app.include_router(incidents.router)

# Phase 3 — Monetization & Overview
app.include_router(billing.router)
app.include_router(overview.router)
app.include_router(pricing.router)


# Phase 4 — Composability
app.include_router(compositions.router)

# Phase 5 — Enterprise Procurement
app.include_router(procurement.router)

# Phase 6 — Agent-to-Agent Commerce
app.include_router(a2a_commerce.router)


@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


@app.get("/")
def root():

    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "phases": {
            "phase1": "Foundation Registry — /api/v1/registry, /api/v1/search, /api/v1/cli",
            "phase2": "Verification & Trust — /api/v1/verification, /api/v1/incidents",
            "phase3": "Monetization — /api/v1/billing, /api/v1/pricing",
            "phase4": "Composability — /api/v1/compositions",
            "phase5": "Enterprise Procurement — /api/v1/procurement",
            "phase6": "Agent-to-Agent Commerce — /api/v1/a2a",
        }
    }
