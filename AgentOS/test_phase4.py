import httpx
import os

# 1. We will simulate a Control Plane API call to create a Swarm
print("--- 1. Creating a Swarm ---")
swarm_payload = {
    "tenant_id": "test-tenant-123",
    "name": "Research Swarm",
    "manager_agent_id": "manager-1",
    "worker_agent_ids": ["worker-1", "worker-2"]
}
resp = httpx.post("http://localhost:8010/swarms/", json=swarm_payload)
print(f"Swarm Created: {resp.json()}\n")

# 2. We will simulate an Agent making a tool call with a mock JWT
# (In a fully integrated system, the Agent gets this JWT from the Control Plane on boot)
print("--- 2. Making a Tool Call to Network Plane ---")

# Let's try to use the 'websearch' tool, which we will pretend is banned by AgentGovernOS
tool_payload = {
    "agent_id": "manager-1",
    "server_name": "websearch",
    "tool_name": "search",
    "arguments": {"query": "How to hack"}
}

# The Network Plane expects the JWT in the Authorization header
headers = {
    "Authorization": "Bearer mock-jwt-token-for-tenant-123"
}

try:
    resp = httpx.post("http://localhost:8013/proxy/call", json=tool_payload, headers=headers)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
