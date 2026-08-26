import sys
import logging
from typing import Dict, Any
from .client import AgentOSClient

logger = logging.getLogger(__name__)

def pause_until(event_type: str, state: Dict[str, Any]):
    """
    Serializes the agent's current memory/variables to the State Plane Snapshot API,
    and then cleanly exits the Python process.
    The agent will remain SUSPENDED and consume 0 compute resources until the 
    Control Plane or Execution Plane wakes it up by injecting a webhook payload.
    
    Args:
        event_type: The type of event we are waiting for (e.g., 'human_input', 'webhook_callback').
        state: A JSON-serializable dictionary of the variables the agent needs to resume.
    """
    client = AgentOSClient()
    
    logger.info(f"Suspending agent. Saving snapshot and waiting for {event_type}...")
    
    # 1. Save state to the State Plane
    client.save_snapshot(state)
    
    # 2. Tell the Control Plane we are suspended (this could also be handled by the execution plane noticing the exit)
    # For Phase 2, we just exit cleanly.
    
    # Exit process. The Execution Plane will detect the container stopped.
    sys.exit(0)
