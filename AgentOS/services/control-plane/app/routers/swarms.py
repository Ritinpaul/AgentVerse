
from fastapi import APIRouter, HTTPException

from app.models.swarm import Swarm, SwarmCreate

router = APIRouter(prefix="/swarms", tags=["swarms"])

# In-memory storage for Phase 4 (Mocking DB for simplicity)
SWARMS_DB: dict[str, Swarm] = {}

@router.post("/", response_model=Swarm)
def create_swarm(swarm_in: SwarmCreate):
    swarm = Swarm(**swarm_in.model_dump())
    SWARMS_DB[swarm.id] = swarm
    return swarm

@router.get("/", response_model=list[Swarm])
def list_swarms():
    return list(SWARMS_DB.values())

@router.get("/{swarm_id}", response_model=Swarm)
def get_swarm(swarm_id: str):
    swarm = SWARMS_DB.get(swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail="Swarm not found")
    return swarm

@router.post("/{swarm_id}/workers")
def add_worker(swarm_id: str, worker_id: str):
    swarm = SWARMS_DB.get(swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail="Swarm not found")
    if worker_id not in swarm.worker_agent_ids:
        swarm.worker_agent_ids.append(worker_id)
    return swarm
