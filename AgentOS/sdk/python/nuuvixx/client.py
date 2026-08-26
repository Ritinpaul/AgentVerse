import httpx
import os
from typing import Dict, Any, List, Optional

class GovernedProxyClient:
    """
    Transparent Governance Proxy Client:
    Forces all outgoing LLM calls, MCP tool calls, and HTTP egress requests
    through AgentOS Network Plane Proxy -> AgentGovernOS Sentinel.
    """
    def __init__(self, agent_id: str = None, network_plane_url: str = None):
        self.agent_id = agent_id or os.getenv("AGENTOS_AGENT_ID", "system_agent")
        self.network_plane_url = network_plane_url or os.getenv("AGENTOS_NETWORK_PLANE_URL", "http://localhost:8013")
        self.http = httpx.Client(base_url=self.network_plane_url, timeout=30.0)

    def call_llm(self, model: str, prompt: str, provider: str = "openrouter") -> Dict[str, Any]:
        """Routes LLM request through transparent governance proxy."""
        payload = {
            "agent_id": self.agent_id,
            "provider": provider,
            "model": model,
            "prompt": prompt
        }
        resp = self.http.post("/proxy/llm", json=payload)
        resp.raise_for_status()
        return resp.json()

    def call_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Routes MCP tool call through transparent governance proxy."""
        payload = {
            "agent_id": self.agent_id,
            "server_name": server_name,
            "tool_name": tool_name,
            "arguments": arguments
        }
        resp = self.http.post("/proxy/call", json=payload)
        resp.raise_for_status()
        return resp.json()

    def check_egress_domain(self, domain: str, url: str) -> Dict[str, Any]:
        """Routes HTTP egress request through transparent governance proxy."""
        payload = {
            "agent_id": self.agent_id,
            "domain": domain,
            "url": url,
            "method": "GET"
        }
        resp = self.http.post("/proxy/egress", json=payload)
        resp.raise_for_status()
        return resp.json()


class AgentOSClient:
    """
    Client for interacting with the AgentOS State Plane and Control Plane.
    Usually instantiated automatically inside an @agent function context.
    """
    def __init__(self, agent_id: str = None, state_plane_url: str = None):
        self.agent_id = agent_id or os.getenv("AGENTOS_AGENT_ID")
        self.state_plane_url = state_plane_url or os.getenv("AGENTOS_STATE_PLANE_URL", "http://localhost:8012")
        self.http = httpx.Client(base_url=self.state_plane_url)
        self.proxy = GovernedProxyClient(agent_id=self.agent_id)
        
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        if not self.agent_id:
            raise ValueError("AGENTOS_AGENT_ID not set")
            
        payload = {"role": role, "content": content, "metadata": metadata or {}}
        resp = self.http.post(f"/conversation/{self.agent_id}/messages", json=payload)
        resp.raise_for_status()
        
    def get_messages(self) -> List[Dict[str, Any]]:
        if not self.agent_id:
            raise ValueError("AGENTOS_AGENT_ID not set")
            
        resp = self.http.get(f"/conversation/{self.agent_id}/messages")
        resp.raise_for_status()
        return resp.json()

    def save_snapshot(self, state: Dict[str, Any]):
        if not self.agent_id:
            raise ValueError("AGENTOS_AGENT_ID not set")
            
        resp = self.http.post(f"/snapshots/{self.agent_id}", json={"state": state})
        resp.raise_for_status()
        
    def get_snapshot(self) -> Dict[str, Any]:
        if not self.agent_id:
            raise ValueError("AGENTOS_AGENT_ID not set")
            
        resp = self.http.get(f"/snapshots/{self.agent_id}")
        resp.raise_for_status()
        return resp.json().get("state", {})
