from decimal import Decimal
from typing import Any

from models import Agent, TokenLedger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CostGovernanceService:
    @staticmethod
    async def evaluate_budget(db: AsyncSession, agent_id: str, estimated_cost: Decimal = Decimal("0.00")) -> dict[str, Any]:
        """
        Validates if an agent has enough budget to execute the request.
        """
        agent = await db.scalar(select(Agent).where(Agent.id == agent_id))
        if not agent:
            return {"approved": False, "reason": "Agent not found"}
            
        if agent.daily_budget_usd <= Decimal("0.00"):
            # No budget limits enforced
            return {"approved": True}
            
        projected_spend = agent.current_spend_usd + estimated_cost
        if projected_spend > agent.daily_budget_usd:
            return {
                "approved": False, 
                "reason": f"Budget Exceeded. Daily budget is {agent.daily_budget_usd} USD, projected spend is {projected_spend} USD."
            }
            
        return {"approved": True}

    @staticmethod
    async def log_usage(
        db: AsyncSession, 
        agent_id: str, 
        task_id: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int, 
        cost_usd: Decimal
    ) -> None:
        """
        Records the API usage into the TokenLedger and updates the agent's current spend.
        """
        ledger_entry = TokenLedger(
            agent_id=agent_id,
            task_id=task_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd
        )
        db.add(ledger_entry)
        
        # Update current spend on the agent
        agent = await db.scalar(select(Agent).where(Agent.id == agent_id))
        if agent:
            agent.current_spend_usd += cost_usd
            db.add(agent)
            
        await db.commit()
