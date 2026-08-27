import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from models import Agent, DelegationAttestation, DelegationRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class A2APolicyService:
    @staticmethod
    async def evaluate_delegation(
        db: AsyncSession, 
        caller_did: str, 
        target_did: str, 
        task_id: str, 
        depth: int
    ) -> dict[str, Any]:
        """
        Validates delegation depth, mutual trust scores, and creates an attestation.
        """
        # Fetch caller and target agents
        caller = await db.scalar(select(Agent).where(Agent.did == caller_did))
        target = await db.scalar(select(Agent).where(Agent.did == target_did))

        if not caller or not target:
            return {"approved": False, "reason": "Caller or target agent not found"}

        # Rule 1: Max depth
        if depth > 5:
            return {"approved": False, "reason": "Max delegation depth exceeded"}

        # Rule 2: Minimum trust score
        if caller.trust_score < Decimal("0.3") or target.trust_score < Decimal("0.3"):
            return {"approved": False, "reason": "Trust score too low for delegation"}

        # Create request
        req = DelegationRequest(
            caller_did=caller_did,
            target_did=target_did,
            task_id=task_id,
            depth=depth,
            status="approved"
        )
        db.add(req)
        await db.flush

        # Compute hash
        payload_str = json.dumps({
            "request_id": str(req.id),
            "caller": caller_did,
            "target": target_did,
            "timestamp": datetime.now(UTC).isoformat
        }, sort_keys=True)
        attestation_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest

        # Create attestation
        att = DelegationAttestation(
            request_id=req.id,
            caller_trust_score=caller.trust_score,
            target_trust_score=target.trust_score,
            policy_violations=[],
            attestation_hash=attestation_hash
        )
        db.add(att)
        await db.commit

        return {
            "approved": True,
            "attestation_hash": attestation_hash,
            "request_id": str(req.id)
        }
