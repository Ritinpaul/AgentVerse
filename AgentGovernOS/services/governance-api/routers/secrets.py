"""
Secrets Router

Handles auditing and delivery of secrets for agents.
Ensures that an agent is authorized by policy to access a specific secret path.
"""

from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import Agent, SecretRequest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.vault_client import VaultClient

router = APIRouter(prefix="/secrets", tags=["Secrets"])
vault_client = VaultClient()

class SecretAccessRequest(BaseModel):
    agent_did: str
    secret_path: str
    reason: str | None = None

class SecretRegistrationRequest(BaseModel):
    secret_path: str
    payload: dict

@router.post("/request")
async def request_secret(req: SecretAccessRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent requests access to a secret. 
    Logs the request and returns the secret if authorized.
    """
    # 1. Verify agent DID exists
    result = await db.execute(select(Agent).where(Agent.did == req.agent_did))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=403, detail="Agent DID not recognized")
        
    # 2. Check policy authorization by trust tier (T1/T2 highest, T3 policy, T4 restricted)
    if "admin" in req.secret_path and agent.tier not in ["T1", "T2"]:
        denied_req = SecretRequest(
            agent_did=req.agent_did,
            secret_path=req.secret_path,
            status="denied",
            reason="Admin path restricted to T1/T2 agents"
        )
        db.add(denied_req)
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied by policy")
    elif agent.tier == "T4":
        denied_req = SecretRequest(
            agent_did=req.agent_did,
            secret_path=req.secret_path,
            status="denied",
            reason="T4 agents restricted from secret access"
        )
        db.add(denied_req)
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied by policy")

    # 3. Retrieve secret
    secret_data = vault_client.read_secret(req.secret_path)
    
    if not secret_data:
        raise HTTPException(status_code=404, detail="Secret path not found")
        
    # 4. Log successful access
    granted_req = SecretRequest(
        agent_did=req.agent_did,
        secret_path=req.secret_path,
        status="granted",
        reason=req.reason
    )
    db.add(granted_req)
    await db.commit()
    
    return {"status": "success", "data": secret_data}


@router.post("/register")
async def register_secret(req: SecretRegistrationRequest):
    """
    Registers a new secret payload into the vault. (Admin only)
    """
    success = vault_client.write_secret(req.secret_path, req.payload)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write secret to vault")
    
    return {"status": "success", "path": req.secret_path}
