
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.a2a_policy import A2APolicyService

router = APIRouter(tags=["a2a"])

class DelegationRequestPayload(BaseModel):
    caller_did: str
    target_did: str
    task_id: str
    depth: int = 0
    intent_signature: str | None = None

@router.post("/a2a/delegation-request")
async def delegation_request(payload: DelegationRequestPayload, db: AsyncSession = Depends(get_db)):
    """
    Evaluates an agent-to-agent delegation request.
    """
    result = await A2APolicyService.evaluate_delegation(
        db, 
        payload.caller_did, 
        payload.target_did, 
        payload.task_id, 
        payload.depth
    )
    if not result.get("approved"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.get("reason")
        )
    return result

@router.post("/a2a/attest-intent")
async def attest_intent(payload: DelegationRequestPayload, db: AsyncSession = Depends(get_db)):
    """
    Mocks an intent attestation endpoint for .
    """
    return {"status": "attested", "signature": "mock_signature_123"}
