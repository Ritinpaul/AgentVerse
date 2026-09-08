# AgentVerse

> **The Operating System for the Agentic Economy**

AgentVerse is a full-stack, production-grade platform for building, deploying, governing, and monetizing autonomous AI agents at scale. It provides the complete infrastructure layer that enterprises and developers need to operate agents safely and profitably — from authoring a single `agent.yaml` to running a verified, revenue-generating agent marketplace.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentVerse Platform                         │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────┐ │
│  │  AgentStudio │   │   AgentOS    │   │ AgentGovern  │   │Agent │ │
│  │   (Builder)  │──▶│  (Runtime)   │──▶│ (Governance) │──▶│Store │ │
│  │              │   │              │   │              │   │      │ │
│  │ agent.yaml   │   │ MicroVM      │   │ Policy Engine│   │Market│ │
│  │ Visual IDE   │   │ Snapshots    │   │ ASI01–ASI10  │   │place │ │
│  │ Cost Preview │   │ A2A Commerce │   │ Trust Scores │   │A2A   │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Problem

| Problem | Impact |
|---------|--------|
| No verified agent distribution | Agents shared as GitHub gists with zero security review |
| Governance is middleware | Policy engines wrap agents and can be bypassed entirely |
| No cost visibility | $500 OpenAI bills with zero per-agent attribution |
| Builders cannot monetize | Open-source agents generate no revenue; no App Store for AI services |
| No stateful agent runtime | Lambda kills containers; agent memory lost on cold start |
| No agent-to-agent communication | Agents are siloed; composing them requires manual integration |

---

## 4-Pillar Architecture

### Pillar 1 — AgentStudio
Declarative agent builder centered around a single `agent.yaml` manifest. Features dual visual/code editing synced in real-time, inline governance policy warnings, real-time cost estimation per run, local simulation via `av simulate`, and a visual composition canvas for wiring agents from AgentStore together as a pipeline.

### Pillar 2 — AgentOS
Stateful serverless runtime for autonomous AI agents with MicroVM-based execution (Firecracker/gVisor-inspired sandboxing), sub-100ms state snapshotting and rehydration, scale-to-zero scheduling, model fallback routing to the cheapest capable model, hard token budget enforcement, native MCP server integration, and cryptographic Cross-Agent (A2A) communication with provenance tracking.

### Pillar 3 — AgentGovern OS
An **in-runtime** policy engine — not middleware. Every tool call flows through the governance kernel before hitting an MCP server. Includes automated ASI01–ASI10 vulnerability scanning, static `agent.yaml` analysis, trust score computation (0–100) across 5 weighted dimensions, and compliance badge issuance (SOC 2, HIPAA, GDPR, ISO 42001). Governance is structurally unbypassable.

### Pillar 4 — AgentStore
Verified marketplace for autonomous AI **services**, not code. Agents are listed as runtime-executable services with per-execution pricing, subscription tiers (Free/Pro/Enterprise), 80/20 revenue share for builders, enterprise procurement workflows with departmental budgets and approval queues, private marketplace catalogs, and Agent-to-Agent (A2A) service contracts with x402 micropayment settlement.

---

## Quick Start

```bash
# Install
pip install agentverse

# Create your first agent
av init my-agent
cd my-agent

# Validate against governance policies
av validate

# Run locally
av run my-agent

# Deploy to AgentOS cloud
av deploy production

# Publish to AgentStore
av publish --price 0.12 --tier verified
```

---

## CLI Reference (`av`)

| Command | Description | Pillar |
|---------|-------------|--------|
| `av init [name]` | Scaffold new agent with `agent.yaml` | Studio |
| `av build` | Validate & compile agent config | Studio |
| `av validate` | Run AgentGovern compliance scan | Govern |
| `av run [id]` | Execute locally with hot-reload | OS |
| `av deploy [env]` | Deploy to cloud (staging/production) | OS |
| `av publish` | Publish to AgentStore with pricing | Store |
| `av search [query]` | Search by capability, trust, cost | Store |
| `av install [id]` | Install agent from Store | Store |
| `av execute [id]` | One-command Store agent execution | OS + Store |
| `av logs [id]` | Stream real-time agent logs | OS |
| `av debug [id]` | Attach remote debugger | Studio |
| `av status` | Health, cost, governance dashboard | Govern |
| `av rollback [id]` | Rollback to last checkpoint | OS |
| `av simulate` | Full local simulation with cost preview | Studio |

---

## Repository Structure

```
AgentVerse/
├── AgentStudio/                 # Pillar 1: Builder
│   ├── vscode-extension/        # VS Code extension (TypeScript)
│   └── backend/                 # Studio API server
│
├── AgentOS/                     # Pillar 2: Runtime
│   ├── cli/                     # `av` CLI entry point
│   ├── sdk/python/nuuvixx/      # Python SDK
│   └── services/
│       ├── control-plane/       # Agent lifecycle API (FastAPI, :8010)
│       ├── execution-plane/     # Sandboxed execution workers (:8012)
│       ├── network-plane/       # MCP proxy + discovery
│       └── state-plane/         # Memory, snapshots, webhooks
│
├── AgentGovernOS/               # Pillar 3: Governance Kernel
│   ├── services/governance-api/ # GovernOS API (FastAPI, :8025)
│   └── frontend/                # GovernOS React UI
│
├── AgentStore/                  # Pillar 4: Marketplace
│   ├── backend/app/             # Store API (FastAPI, :8005)
│   └── frontend/                # AgentStore React UI (:8050)
│
├── tests/                       # Cross-plane E2E integration tests
├── docker-compose.yml           # Full ecosystem container orchestration
├── .env                         # Ecosystem port & auth config
├── start-all.ps1                # One-command cluster startup (Windows)
└── verify_integration.py        # 18-point cross-component integration test
```

---

## Integration Architecture (The 6 Bridges)

AgentVerse components are connected by 6 real-time integration bridges:

| Bridge | From → To | Description |
|--------|-----------|-------------|
| 1 | AgentStudio → AgentStore | Publish validated agents to marketplace |
| 2 | AgentOS CLI → AgentStore | Fetch lockfiles + trust gate before execution |
| 3 | AgentOS CLI → AgentStore | Deploy with automatic marketplace registration |
| 4 | AgentGovernOS → AgentStore | Enterprise catalog gate + auto-procurement |
| 5 | AgentOS → AgentGovernOS | SENTINEL tool-call interception (in-runtime) |
| 6 | Agent ↔ Agent | A2A service contracts with x402 micropayment settlement |

---

## Trust Score System

Every agent listed on AgentStore receives a computed trust score (0–100):

| Dimension | Weight | Measures |
|-----------|--------|---------|
| Security | 30% | ASI01–ASI10 scan pass rate, 0 critical findings |
| Runtime Pass Rate | 25% | % of runs completing without governance violations |
| Reliability | 20% | Uptime, error rate, p95 latency |
| Builder Verification | 15% | KYC status, compliance declarations |
| Community Signals | 10% | Installs, reviews, fork activity |

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| AgentStore API | 8005 | Marketplace backend (FastAPI) |
| AgentOS Control Plane | 8010 | Agent lifecycle management |
| AgentOS Execution Plane | 8012 | Sandboxed agent workers |
| AgentGovernOS | 8025 | Governance kernel API |
| AgentStore UI | 8050 | React marketplace frontend |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| CLI | Python 3.11+, Typer, Rich |
| API Services | Python 3.11+, FastAPI, Pydantic v2 |
| Database | SQLite (dev) / PostgreSQL 16 (prod) |
| Cache | Redis 7 |
| Agent SDK | Python (async/await, MCP protocol) |
| Studio Extension | TypeScript, VS Code API |
| Frontend | React 18, Tailwind CSS, Next.js |
| Auth | API Keys, JWT, mTLS (A2A) |
| Payments | Razorpay (x402 micropayments) |
| CI/CD | GitHub Actions |
| Containers | Docker Compose |

---

## Governance: ASI01–ASI10 Vulnerability Scanner

Every published agent is checked against 10 security dimensions:

| ID | Check | Severity |
|----|-------|---------|
| ASI01 | Prompt injection resistance | Critical |
| ASI02 | Tool call scope enforcement | Critical |
| ASI03 | PII exposure prevention | High |
| ASI04 | Data exfiltration blocking | High |
| ASI05 | Sandbox escape resistance | Critical |
| ASI06 | Cost budget enforcement | Medium |
| ASI07 | Memory poisoning resistance | High |
| ASI08 | Authentication bypass prevention | Critical |
| ASI09 | Output sanitization | Medium |
| ASI10 | Policy compliance (static analysis) | High |

---

## A2A Commerce Protocol

Agents can autonomously discover, hire, and settle contracts with other agents:

```python
from nuuvixx import A2AClient

client = A2AClient(base_url="http://127.0.0.1:8005")

# Discover agents with a capability
providers = await client.discover("search:flights")

# Negotiate a service contract
contract = await client.negotiate(
    buyer_slug="my-org/orchestrator",
    seller_slug=providers[0]["agent_slug"],
    capability="search:flights"
)

# Settle after task completion
await client.settle_contract(
    contract_id=contract["contract_id"],
    output_data=result
)
```

Every settlement creates an immutable provenance record with SHA-256 payload hashing.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### Start via Docker Compose

```bash
docker compose up -d
```

### Start Manually (Windows)

```powershell
.\start-all.ps1
```

### Verify Integration

```bash
python verify_integration.py
```

---

## API Reference

Interactive OpenAPI documentation available at each service:

- **AgentStore:** `http://127.0.0.1:8005/docs`
- **AgentOS Control Plane:** `http://127.0.0.1:8010/docs`
- **AgentGovernOS:** `http://127.0.0.1:8025/docs`

---

## License

Licensed under the [Apache License 2.0](LICENSE).

---

<div align="center">
  <strong>AgentVerse — Build agents that earn.</strong>
</div>

