"""
app/routers/telemetry.py

State Plane Telemetry & ANCESTOR Trace Streaming Router.
Provides real-time WebSocket telemetry streaming and HTTP endpoints for ANCESTOR trace logs.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import redis.asyncio as redis
import os
import json
import logging
import asyncio
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["Telemetry & ANCESTOR Traces"])

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# In-memory fallback trace store if Redis connection is offline
_in_memory_traces: Dict[str, List[Dict[str, Any]]] = {}
_in_memory_steps: Dict[str, List[Dict[str, Any]]] = {}


class TelemetryEventPayload(BaseModel):
    run_id: str = Field(..., alias="runId")
    agent_id: str = Field(..., alias="agentId")
    event_type: str = Field(..., alias="eventType")  # "STEP", "STATUS", "ANCESTOR"
    action: str
    verdict: Optional[str] = "APPROVED"  # "APPROVED", "BLOCKED", "ESCALATED"
    risk_score: Optional[str] = "LOW"    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    policy: Optional[str] = "SENTINEL_POLICY"
    duration_ms: Optional[int] = 0
    details: Optional[str] = None
    step_data: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True}


def compute_ancestor_hash(prev_hash: str, run_id: str, action: str, ts: str) -> str:
    payload = f"{prev_hash}:{run_id}:{action}:{ts}"
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.post("/events")
async def publish_telemetry_event(payload: TelemetryEventPayload):
    """
    Publishes step or ANCESTOR trace event to Redis pub/sub and stores in append-only log.
    """
    ts = datetime.utcnow().isoformat() + "Z"
    run_id = payload.run_id

    # Compute append-only cryptographic ANCESTOR hash link
    existing = _in_memory_traces.get(run_id, [])
    prev_hash = existing[-1]["state_hash"] if existing else "sha256:00000000000000000000000000000000"
    state_hash = compute_ancestor_hash(prev_hash, run_id, payload.action, ts)

    event_dict = {
        "id": f"tr-{len(existing)+1:03d}",
        "ts": ts,
        "run_id": run_id,
        "agent_id": payload.agent_id,
        "action": payload.action,
        "verdict": payload.verdict,
        "policy": payload.policy,
        "risk_score": payload.risk_score,
        "duration_ms": payload.duration_ms,
        "details": payload.details or f"Executed action {payload.action}",
        "state_hash": state_hash,
        "step_data": payload.step_data or {}
    }

    if run_id not in _in_memory_traces:
        _in_memory_traces[run_id] = []
    _in_memory_traces[run_id].append(event_dict)

    # Publish to Redis channel telemetry:{run_id}
    try:
        r = redis.Redis(connection_pool=redis_pool)
        channel = f"telemetry:{run_id}"
        await r.publish(channel, json.dumps(event_dict))
    except Exception as e:
        logger.warning(f"Redis publish failed, kept in memory fallback: {e}")

    return {"status": "published", "event_id": event_dict["id"], "state_hash": state_hash}


@router.get("/runs/{run_id}/ancestor")
async def get_ancestor_traces(run_id: str):
    """
    Fetches immutable ANCESTOR audit traces for a given run ID.
    """
    traces = _in_memory_traces.get(run_id, [])
    return {
        "runId": run_id,
        "count": len(traces),
        "traces": traces
    }


@router.get("/runs/{run_id}/steps")
async def get_telemetry_steps(run_id: str):
    """
    Fetches step telemetry for a given run ID.
    """
    traces = _in_memory_traces.get(run_id, [])
    steps = [t for t in traces if t.get("step_data")]
    return {
        "runId": run_id,
        "count": len(steps),
        "steps": steps
    }


@router.websocket("/ws/{run_id}")
async def telemetry_websocket(websocket: WebSocket, run_id: str):
    """
    Real-time WebSocket stream of telemetry & ANCESTOR traces for a run.
    """
    await websocket.accept()
    logger.info(f"Telemetry Webview connected for run: {run_id}")

    try:
        r = redis.Redis(connection_pool=redis_pool)
        pubsub = r.pubsub()
        channel = f"telemetry:{run_id}"
        await pubsub.subscribe(channel)

        async def redis_streamer():
            try:
                while True:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg is not None:
                        await websocket.send_text(msg["data"])
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Redis streamer error for run {run_id}: {e}")

        stream_task = asyncio.create_task(redis_streamer())

        try:
            while True:
                _ = await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info(f"Client disconnected from telemetry stream: {run_id}")
        finally:
            stream_task.cancel()
            await pubsub.unsubscribe(channel)
            await r.close()
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {e}")
