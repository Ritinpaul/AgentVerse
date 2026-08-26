"""
AgentOS Python SDK.

Exports:
  Core:
    agent, tool          — Decorators for defining agents and tools
    AgentOSClient        — Control/State Plane client
    MCPClient            — MCP tool caller (Bridge 5: GovernOS policy gate)

  A2A Commerce (Bridge 6):
    A2AClient            — Full A2A commerce client (class)
    hire_agent           — Convenience: discover + negotiate in one call
    settle_contract      — Convenience: settle a completed contract
"""

__version__ = "0.2.0"

from .agent import agent, tool
from .client import AgentOSClient
from .mcp import MCPClient
from .a2a import A2AClient, hire_agent, settle_contract

__all__ = [
    # Core
    "agent",
    "tool",
    "AgentOSClient",
    "MCPClient",
    # A2A Commerce (Bridge 6)
    "A2AClient",
    "hire_agent",
    "settle_contract",
]
