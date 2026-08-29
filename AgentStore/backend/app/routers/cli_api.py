"""
AgentStore — CLI API Router.

Provides endpoints consumed by the AgentOS CLI:
  GET  /cli/search               — Search agents by keyword
  POST /cli/install              — Install agent manifest locally
  GET  /cli/run/{slug}           — Fetch execution manifest with trust gate data (Bridge 2)
  GET  /cli/run/{slug}/lockfile  — Fetch dependency lockfile only
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.core.rate_limit import mutation_limit
from app.models.agent_listing import AgentListing, AgentVersion

router = APIRouter(prefix="/cli", tags=["CLI Integration"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CLISearchResult(BaseModel):
    slug: str
    name: str
    current_version: str
    trust_score: float
    description: str


class CLIInstallRequest(BaseModel):
    slug: str = Field(..., description="Agent slug format builder/agent")
    version: Optional[str] = Field(None, description="Target semver or latest")


class CLIInstallResponse(BaseModel):
    slug: str
    version: str
    agent_yaml: str
    install_path: str
    instructions: List[str]


class CLIRunManifestResponse(BaseModel):
    """
    Bridge 2: Full execution manifest returned to 'nuuvixx run <slug>'.

    Includes trust score, lockfile, and scan results so the CLI can:
      - Enforce the trust gate (block if score < threshold)
      - Pass lockfile to AgentOS Control Plane /agents/spawn
      - Show scan details to the user
    """
    slug: str
    version: str
    listing_id: str
    builder: str
    name: str
    command: str
    agent_yaml: str
    runner: str = "agentos"
    # Trust gate data
    trust_score: float = Field(..., description="ASI trust score 0-100")
    scan_results: Dict[str, str] = Field(default_factory=dict, description="ASI rule → pass/fail")
    # Lockfile for dependency pinning on AgentOS
    lockfile: Dict[str, Any] = Field(default_factory=dict, description="Pinned dependency lockfile")
    # Pricing info for billing meter
    price_per_call_usd: float = 0.0
    pricing_model: str = "per_call"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=List[CLISearchResult])
def cli_search(
    q: Optional[str] = Query(None),
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    """Search agents by keyword."""
    from app.services.search_engine import search_agents
    results = search_agents(db=db, q=q, limit=limit)
    return [
        CLISearchResult(
            slug=str(getattr(r, "slug", "")),
            name=str(getattr(r, "name", "")),
            current_version=str(getattr(r, "current_version", "")),
            trust_score=float(getattr(r, "trust_score", 0.0) or 0.0),
            description=str(getattr(r, "description", "") or "")[:100] + ("..." if len(str(getattr(r, "description", "") or "")) > 100 else "")
        )
        for r in results
    ]


@router.post("/install", response_model=CLIInstallResponse)
@mutation_limit("10/minute")
def cli_install(request: Request, payload: CLIInstallRequest, db: Session = Depends(get_db)):
    """Download and install an agent manifest locally."""
    listing = db.query(AgentListing).filter(AgentListing.slug == payload.slug).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{payload.slug}' not found in AgentStore."
        )

    target_ver_str = payload.version or listing.current_version
    ver_obj = db.query(AgentVersion).filter(
        AgentVersion.listing_id == listing.id,
        AgentVersion.version_semver == target_ver_str
    ).first()

    if not ver_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{target_ver_str}' not found for '{payload.slug}'."
        )

    folder_name = str(listing.slug).split("/")[-1]
    return CLIInstallResponse(
        slug=str(listing.slug),
        version=str(ver_obj.version_semver),
        agent_yaml=str(ver_obj.agent_yaml),
        install_path=f"./agents/{folder_name}/agent.yaml",
        instructions=[
            f"Created directory ./agents/{folder_name}",
            f"Saved manifest to ./agents/{folder_name}/agent.yaml",
            f"Run agent with: nuuvixx run {listing.slug}"
        ]
    )


@router.get("/run/{slug:path}", response_model=CLIRunManifestResponse)
def cli_run_manifest(
    slug: str,
    version: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Bridge 2 — Fetch execution manifest for 'nuuvixx run <slug>'.

    Returns the full execution manifest including:
    - Trust score and ASI scan results (for trust gate enforcement in CLI)
    - Dependency lockfile (for pinned execution on AgentOS)
    - Pricing info (for billing meter after execution)

    Called by: AgentOS CLI run.py before spawning an agent.
    """
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{slug}' not found. "
                   f"Publish it first: nuuvixx deploy agent.yaml"
        )

    target_ver_str = version or listing.current_version
    ver_obj = db.query(AgentVersion).filter(
        AgentVersion.listing_id == listing.id,
        AgentVersion.version_semver == target_ver_str
    ).first()

    if not ver_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{target_ver_str}' not found for '{slug}'."
        )

    # ── Build scan results dict from stored security scan data ───────────────
    # Use stored scan_results if available, otherwise derive from trust score
    scan_results: Dict[str, str] = {}
    raw_scan = getattr(listing, "scan_results", None) or {}
    if isinstance(raw_scan, dict):
        scan_results = raw_scan
    else:
        # Synthetic scan summary from trust score
        score = float(getattr(listing, "trust_score", 0.0) or 0.0)
        passed = max(0, round((score / 100.0) * 10))
        for i in range(1, 11):
            rule = f"ASI{i:02d}"
            scan_results[rule] = "pass" if i <= passed else "fail"

    # ── Build lockfile from stored composition/lockfile data ─────────────────
    lockfile: Dict[str, Any] = {}
    raw_lockfile = getattr(listing, "lockfile", None) or getattr(ver_obj, "lockfile", None) or {}
    if isinstance(raw_lockfile, dict):
        lockfile = raw_lockfile
    else:
        # Minimal lockfile with runtime info
        lockfile = {
            "schema_version": "1",
            "agent_slug": slug,
            "agent_version": target_ver_str,
            "locked_at": str(listing.updated_at) if hasattr(listing, "updated_at") else "",
            "dependencies": [],
        }

    # ── Builder name from slug ────────────────────────────────────────────────
    slug_parts = slug.split("/", 1)
    builder = slug_parts[0] if len(slug_parts) > 1 else "unknown"
    agent_name = slug_parts[1] if len(slug_parts) > 1 else slug

    return CLIRunManifestResponse(
        slug=str(listing.slug),
        version=str(ver_obj.version_semver),
        listing_id=str(listing.id),
        builder=builder,
        name=agent_name,
        command=f"nuuvixx-agent-runner {listing.slug}@{ver_obj.version_semver}",
        agent_yaml=str(ver_obj.agent_yaml),
        runner="agentos",
        trust_score=float(getattr(listing, "trust_score", 0.0) or 0.0),
        scan_results=scan_results,
        lockfile=lockfile,
        price_per_call_usd=float(getattr(listing, "price_per_call_usd", 0.0) or 0.0),
        pricing_model=str(getattr(listing, "pricing_model", "per_call") or "per_call"),
    )
