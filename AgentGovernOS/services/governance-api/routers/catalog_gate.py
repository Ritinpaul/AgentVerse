"""
AgentGovernOS — Catalog Gate Router.

Bridge 4 (AgentGovernOS → AgentStore):
Exposes HTTP endpoints for enterprise org catalog enforcement.
Called by AgentOS Control Plane, CrewAI engine, and enterprise adapters
before any agent is permitted to run.

Routes:
  POST /catalog-gate/check          — Check if agent is approved for an org
  GET  /catalog-gate/status/{org_id} — View approved/restricted catalog for an org
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.agentstore_gateway import check_agent_approval

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog-gate", tags=["Catalog Gate (Bridge 4)"])


class CatalogCheckRequest(BaseModel):
    org_id: str
    agent_slug: str                 # e.g. "nuuvixx/support-agent"
    requester_id: str | None = "api-caller"
    auto_submit_procurement: bool = True


class CatalogCheckResponse(BaseModel):
    allowed: bool
    reason: str
    trust_score: int = 0
    procurement_id: str | None = None
    message: str | None = None


@router.post("/check", response_model=CatalogCheckResponse, summary="Check Agent Approval for Org")
async def check_catalog_gate(req: CatalogCheckRequest) -> CatalogCheckResponse:
    """
    Bridge 4 enforcement point.

    Checks if an agent is approved to run in a given org by querying the
    AgentStore private catalog. If not approved and trust score is too low,
    auto-submits a procurement request and blocks execution.

    Called by:
    - AgentOS Control Plane (before spawning any agent for an enterprise org)
    - SAP BTP Adapter (before routing tasks to agents)
    - CrewAI Engine (before delegating tasks to marketplace agents)
    """
    logger.info(f"[CatalogGate] Checking {req.agent_slug} for org {req.org_id}")

    try:
        decision = await check_agent_approval(
            org_id=req.org_id,
            agent_slug=req.agent_slug,
            requester_id=req.requester_id,
            auto_submit_procurement=req.auto_submit_procurement,
        )
    except Exception as e:
        logger.exception(f"[CatalogGate] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Catalog gate check failed: {e}")

    if not decision["allowed"]:
        logger.warning(
            f"[CatalogGate] BLOCKED {req.agent_slug} for org {req.org_id}: {decision['reason']}"
        )

    return CatalogCheckResponse(**decision)


@router.get("/status/{org_id}", summary="Get Org Catalog Status")
async def get_org_catalog_status(org_id: str) -> dict:
    """
    Returns the current approved and restricted agent catalog for an org.
    Useful for IT admins reviewing what is permitted.
    """
    import os

    import httpx
    agentstore_url = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
    api_key = os.getenv("NUUVIXX_API_KEY", "")

    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{agentstore_url}/api/v1/procurement/private-catalog/{org_id}",
                headers=headers
            )
            if r.status_code == 404:
                return {
                    "org_id": org_id,
                    "approved_slugs": [],
                    "restricted_slugs": [],
                    "note": "No private catalog found for this org in AgentStore."
                }
            r.raise_for_status()
            catalog = r.json()
            catalog["org_id"] = org_id
            return catalog
    except httpx.RequestError as e:
        logger.warning(f"[CatalogGate] Cannot reach AgentStore at {agentstore_url}: {e}")
        return {
            "org_id": org_id,
            "status": "degraded",
            "approved_slugs": [],
            "restricted_slugs": [],
            "warning": f"Cannot reach AgentStore at {agentstore_url}: {e}",
            "note": "AgentStore temporarily unavailable; fallback degraded catalog applied."
        }

