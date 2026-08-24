from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import redis
import json
import os

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)

class Snapshot(BaseModel):
    state: Dict[str, Any]

@router.post("/{agent_id}")
def save_snapshot(agent_id: str, snapshot: Snapshot):
    try:
        r.set(f"agent:{agent_id}:snapshot", snapshot.model_dump_json())
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=Snapshot)
def get_snapshot(agent_id: str):
    try:
        raw_state = r.get(f"agent:{agent_id}:snapshot")
        if not raw_state:
            # Return empty state if none exists yet
            return Snapshot(state={})
        return Snapshot(**json.loads(raw_state))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
