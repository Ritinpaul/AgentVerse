import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def load_registry() -> List[Dict[str, Any]]:
    """
    Simulates fetching verified MCP servers from AgentStore.
    For Phase 3, we load this from a local hardcoded JSON file.
    """
    registry_path = os.path.join(os.path.dirname(__file__), "../../mock_registry.json")
    try:
        with open(registry_path, "r") as f:
            data = json.load(f)
            return data.get("servers", [])
    except Exception as e:
        logger.error(f"Failed to load mock registry: {e}")
        return []

def get_mcp_url(server_name: str) -> str:
    """Find the URL for a given MCP server name in the registry."""
    servers = load_registry()
    for server in servers:
        if server["name"] == server_name:
            return server["url"]
    return None
