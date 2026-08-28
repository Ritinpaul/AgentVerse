from typing import Any

from database import get_db
from fastapi import APIRouter, Depends
from models import Agent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/graph", tags=["Dependency Graph"])

@router.get("/")
async def get_agent_dependency_graph(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Returns a node-edge graph representation of all registered agents and their 
    A2A (Agent-to-Agent) delegation policies.
    """
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    
    nodes = []
    edges = []
    
    for agent in agents:
        nodes.append({
            "id": agent.id,
            "label": agent.name,
            "framework": agent.framework,
            "tier": agent.tier,
            "status": agent.status
        })
        
        # In a real implementation, we would query the Delegation tables or policies.
        # For Phase 4 scaffolding, we simulate edges if the agent has allowed_delegations
        # Assuming allowed_actions contains something like "delegate:AGENT-002"
        # Or if we have a specific A2A policy model.
        # This is a stubbed out relation for visualization purposes.
        for action in agent.allowed_actions:
            if action.startswith("delegate:"):
                target_id = action.split(":")[1]
                edges.append({
                    "source": agent.id,
                    "target": target_id,
                    "label": "delegates to"
                })

    return {
        "nodes": nodes,
        "edges": edges
    }
