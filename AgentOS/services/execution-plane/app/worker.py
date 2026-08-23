import redis.asyncio as redis
import os
import logging
from app.sandbox.runner import sandbox

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def listen_for_events():
    """
    Background worker that listens to the 'agentos:events' Redis stream.
    When a wakeup/webhook event is received, it triggers the execution plane runner.
    """
    try:
        r = redis.from_url(REDIS_URL)
        # Create consumer group if it doesn't exist
        try:
            await r.xgroup_create("agentos:events", "execution_workers", id="0", mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        logger.info("Started listening for AgentOS events...")
        while True:
            # Block and read from the stream
            # ">" means we want messages that were never delivered to any other consumer
            messages = await r.xreadgroup(
                "execution_workers", 
                "worker_1", 
                {"agentos:events": ">"}, 
                count=10, 
                block=5000
            )

            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    try:
                        await process_event(msg_id, msg_data)
                        # Acknowledge the message
                        await r.xack(stream, "execution_workers", msg_id)
                    except Exception as e:
                        logger.error(f"Error processing event {msg_id}: {e}")

    except Exception as e:
        logger.error(f"Redis listener failed: {e}")
        # In production, we'd want backoff and reconnect logic here.
        
async def process_event(msg_id, msg_data):
    agent_id = msg_data.get(b"agent_id", b"").decode("utf-8")
    event_type = msg_data.get(b"event_type", b"").decode("utf-8")
    payload = msg_data.get(b"payload", b"{}").decode("utf-8")

    logger.info(f"Received {event_type} for {agent_id}")

    # Wake up the agent by starting its sandbox, passing the event as env vars
    # In a full system, we'd lookup the agent's entrypoint from the Control Plane DB.
    # For Phase 2, we assume a standard Python agent entrypoint `python main.py` or similar.
    env_vars = {
        "AGENTOS_WAKEUP_EVENT": event_type,
        "AGENTOS_WAKEUP_PAYLOAD": payload
    }
    
    # We pass a generic entrypoint because the agent SDK handles routing the wakeup
    sandbox.start_execution(agent_id, entrypoint="python main.py", env_vars=env_vars)
