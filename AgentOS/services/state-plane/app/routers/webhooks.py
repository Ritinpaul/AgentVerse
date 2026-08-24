from fastapi import APIRouter, HTTPException, Request
import redis
import json
import os

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)

@router.post("/{agent_id}")
async def receive_webhook(agent_id: str, request: Request):
    """
    Public webhook URL for an agent.
    When a payload is received here, we push it to the Redis Stream 'agentos:events'
    so the Execution Plane can wake up the agent.
    """
    try:
        # We accept any JSON payload
        payload = await request.json()
    except Exception:
        # Fallback for non-JSON payloads
        raw_body = await request.body()
        payload = {"raw_body": raw_body.decode('utf-8', errors='replace')}

    event_data = {
        "agent_id": agent_id,
        "event_type": "webhook",
        "payload": json.dumps(payload)
    }

    try:
        # Push to Redis stream. 
        # * means Redis will auto-generate an ID.
        r.xadd("agentos:events", event_data)
        return {"status": "accepted", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
