"""
Compositions Router — /api/v1/compositions
Multi-agent pipeline publishing, search, dependency resolution, and policy validation.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.rate_limit import mutation_limit
from app.models.composition_models import AgentComposition
from app.services.dependency_resolver import resolve_agent_dependencies, generate_lockfile
from app.services.composition_validator import validate_composition_policies

router = APIRouter(prefix="/api/v1/compositions", tags=["compositions"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class StepSchema(BaseModel):
    step_id: str
    agent_slug: str
    version_constraint: Optional[str] = ">=0.1.0"
    depends_on: Optional[List[str]] = []


class CompositionCreateRequest(BaseModel):
    name: str
    builder_id: str
    description: str
    category: Optional[str] = "pipeline"
    version: Optional[str] = "1.0.0"
    steps: List[StepSchema]


class ResolveRequest(BaseModel):
    agent_slugs: List[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
@mutation_limit("10/minute")
def create_composition(request: Request, req: CompositionCreateRequest, db: Session = Depends(get_db)):
    """Publish a new multi-agent composition / pipeline."""
    clean_name = req.name.lower().replace(" ", "-")
    slug = f"{req.builder_id}/{clean_name}"

    existing = db.query(AgentComposition).filter(AgentComposition.slug == slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Composition '{slug}' already exists.")

    agent_slugs = [s.agent_slug for s in req.steps]

    # Resolve dependencies
    resolved_data = resolve_agent_dependencies(agent_slugs, db)

    # Validate policies
    policy_res = validate_composition_policies(agent_slugs, db)

    # Generate lockfile
    lockfile = generate_lockfile(slug, resolved_data)

    composition = AgentComposition(
        slug=slug,
        name=req.name,
        description=req.description,
        builder_id=req.builder_id,
        category=req.category or "pipeline",
        version=req.version or "1.0.0",
        steps=[s.dict() for s in req.steps],
        version_lockfile=lockfile,
        policy_status="valid" if policy_res["valid"] else "policy_clash",
        policy_clashes=policy_res["clashes"],
        status="active",
    )
    db.add(composition)
    db.commit()
    db.refresh(composition)

    return {
        "id": composition.id,
        "slug": composition.slug,
        "name": composition.name,
        "policy_status": composition.policy_status,
        "policy_clashes": composition.policy_clashes,
        "resolved_agents_count": len(resolved_data["resolved_agents"]),
        "lockfile": lockfile,
    }


@router.get("/")
def list_compositions(builder: Optional[str] = None, db: Session = Depends(get_db)):
    """List published multi-agent compositions."""
    query = db.query(AgentComposition).filter(AgentComposition.status == "active")
    if builder:
        query = query.filter(AgentComposition.builder_id == builder)
    comps = query.order_by(AgentComposition.id.desc()).all()
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "builder_id": c.builder_id,
            "category": c.category,
            "version": c.version,
            "step_count": len(c.steps) if isinstance(c.steps, list) else 0,
            "policy_status": c.policy_status,
            "created_at": c.created_at,
        }
        for c in comps
    ]


@router.get("/{builder}/{composition_name}")
def get_composition(builder: str, composition_name: str, db: Session = Depends(get_db)):
    """Fetch composition details, topology, and generated lockfile."""
    slug = f"{builder}/{composition_name}"
    comp = db.query(AgentComposition).filter(AgentComposition.slug == slug).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Composition '{slug}' not found.")

    return {
        "id": comp.id,
        "slug": comp.slug,
        "name": comp.name,
        "description": comp.description,
        "builder_id": comp.builder_id,
        "category": comp.category,
        "version": comp.version,
        "steps": comp.steps,
        "policy_status": comp.policy_status,
        "policy_clashes": comp.policy_clashes,
        "lockfile": comp.version_lockfile,
        "created_at": comp.created_at,
    }


@router.post("/resolve-deps")
@mutation_limit("30/minute")
def resolve_dependencies_endpoint(request: Request, req: ResolveRequest, db: Session = Depends(get_db)):
    """Resolve direct and transitive dependencies for a list of agent slugs."""
    resolved_data = resolve_agent_dependencies(req.agent_slugs, db)
    lockfile = generate_lockfile("adhoc-resolution", resolved_data)
    return {
        "resolved": resolved_data,
        "lockfile": lockfile,
    }


@router.post("/validate-policies")
@mutation_limit("30/minute")
def validate_policies_endpoint(request: Request, req: ResolveRequest, db: Session = Depends(get_db)):
    """Cross-agent security policy validation for a list of agent slugs."""
    return validate_composition_policies(req.agent_slugs, db)
