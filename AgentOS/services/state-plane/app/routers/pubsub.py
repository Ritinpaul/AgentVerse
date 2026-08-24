from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import redis.asyncio as redis
import os
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["A2A Messaging"])

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

class MessagePayload(BaseModel):
    target_agent_id: str
    sender_id: str
    content: str
    metadata: dict = {}

@router.post("/send")
async def send_message(payload: MessagePayload):
    """
    Publish a message to the target agent's Redis channel.
    """
    r = redis.Redis(connection_pool=redis_pool)
    channel = f"agent:{payload.target_agent_id}"
    message_json = json.dumps({
        "sender_id": payload.sender_id,
        "content": payload.content,
        "metadata": payload.metadata
    })
    await r.publish(channel, message_json)
    return {"status": "sent", "channel": channel}


@router.websocket("/stream/{agent_id}")
async def stream_messages(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint for an agent to listen for its own messages.
    """
    await websocket.accept()
    logger.info(f"Agent {agent_id} connected to message stream.")

    r = redis.Redis(connection_pool=redis_pool)
    pubsub = r.pubsub()
    channel = f"agent:{agent_id}"
    
    await pubsub.subscribe(channel)
    
    async def redis_listener():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    data = message["data"]
                    await websocket.send_text(data)
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    listener_task = asyncio.create_task(redis_listener())

    try:
        # Keep connection open and detect client disconnect
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected from message stream.")
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {e}")
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(channel)
        await r.close()
