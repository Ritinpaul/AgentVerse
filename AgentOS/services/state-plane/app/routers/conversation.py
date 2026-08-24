from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import redis
import json
import os

router = APIRouter(prefix="/conversation", tags=["conversation"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)

class Message(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = {}

@router.post("/{agent_id}/messages")
def add_message(agent_id: str, message: Message):
    try:
        r.rpush(f"agent:{agent_id}:conversation", message.model_dump_json())
        return {"status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/messages", response_model=List[Message])
def get_messages(agent_id: str):
    try:
        raw_msgs = r.lrange(f"agent:{agent_id}:conversation", 0, -1)
        return [Message(**json.loads(msg)) for msg in raw_msgs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
