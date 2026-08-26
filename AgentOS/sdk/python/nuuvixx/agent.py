from typing import Callable, Any
from functools import wraps
from .client import AgentOSClient

def agent(name: str):
    """
    Decorator to mark a class or function as an AgentOS Agent.
    For Phase 2, this also wraps the function to inject any resumed state 
    from a previous snapshot.
    """
    def decorator(func: Callable) -> Callable:
        func.__agentos_name__ = name
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # When the container wakes up, this wrapper intercepts the call.
            # It pulls the latest snapshot to restore state.
            client = AgentOSClient()
            try:
                state = client.get_snapshot()
            except Exception:
                state = {}
                
            # If the function expects a 'state' kwarg, we inject it.
            import inspect
            sig = inspect.signature(func)
            if 'state' in sig.parameters:
                kwargs['state'] = state
                
            return func(*args, **kwargs)
            
        return wrapper
    return decorator

def tool(name: str = None):
    """
    Decorator to mark a method or function as an AgentOS Tool.
    """
    def decorator(func: Callable) -> Callable:
        func.__agentos_tool_name__ = name or func.__name__
        return func
    return decorator

import httpx
import os

def spawn(agent_name: str, instructions: str, swarm_id: str = None) -> str:
    """
    Spawns a sub-agent to handle a delegated task.
    This talks to the Control Plane to boot a new agent container.
    """
    control_plane_url = os.getenv("CONTROL_PLANE_URL", "http://localhost:8010")
    payload = {
        "name": agent_name,
        "instructions": instructions,
        "swarm_id": swarm_id
    }
    
    # In a real implementation, we would pass the parent agent's JWT token here
    try:
        resp = httpx.post(f"{control_plane_url}/lifecycle/boot", json=payload, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("agent_id")
    except Exception as e:
        print(f"Failed to spawn sub-agent: {e}")
        return None

import threading
from websockets.sync.client import connect as ws_connect

def send_message(target_agent_id: str, content: str, sender_id: str = "unknown", metadata: dict = None):
    """
    Sends a real-time message to another agent in the swarm.
    """
    state_plane_url = os.getenv("STATE_PLANE_URL", "http://localhost:8012")
    payload = {
        "target_agent_id": target_agent_id,
        "sender_id": sender_id,
        "content": content,
        "metadata": metadata or {}
    }
    
    try:
        resp = httpx.post(f"{state_plane_url}/messages/send", json=payload, timeout=10.0)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send message to {target_agent_id}: {e}")
        return False

def listen(agent_id: str, callback: Callable[[dict], None]):
    """
    Connects to the State Plane WebSocket and listens for incoming messages.
    Runs the listener in a background thread and triggers the callback.
    """
    state_plane_ws = os.getenv("STATE_PLANE_WS", "ws://localhost:8012")
    ws_url = f"{state_plane_ws}/messages/stream/{agent_id}"

    def _listener_loop():
        try:
            with ws_connect(ws_url) as websocket:
                print(f"[AgentOS] Connected to A2A stream for agent {agent_id}")
                for message in websocket:
                    import json
                    try:
                        data = json.loads(message)
                        callback(data)
                    except json.JSONDecodeError:
                        print(f"[AgentOS] Received malformed message: {message}")
        except Exception as e:
            print(f"[AgentOS] A2A stream disconnected: {e}")

    thread = threading.Thread(target=_listener_loop, daemon=True)
    thread.start()
    return thread
