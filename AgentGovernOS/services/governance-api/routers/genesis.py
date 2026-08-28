"""
GENESIS Router — Agent Identity & DNA Registry
===============================================
Endpoints for registering agents, managing Decision DNA profiles,
tracking lineage, diffing DNA, and bulk importing manifests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent, AgentGene
from pydantic import BaseModel, Field
from schemas import AgentCreate, AgentListResponse, AgentResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import ROLE_ADMIN, ROLE_AUDITOR, ROLE_OPERATOR, require_roles
from services.dna_engine import DNAEngine

router = APIRouter(prefix="/api/v1/agents", tags=["GENESIS Registry"])


class TraitMutationRequest(BaseModel):
    delta: float = Field(
        ...,
        ge=-0.50,
        le=0.50,
        description="Amount to mutate trait strength by (-0.50 to +0.50)",
        examples=[0.10],
    )
    reason: str = Field(
        ...,
        min_length=5,
        max_length=250,
        description="Human-readable reason for this mutation",
        examples=["Performance review Q1 — consistently above threshold"],
    )


# ──── Existing endpoints ────

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent_in: AgentCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    """Register a new agent in the GENESIS registry."""
    existing = await db.execute(select(Agent).where(Agent.agent_code == agent_in.agent_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent {agent_in.agent_code} already exists")

    agent = Agent(
        agent_code=agent_in.agent_code,
        display_name=agent_in.display_name,
        role=agent_in.role,
        crewai_role=agent_in.crewai_role,
        crewai_backstory=agent_in.crewai_backstory,
        tier=agent_in.tier.value,
        authority_limit=Decimal(str(agent_in.authority_limit)),
        dna_profile=agent_in.dna_profile,
        platform_bindings=agent_in.platform_bindings,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    status_filter: str | None = None,
    tier: str | None = None,
    role: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR)),
):
    """List all agents with optional filters."""
    query = select(Agent)
    if status_filter:
        query = query.where(Agent.status == status_filter)
    if tier:
        query = query.where(Agent.tier == tier)
    if role:
        query = query.where(Agent.role == role)

    subq = query.subquery()
    total_q = select(func.count()).select_from(subq)
    total = (await db.execute(total_q)).scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit).order_by(Agent.trust_score.desc()))
    agents = result.scalars().all()

    return AgentListResponse(agents=agents, total=total)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR)),
):
    """Get a single agent by ID."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    """Update agent fields (partial update)."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    allowed_fields = {"display_name", "status", "tier", "dna_profile", "platform_bindings", "metadata"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(agent, key if key != "metadata" else "metadata_", value)

    await db.flush()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def retire_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    """Retire an agent (soft delete — sets status to 'retired')."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "retired"
    await db.flush()


@router.get("/{agent_id}/dna")
async def get_agent_dna(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR)),
):
    """Get agent's Decision DNA profile with all genes."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await db.execute(select(AgentGene).where(AgentGene.agent_id == agent_id))
    genes = result.scalars().all()

    return {
        "agent_code": agent.agent_code,
        "dna_profile": agent.dna_profile,
        "genes": [
            {
                "gene_name": g.gene_name,
                "gene_type": g.gene_type,
                "acquired_from": g.acquired_from,
                "strength": float(g.strength) if g.strength is not None else 0.5,
                "version": g.version,
                "mutation_log": g.mutation_log,
            }
            for g in genes
        ],
    }


@router.post("/{agent_id}/dna/mutate/{trait}")
async def mutate_agent_trait(
    agent_id: UUID,
    trait: str,
    body: TraitMutationRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    """Mutate a trait strength for an agent and update DNA profile."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    engine = DNAEngine()
    current_dna = agent.dna_profile or {}

    try:
        updated_dna, old_value, new_value = engine.apply_mutation(
            dna=current_dna, trait=trait, delta=body.delta
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    agent.dna_profile = updated_dna
    delta = body.delta
    reason = body.reason

    gene_result = await db.execute(
        select(AgentGene).where(
            AgentGene.agent_id == agent_id,
            AgentGene.gene_name == trait,
        )
    )
    gene = gene_result.scalar_one_or_none()

    mutation_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "delta": delta,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
    }

    if gene:
        gene.strength = Decimal(str(round(min(1.0, max(0.0, float(gene.strength or 0.5) + delta)), 4)))
        gene.version += 1
        log = list(gene.mutation_log) if gene.mutation_log else []
        log.append(mutation_entry)
        gene.mutation_log = log[-20:]
    else:
        gene = AgentGene(
            agent_id=agent_id,
            gene_name=trait,
            gene_type="learned",
            acquired_from="governance_mutation",
            strength=Decimal(str(round(max(0.0, min(1.0, 0.5 + delta)), 4))),
            version=1,
            mutation_log=[mutation_entry],
        )
        db.add(gene)

    await db.flush()
    await db.refresh(agent)

    return {
        "agent_code": agent.agent_code,
        "trait_mutated": trait,
        "old_value": old_value,
        "new_value": new_value,
        "delta_applied": delta,
        "reason": reason,
        "dna_profile": agent.dna_profile,
        "mutated_at": datetime.now(UTC).isoformat(),
    }


# ──── NEW: DNA Diff Endpoint ────

@router.get("/{agent_id}/dna/diff/{other_agent_id}")
async def diff_agent_dna(
    agent_id: UUID,
    other_agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR)),
):
    """Compare DNA profiles of two agents trait by trait."""
    agent_a = await db.get(Agent, agent_id)
    if not agent_a:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent_b = await db.get(Agent, other_agent_id)
    if not agent_b:
        raise HTTPException(status_code=404, detail=f"Agent {other_agent_id} not found")

    engine = DNAEngine()
    dna_a = agent_a.dna_profile or {}
    dna_b = agent_b.dna_profile or {}

    diff = engine.diff_dna(
        dna_a,
        dna_b,
        label_a=agent_a.agent_code,
        label_b=agent_b.agent_code,
    )
    fitness_a = engine.fitness_score(dna_a)
    fitness_b = engine.fitness_score(dna_b)

    return {
        "agent_a": {
            "id": str(agent_a.id),
            "agent_code": agent_a.agent_code,
            "display_name": agent_a.display_name,
            "tier": agent_a.tier,
            "dna_hash": engine.compute_dna_hash(dna_a),
            "fitness": fitness_a,
        },
        "agent_b": {
            "id": str(agent_b.id),
            "agent_code": agent_b.agent_code,
            "display_name": agent_b.display_name,
            "tier": agent_b.tier,
            "dna_hash": engine.compute_dna_hash(dna_b),
            "fitness": fitness_b,
        },
        "diff": diff,
        "are_related": (
            str(agent_a.parent_agent_id) == str(agent_b.id)
            or str(agent_b.parent_agent_id) == str(agent_a.id)
        ),
        "compared_at": datetime.now(UTC).isoformat(),
    }


# ──── NEW: Lineage Tree Endpoint ────

@router.get("/{agent_id}/lineage")
async def get_agent_lineage(
    agent_id: UUID,
    max_depth: int = 10,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_AUDITOR)),
):
    """Get the full lineage tree for an agent."""
    root = await db.get(Agent, agent_id)
    if not root:
        raise HTTPException(status_code=404, detail="Agent not found")

    ancestors: list[dict] = []
    current_id: UUID | None = root.parent_agent_id
    depth = 0
    visited: set[UUID] = {agent_id}

    while current_id and depth < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)
        parent = await db.get(Agent, current_id)
        if not parent:
            break
        ancestors.append({
            "id": str(parent.id),
            "agent_code": parent.agent_code,
            "display_name": parent.display_name,
            "tier": parent.tier,
            "trust_score": float(parent.trust_score),
            "generation": parent.generation,
            "status": parent.status,
            "depth": -(depth + 1),
        })
        current_id = parent.parent_agent_id
        depth += 1

    descendants: list[dict] = []
    queue: list[tuple[UUID, int]] = [(agent_id, 0)]
    visited_desc: set[UUID] = {agent_id}

    while queue:
        parent_id, level = queue.pop(0)
        if level >= max_depth:
            continue
        children_result = await db.execute(
            select(Agent).where(Agent.parent_agent_id == parent_id)
        )
        children = children_result.scalars().all()
        for child in children:
            if child.id in visited_desc:
                continue
            visited_desc.add(child.id)
            descendants.append({
                "id": str(child.id),
                "agent_code": child.agent_code,
                "display_name": child.display_name,
                "tier": child.tier,
                "trust_score": float(child.trust_score),
                "generation": child.generation,
                "status": child.status,
                "parent_id": str(parent_id),
                "depth": level + 1,
            })
            queue.append((child.id, level + 1))

    return {
        "root": {
            "id": str(root.id),
            "agent_code": root.agent_code,
            "display_name": root.display_name,
            "tier": root.tier,
            "trust_score": float(root.trust_score),
            "generation": root.generation,
            "status": root.status,
            "depth": 0,
        },
        "ancestors": ancestors,
        "descendants": descendants,
        "total_nodes": 1 + len(ancestors) + len(descendants),
        "max_ancestor_depth": len(ancestors),
        "max_descendant_depth": max(d["depth"] for d in descendants) if descendants else 0,
    }


# ──── NEW: POST /agents/import ────

class BulkAgentImportRequest(BaseModel):
    agents: list[dict] = Field(..., description="List of agent definition objects")
    skip_duplicates: bool = Field(
        default=True,
        description="If True, silently skip agents whose agent_code already exists. If False, return 409."
    )


@router.post("/import", status_code=status.HTTP_207_MULTI_STATUS)
async def bulk_import_agents(
    body: BulkAgentImportRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    """Bulk-import agents from a JSON / YAML manifest."""
    results = []
    for entry in body.agents:
        agent_code = entry.get("agent_code")
        if not agent_code:
            results.append({
                "agent_code": None,
                "status": "error",
                "message": "Missing agent_code in entry",
            })
            continue

        existing = await db.execute(
            select(Agent).where(Agent.agent_code == agent_code)
        )
        if existing.scalar_one_or_none() is not None:
            if body.skip_duplicates:
                results.append({
                    "agent_code": agent_code,
                    "status": "skipped",
                    "message": f"Agent '{agent_code}' already exists",
                })
            else:
                results.append({
                    "agent_code": agent_code,
                    "status": "error",
                    "message": f"Agent '{agent_code}' already exists (skip_duplicates=false)",
                })
            continue

        try:
            agent = Agent(
                agent_code=agent_code,
                display_name=entry.get("display_name", agent_code),
                role=entry.get("role", "analyst"),
                crewai_role=entry.get("crewai_role", "Agent"),
                crewai_backstory=entry.get("crewai_backstory", "Imported via bulk manifest"),
                tier=entry.get("tier", "T4"),
                authority_limit=Decimal(str(entry.get("authority_limit", 0))),
                dna_profile=entry.get("dna_profile", {}),
                platform_bindings=entry.get("platform_bindings", []),
                trust_score=Decimal(str(entry.get("trust_score", "0.60"))),
                status=entry.get("status", "active"),
            )
            db.add(agent)
            await db.flush()
            await db.refresh(agent)
            results.append({
                "agent_code": agent_code,
                "status": "created",
                "id": str(agent.id),
                "tier": agent.tier,
                "trust_score": float(agent.trust_score),
            })
        except Exception as exc:
            await db.rollback()
            results.append({
                "agent_code": agent_code,
                "status": "error",
                "message": str(exc),
            })

    created = sum(1 for r in results if r["status"] == "created")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")

    return {
        "summary": {
            "total": len(results),
            "created": created,
            "skipped": skipped,
            "errors": errors,
        },
        "results": results,
    }
