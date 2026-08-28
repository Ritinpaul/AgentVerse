from decimal import Decimal

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models import Agent
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/cost", tags=["Cost Governance"])

class UpdateBudgetPayload(BaseModel):
    agent_id: str
    daily_budget_usd: Decimal

@router.get("/{agent_id}")
async def get_cost_metrics(agent_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns the current spend and budget for an agent.
    """
    agent = await db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        
    return {
        "agent_id": str(agent.id),
        "daily_budget_usd": agent.daily_budget_usd,
        "current_spend_usd": agent.current_spend_usd,
        "remaining_budget_usd": agent.daily_budget_usd - agent.current_spend_usd if agent.daily_budget_usd > 0 else "unlimited"
    }

@router.post("/budget")
async def update_budget(payload: UpdateBudgetPayload, db: AsyncSession = Depends(get_db)):
    """
    Updates the daily budget for an agent.
    """
    agent = await db.scalar(select(Agent).where(Agent.id == payload.agent_id))
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        
    agent.daily_budget_usd = payload.daily_budget_usd
    await db.commit
    return {"status": "success", "new_budget": agent.daily_budget_usd}
