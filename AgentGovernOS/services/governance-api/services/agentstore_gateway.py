"""
AgentGovernOS — AgentStore Gateway Service.

Bridge 4 (AgentGovernOS → AgentStore):
Queries the AgentStore private catalog before allowing an enterprise agent to execute.
Auto-submits procurement requests for unapproved agents.

This service is called by the SENTINEL policy engine and the catalog_gate router
before any agent is permitted to run in an enterprise org.
"""

import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

try:
    for _parent in Path(__file__).resolve().parents:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(dotenv_path=_env, override=False)
            break
except Exception:
    pass

logger = logging.getLogger(__name__)

AGENTSTORE_URL  = os.getenv("AGENTSTORE_URL", "http://127.0.0.1:8005")
NUUVIXX_API_KEY = os.getenv("NUUVIXX_API_KEY", "")

# Minimum trust score required to automatically allow an agent (not in restricted list)
DEFAULT_MIN_TRUST_SCORE = int(os.getenv("MIN_TRUST_SCORE", "70"))


def _store_headers() -> dict:
    """Service-to-service headers for AgentStore API calls."""
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if NUUVIXX_API_KEY:
        h["X-API-Key"] = NUUVIXX_API_KEY
    return h


async def check_agent_approval(
    org_id: str,
    agent_slug: str,
    requester_id: str | None = "agentgovern-auto",
    auto_submit_procurement: bool = True,
) -> dict:
    """
    Query AgentStore to determine if an agent is approved for use in an org.

    Returns a decision dict:
      { "allowed": bool, "reason": str, "trust_score": int, "procurement_id": str | None }

    Decision logic:
      1. Fetch the agent listing to get trust score
      2. Fetch the org's private catalog
      3. If agent is in restricted_slugs → DENY (restricted)
      4. If agent is in approved_slugs → ALLOW
      5. If agent has trust_score >= DEFAULT_MIN_TRUST_SCORE → ALLOW (auto-approved)
      6. Otherwise → DENY + auto-submit procurement request if enabled
    """
    trust_score = 0
    procurement_id = None

    async with httpx.AsyncClient(timeout=8.0) as client:

        # ── 1. Get agent listing & trust score ────────────────────────────────
        try:
            parts = agent_slug.split("/", 1)
            builder, name = (parts[0], parts[1]) if len(parts) == 2 else ("unknown", agent_slug)
            listing_r = await client.get(
                f"{AGENTSTORE_URL}/api/v1/registry/agents/{builder}/{name}",
                headers=_store_headers()
            )
            if listing_r.status_code == 200:
                listing = listing_r.json()
                trust_score = listing.get("trust_score", 0)
                logger.info(f"[CatalogGate] Agent {agent_slug} trust score: {trust_score}")
            elif listing_r.status_code == 404:
                return {
                    "allowed": False,
                    "reason": "agent_not_in_agentstore",
                    "trust_score": 0,
                    "procurement_id": None,
                    "message": f"Agent '{agent_slug}' is not registered in AgentStore. "
                               "Publish it first: nuuvixx deploy agent.yaml",
                }
        except httpx.RequestError as e:
            logger.warning(f"[CatalogGate] Cannot reach AgentStore: {e}. Allowing with caution.")
            return {
                "allowed": True,
                "reason": "agentstore_unreachable_failopen",
                "trust_score": 0,
                "procurement_id": None,
                "message": "AgentStore unreachable — fail-open for continuity. Alert ops team.",
            }

        # ── 2. Fetch org private catalog ──────────────────────────────────────
        approved_slugs = []
        restricted_slugs = []
        try:
            catalog_r = await client.get(
                f"{AGENTSTORE_URL}/api/v1/procurement/private-catalog/{org_id}",
                headers=_store_headers()
            )
            if catalog_r.status_code == 200:
                catalog = catalog_r.json()
                approved_slugs   = catalog.get("approved_slugs", [])
                restricted_slugs = catalog.get("restricted_slugs", [])
        except httpx.RequestError:
            logger.warning("[CatalogGate] Could not fetch private catalog — skipping catalog check.")

        # ── 3. Restricted list check ──────────────────────────────────────────
        if agent_slug in restricted_slugs:
            return {
                "allowed": False,
                "reason": "agent_in_restricted_catalog",
                "trust_score": trust_score,
                "procurement_id": None,
                "message": f"Agent '{agent_slug}' is on the restricted list for org '{org_id}'.",
            }

        # ── 4. Approved list check ────────────────────────────────────────────
        if agent_slug in approved_slugs:
            return {
                "allowed": True,
                "reason": "agent_in_approved_catalog",
                "trust_score": trust_score,
                "procurement_id": None,
            }

        # ── 5. Trust score auto-approval ──────────────────────────────────────
        if trust_score >= DEFAULT_MIN_TRUST_SCORE:
            return {
                "allowed": True,
                "reason": f"trust_score_auto_approved ({trust_score}>={DEFAULT_MIN_TRUST_SCORE})",
                "trust_score": trust_score,
                "procurement_id": None,
            }

        # ── 6. Auto-submit procurement request ───────────────────────────────
        if auto_submit_procurement:
            try:
                proc_r = await client.post(
                    f"{AGENTSTORE_URL}/api/v1/procurement/requests",
                    json={
                        "org_id": org_id,
                        "agent_slug": agent_slug,
                        "requester_id": requester_id,
                        "tier": "enterprise",
                        "justification": (
                            f"Auto-submitted by AgentGovernOS SENTINEL policy engine. "
                            f"Agent '{agent_slug}' attempted execution in org '{org_id}' "
                            f"but is not in the approved catalog. "
                            f"Trust score: {trust_score}/{DEFAULT_MIN_TRUST_SCORE} minimum."
                        ),
                    },
                    headers=_store_headers()
                )
                if proc_r.status_code in (200, 201):
                    proc_data = proc_r.json()
                    procurement_id = proc_data.get("id") or proc_data.get("request_id")
                    logger.info(f"[CatalogGate] Procurement request submitted: {procurement_id}")
            except Exception as e:
                logger.warning(f"[CatalogGate] Failed to submit procurement request: {e}")

        return {
            "allowed": False,
            "reason": "pending_procurement_approval",
            "trust_score": trust_score,
            "procurement_id": procurement_id,
            "message": (
                f"Agent '{agent_slug}' requires IT approval for org '{org_id}'. "
                f"Trust score: {trust_score} (minimum: {DEFAULT_MIN_TRUST_SCORE}). "
                + (f"Procurement request submitted (ID: {procurement_id})." if procurement_id
                   else "Manual procurement request required.")
            ),
        }
