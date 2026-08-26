# AgentOS

> **Pillar 2 of AgentVerse — The Stateful Serverless Runtime for Autonomous AI Agents**

AgentOS is the execution backbone of AgentVerse. It provides a stateful, sandboxed, and policy-governed runtime for autonomous AI agents — handling everything from cold-start scheduling to cross-agent communication, model routing, MCP server integration, and real-time cost metering.

---

## Overview

```
AgentOS
├── services/
│   ├── control-plane/    # Agent lifecycle API (:8010)
│   ├── execution-plane/  # Sandboxed execution workers
│   ├── network-plane/    # MCP proxy + tool discovery
│   └── state-plane/      # Memory, snapshots, webhooks
├── sdk/python/nuuvixx/   # Python SDK for agent developers
├── cli/                  # `av` CLI entry point
├── infra/                # Docker + deployment configs
├── test_a2a.py           # A2A integration tests
├── test_mcp.py           # MCP integration tests
└── test_phase4.py        # State plane integration tests
```

---

## Architecture: 4-Plane Design

AgentOS separates concerns into four independent service planes:

```
┌────────────────────────────────────────────────────────────────┐
│                         AgentOS Runtime                        │
│                                                                │
│  Control Plane (:8010)      Execution Plane                    │
│  ┌─────────────────┐        ┌──────────────────────────────┐   │
│  │ Agent Lifecycle │        │  Sandboxed Worker Processes  │   │
│  │ - Create        │───────▶│  - MicroVM isolation          │   │
│  │ - Start / Stop  │        │  - Token budget enforcement   │   │
│  │ - Health check  │        │  - Hot-reload on file change  │   │
│  │ - Rollback      │        │  - Execution trace + metrics  │   │
│  └─────────────────┘        └──────────────────────────────┘   │
│                                            │                   │
│  Network Plane                  State Plane│                   │
│  ┌─────────────────┐        ┌──────────────▼───────────────┐   │
│  │ MCP Proxy       │        │  Memory + Snapshots          │   │
│  │ - Tool discovery│◀───────│  - Conversation memory       │   │
│  │ - Call routing  │        │  - Sub-100ms snapshots       │   │
│  │ - GovernOS gate │        │  - State rehydration         │   │
│  │ - Rate limiting │        │  - Webhook delivery          │   │
│  └─────────────────┘        └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

---

## Service Planes

### Control Plane (`:8010`)
The primary API surface for managing agent lifecycles.

**Key responsibilities:**
- Create, start, stop, pause, and delete agent instances
- Agent health monitoring and status reporting
- Rollback to previous checkpoint on failure
- Scale-to-zero scheduling (agent pauses when idle, resumes on demand)
- Integration with AgentGovernOS for pre-execution compliance checks

```bash
cd services/control-plane
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

**Docs:** `http://127.0.0.1:8010/docs`

---

### Execution Plane
Sandboxed worker processes that actually run agent code.

**Key responsibilities:**
- MicroVM-based process isolation per agent instance
- Hard token budget enforcement — agents that exceed limits are terminated
- Hot-reload on `agent.yaml` changes without full restart
- Execution trace collection (tool calls, model calls, latency, tokens)
- Model fallback routing — automatically downgrades to a cheaper capable model when primary is unavailable or over budget

---

### Network Plane
MCP (Model Context Protocol) proxy and tool discovery layer.

**Key responsibilities:**
- Proxies all agent tool calls through GovernOS before they hit actual MCP servers
- Dynamic MCP server discovery — agents declare tool requirements in `agent.yaml`, network plane resolves the live endpoint
- Rate limiting and quota enforcement per agent
- Tool call audit logging with before/after state capture

**Key file:** [`services/network-plane/app/services/mcp_discoverer.py`](services/network-plane/app/services/mcp_discoverer.py)

---

### State Plane
Persistent memory and state management for long-running agents.

**Key responsibilities:**
- Conversation memory — stores and retrieves agent message history
- Sub-100ms state snapshots — point-in-time captures of agent state
- State rehydration — restore agent from snapshot on cold start
- Webhook delivery — push agent lifecycle events to external systems

---

## Python SDK (`nuuvixx`)

The official Python SDK for building agents on AgentOS.

### Installation

```bash
pip install nuuvixx
```

### Modules

| Module | File | Purpose |
|--------|------|---------|
| `MCPClient` | `mcp.py` | Tool calling with automatic GovernOS interception |
| `A2AClient` | `a2a.py` | Agent-to-Agent commerce (discover, contract, settle) |
| `AgentLifecycle` | `lifecycle.py` | Start, stop, checkpoint from within an agent |
| `AgentOSClient` | `client.py` | HTTP client for the Control Plane API |
| `CLI helpers` | `cli.py` | CLI command utilities |
| `Agent` | `agent.py` | Base agent class |

### Quick Start

```python
from nuuvixx import Agent, MCPClient, A2AClient

class MyAgent(Agent):
    async def run(self, task: str) -> str:
        # All tool calls go through GovernOS automatically
        mcp = MCPClient(base_url="http://127.0.0.1:8010")
        result = await mcp.call_tool("web_search", {"query": task})
        return result["output"]
```

### A2A Commerce

```python
from nuuvixx import A2AClient

client = A2AClient(base_url="http://127.0.0.1:8005")

# Discover agents offering a capability
providers = await client.discover("summarize:document")

# Create a service contract
contract = await client.negotiate(
    buyer_slug="my-org/orchestrator",
    seller_slug=providers[0]["agent_slug"],
    capability="summarize:document"
)

# Execute the task, then settle
result = await client.execute_task(contract["contract_id"], input_data)
await client.settle_contract(contract["contract_id"], output_data=result)
```

Every settlement generates an immutable provenance record with SHA-256 payload hashing.

### MCP Integration

```python
from nuuvixx import MCPClient

mcp = MCPClient(base_url="http://127.0.0.1:8010")

# List available tools (from agent.yaml tool declarations)
tools = await mcp.list_tools()

# Call a tool — automatically routed through GovernOS SENTINEL
result = await mcp.call_tool(
    tool_name="database_query",
    parameters={"sql": "SELECT * FROM users LIMIT 10"},
    agent_slug="my-org/my-agent"
)
```

---

## `agent.yaml` Schema

Every agent on AgentOS is declared with a single `agent.yaml` manifest:

```yaml
name: my-agent
version: "1.0.0"
description: "An example agent"

runtime:
  model: gemini-2.5-pro
  fallback_model: gemini-2.0-flash
  max_tokens: 8192
  timeout_seconds: 30

tools:
  - name: web_search
    server: mcp://tools.nuuvixx.io/search
    scope: read
  - name: database_query
    server: mcp://db.nuuvixx.io/query
    scope: read_write

budget:
  max_cost_per_run: 0.50
  max_tokens_per_run: 100000
  alert_threshold: 0.80

governance:
  policy_set: enterprise-strict
  require_human_approval: false
  allowed_tool_scopes: [read, read_write]
```

**JSON Schema:** [`agent.yaml.schema.json`](agent.yaml.schema.json)

---

## CLI (`av`)

AgentOS ships the `av` CLI for local development and deployment.

```bash
# Start a local agent
av run my-agent

# Start with hot-reload
av run my-agent --watch

# Stream live logs
av logs my-agent

# Attach debugger
av debug my-agent

# Check status dashboard
av status

# Roll back to last checkpoint
av rollback my-agent

# Run full local simulation
av simulate
```

---

## Getting Started

### Prerequisites
- Python 3.11+

### Start All Service Planes

```bash
# Control Plane
cd services/control-plane
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload

# Execution Plane
cd services/execution-plane
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload

# Network Plane (MCP Proxy)
cd services/network-plane
uvicorn app.main:app --host 0.0.0.0 --port 8012 --reload

# State Plane
cd services/state-plane
uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload
```

Or use the root startup script:
```powershell
.\start-all.ps1
```

### Environment Variables

```env
AGENTOS_CONTROL_PORT=8010
AGENTOS_EXECUTION_PORT=8011
AGENTOS_NETWORK_PORT=8012
AGENTOS_STATE_PORT=8013
AGENTSTORE_HOST=http://127.0.0.1:8005
AGENTGOVERN_HOST=http://127.0.0.1:8025
```

---

## Testing

```bash
cd AgentOS

# A2A integration tests
python test_a2a.py

# MCP proxy tests
python test_mcp.py

# State plane tests (memory, snapshots, webhooks)
python test_phase4.py
```

---

## Integration with Other Pillars

| Direction | Integration |
|-----------|------------|
| AgentOS → AgentGovernOS | Every MCP tool call is intercepted by GovernOS SENTINEL before execution. This is in-runtime, not middleware — it cannot be bypassed. |
| AgentOS → AgentStore | Before running a store-sourced agent, OS fetches the trust gate and dependency lockfile from AgentStore. |
| AgentOS SDK → AgentStore | The `A2AClient` in the SDK calls AgentStore's A2A commerce API to discover, contract, and settle with peer agents. |
| AgentStudio → AgentOS | Studio's VS Code extension triggers `av run` via the control plane API for local hot-reload development. |

---

## Key Design Decisions

**Why 4 separate planes?**
Each plane scales independently. MCP proxy (Network Plane) can be replicated for high tool-call throughput without scaling the state or control services.

**Why in-runtime governance?**
Middleware-based governance can be bypassed by agents that directly call tool APIs. Routing all calls through the Network Plane's MCP proxy — which calls GovernOS before forwarding — makes policy enforcement structurally unbypassable.

**Why sub-100ms snapshots?**
Long-running agents on serverless infrastructure die on cold starts. Snapshots allow agents to resume from any point in their execution, making scale-to-zero viable for stateful workflows.
