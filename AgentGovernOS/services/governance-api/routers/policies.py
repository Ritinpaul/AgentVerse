"""
Policies Router (Versioning Extension)

Provides endpoints to interact with policy histories,
view diffs, and perform rollbacks.
"""

import uuid
from typing import Any

from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import PolicyVersion
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.policy_versioner import PolicyVersioner

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])
versioner = PolicyVersioner()

class RollbackRequest(BaseModel):
    target_version: int
    reason: str | None = None

class PolicyVersionResponse(BaseModel):
    id: str
    policy_id: str
    version: int
    content_json: dict[str, Any]
    diff: dict[str, Any] | None
    created_at: str

@router.get("/{policy_id}/history", response_model=list[PolicyVersionResponse])
async def get_policy_history(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve the version history of a policy."""
    history = await versioner.get_history(db, policy_id)
    if not history:
        raise HTTPException(status_code=404, detail="Policy history not found")
        
    return [
        PolicyVersionResponse(
            id=str(h.id),
            policy_id=str(h.policy_id),
            version=h.version,
            content_json=h.content_json,
            diff=h.diff,
            created_at=h.created_at.isoformat()
        )
        for h in history
    ]

@router.post("/{policy_id}/rollback")
async def rollback_policy(policy_id: uuid.UUID, req: RollbackRequest, db: AsyncSession = Depends(get_db)):
    """Roll back a policy to a specific previous version."""
    try:
        policy = await versioner.rollback(db, policy_id, req.target_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return {"status": "success", "new_version": policy.version, "message": f"Rolled back to version {req.target_version}"}

@router.get("/{policy_id}/versions/{version}/diff")
async def get_policy_diff(policy_id: uuid.UUID, version: int, db: AsyncSession = Depends(get_db)):
    """Retrieve the diff between a specific version and its predecessor."""
    from sqlalchemy import select
    
    result = await db.execute(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id, PolicyVersion.version == version)
    )
    pv = result.scalar_one_or_none
    
    if not pv:
        raise HTTPException(status_code=404, detail="Version not found")
        
    return {"version": version, "diff": pv.diff}
