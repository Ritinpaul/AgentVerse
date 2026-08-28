"""
Edge Gateway — Lightweight Governance Runtime for Edge Locations

The Edge Gateway runs at the network edge (factory floor, regional datacenter,
client VPN endpoint) and provides:

  1. Passport verification (offline-capable with cached public key)
  2. Local policy enforcement (subset of full policy set)
  3. Pre-action authorization (fast <5ms check for common cases)
  4. Local decision ledger (batch-syncs to control plane)
  5. QICACHE hot layer (governance decisions cached locally)

Design principle: If disconnected from the control plane, the Edge Gateway
operates in DEGRADED mode — it can still verify passports (using cached key
+ revocation list) and enforce the last-known policy set. It CANNOT issue
new passports or update trust scores until reconnection.

                ┌────────────────────────────────┐
                │   Control Plane (Cloud)         │
                │   governance-api:8000           │
                └─────────────┬──────────────────┘
                              │  (30s sync)
                ┌─────────────┴──────────────────┐
                │   Edge Gateway (This Service)   │
                │   edge-gateway:8001             │
                │                                 │
                │   ┌──────────┐ ┌─────────────┐  │
                │   │ Passport │ │  Local      │  │
                │   │ Verifier │ │  Enforcer   │  │
                │   └──────────┘ └─────────────┘  │
                │                                 │
                │   ┌──────────────────────────┐  │
                │   │ Local Ledger (batch sync) │  │
                │   └──────────────────────────┘  │
                └─────────────┬──────────────────┘
                              │
                   AI Agents (any environment)
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from identity.local_enforcer import EnforcerVerdict, LocalPolicyEnforcer
from identity.local_ledger import LocalLedger
from identity.passport_verifier import PassportVerifier, VerificationResult
from identity.sync_client import ControlPlaneSyncClient
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://governance-api:8000")
GATEWAY_ID = os.getenv("GATEWAY_ID", "edge-gateway-001")
GATEWAY_ENVIRONMENT = os.getenv("GATEWAY_ENVIRONMENT", "edge")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-shared-secret-change-in-production")
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "30"))

# ──────────────────────────────────────────────
# Dependencies (initialized at startup)
# ──────────────────────────────────────────────

verifier: PassportVerifier = None
enforcer: LocalPolicyEnforcer = None
ledger: LocalLedger = None
sync_client: ControlPlaneSyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global verifier, enforcer, ledger, sync_client

    logger.info(f"[EDGE-GATEWAY] Starting: id={GATEWAY_ID} env={GATEWAY_ENVIRONMENT}")

    verifier = PassportVerifier(
        jwt_secret=JWT_SECRET,
        control_plane_url=CONTROL_PLANE_URL,
    )
    enforcer = LocalPolicyEnforcer
    ledger = LocalLedger(gateway_id=GATEWAY_ID)
    sync_client = ControlPlaneSyncClient(
        control_plane_url=CONTROL_PLANE_URL,
        gateway_id=GATEWAY_ID,
    )

    # Initial sync on startup
    await sync_client.sync_policies(enforcer)
    await sync_client.sync_revocation_list(verifier)

    logger.info("[EDGE-GATEWAY] Ready")
    yield

    # Flush local ledger to control plane on shutdown
    await sync_client.flush_ledger(ledger)
    logger.info("[EDGE-GATEWAY] Shutdown complete")


app = FastAPI(
    title="AgentGovern Edge Gateway",
    description="Distributed governance runtime for edge-deployed AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────

class AuthorizeRequest(BaseModel):
    passport_token: str
    action_type: str              # "execute" | "read" | "write" | "escalate"
    resource: str                 # What the agent wants to act on
    amount: float = 0.0
    environment: str = "edge"
    context: dict = {}


class AuthorizeResponse(BaseModel):
    authorized: bool
    verdict: str                  # "allow" | "deny" | "escalate"
    reason: str
    agent_id: str
    agent_tier: str
    gateway_id: str
    latency_ms: float
    mode: str                     # "online" | "degraded"
    decision_id: str


class HeartbeatRequest(BaseModel):
    agent_id: str
    passport_token: str
    host_id: str
    region: str = ""
    agent_version: str = "1.0.0"
    metadata: dict = {}


# ──────────────────────────────────────────────
# Core endpoints
# ──────────────────────────────────────────────

@app.post("/authorize", response_model=AuthorizeResponse)
async def authorize(req: AuthorizeRequest, request: Request):
    """
    Core authorization endpoint — called by every agent before any action.

    Flow:
      1. Verify passport (signature + expiry + revocation check)
      2. Check environment permission (is this agent allowed here?)
      3. Evaluate local policy rules
      4. Record decision in local ledger
      5. Return verdict (allow / deny / escalate)

    Latency target: <10ms for cached decisions, <50ms cold path
    """
    import time
    start = time.monotonic

    # ── Step 1: Passport verification
    result: VerificationResult = await verifier.verify(req.passport_token)
    if not result.valid:
        raise HTTPException(status_code=401, detail=f"Invalid passport: {result.reason}")

    claims = result.claims
    agent_id = claims.get("sub", "unknown")
    ag = claims.get("ag", {})

    # ── Step 2: Environment check
    allowed_envs = ag.get("allowed_environments", [])
    if req.environment not in allowed_envs:
        _log_and_record(ledger, agent_id, "deny", f"Environment {req.environment} not permitted", req)
        return AuthorizeResponse(
            authorized=False,
            verdict="deny",
            reason=f"Agent passport does not permit execution in '{req.environment}' environment",
            agent_id=agent_id,
            agent_tier=ag.get("tier", "T4"),
            gateway_id=GATEWAY_ID,
            latency_ms=round((time.monotonic - start) * 1000, 2),
            mode=verifier.mode,
            decision_id=ledger.last_decision_id,
        )

    # ── Step 3: Policy enforcement
    verdict: EnforcerVerdict = enforcer.evaluate(
        agent_tier=ag.get("tier", "T4"),
        trust_score=ag.get("trust_score", 0.0),
        authority_limit=ag.get("authority_limit", 0),
        action_type=req.action_type,
        amount=req.amount,
        context=req.context,
    )

    # ── Step 4: Record in local ledger
    decision_id = ledger.record_decision(
        agent_id=agent_id,
        action_type=req.action_type,
        resource=req.resource,
        amount=req.amount,
        environment=req.environment,
        verdict=verdict.verdict,
        reason=verdict.reason,
        passport_jti=claims.get("jti", ""),
    )

    latency = round((time.monotonic - start) * 1000, 2)
    logger.info(
        f"[AUTH] agent={agent_id[:8]} action={req.action_type} "
        f"verdict={verdict.verdict} latency={latency}ms mode={verifier.mode}"
    )

    return AuthorizeResponse(
        authorized=(verdict.verdict == "allow"),
        verdict=verdict.verdict,
        reason=verdict.reason,
        agent_id=agent_id,
        agent_tier=ag.get("tier", "T4"),
        gateway_id=GATEWAY_ID,
        latency_ms=latency,
        mode=verifier.mode,
        decision_id=decision_id,
    )


@app.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest):
    """Agent phones home — updates environment registry and validates passport."""
    result = await verifier.verify(req.passport_token)
    if not result.valid:
        return {"status": "rejected", "reason": result.reason}

    return {
        "status": "ok",
        "gateway_id": GATEWAY_ID,
        "environment": GATEWAY_ENVIRONMENT,
        "timestamp": datetime.now(UTC).isoformat,
        "passport_valid": True,
        "mode": verifier.mode,
    }


@app.post("/sync")
async def trigger_sync():
    """Manually trigger sync with control plane (for ops/debugging)."""
    results = {}
    results["policies"] = await sync_client.sync_policies(enforcer)
    results["revocation"] = await sync_client.sync_revocation_list(verifier)
    return {"status": "synced", "details": results, "gateway_id": GATEWAY_ID}


@app.get("/status")
async def status():
    """Gateway health: mode, ledger size, policy count, last sync."""
    return {
        "gateway_id": GATEWAY_ID,
        "environment": GATEWAY_ENVIRONMENT,
        "mode": verifier.mode if verifier else "unknown",
        "control_plane_url": CONTROL_PLANE_URL,
        "local_ledger_size": ledger.size if ledger else 0,
        "policy_count": enforcer.policy_count if enforcer else 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "gateway_id": GATEWAY_ID}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _log_and_record(ledger, agent_id, verdict, reason, req):
    ledger.record_decision(
        agent_id=agent_id,
        action_type=req.action_type,
        resource=req.resource,
        amount=req.amount,
        environment=req.environment,
        verdict=verdict,
        reason=reason,
        passport_jti="",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
