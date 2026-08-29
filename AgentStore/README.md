# AgentStore

> **Pillar 4 of AgentVerse — The Verified Agent Marketplace**

AgentStore is a production-grade marketplace for autonomous AI **services**, not code. Every agent listed on AgentStore is verified, priced, and executable — think of it as the App Store for agents where builders earn revenue and enterprises discover trusted, compliant AI services.

---

## Overview

```
AgentStore
├── backend/              # FastAPI marketplace API (:8005)
│   └── app/
│       ├── routers/      # 10 API route modules
│       └── services/     # 13 business logic engines
└── frontend/             # Next.js marketplace UI (:8050)
    ├── app/              # App router pages
    └── components/       # Shared UI components
```

---

## Features

### Agent Registry
- Publish agents via structured JSON manifest or raw `agent.yaml`
- Unique `builder/agent-name` slug generation with collision handling
- Semantic version management (`1.0.0`, `1.1.0`, etc.)
- Full CRUD: publish, update, deprecate, delete

### Verification Pipeline (ASI01–ASI10)
Every published agent goes through an automated 10-point security scan before listing:

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

### Trust Score Engine
Each agent receives a composite trust score (0–100) across 5 weighted dimensions:

| Dimension | Weight |
|-----------|--------|
| Security scan pass rate | 30% |
| Runtime compliance pass rate | 25% |
| Reliability (uptime, error rate) | 20% |
| Builder verification status | 15% |
| Community signals (installs, reviews) | 10% |

### Monetization & Billing
- **Per-execution pricing** — metered billing per agent invocation
- **Subscription tiers** — Free / Pro / Enterprise
- **Revenue share** — 80% to builders, 20% platform fee
- **Razorpay integration** — real payment gateway for x402 micropayments
- **Execution metering** — token usage, latency, cost attribution per agent

### Enterprise Procurement
- Departmental budget allocation and enforcement
- Multi-step approval workflows (request → review → approve/reject)
- Private organizational catalogs with access control
- Bulk procurement with volume pricing

### Composability
- Publish multi-agent compositions as single marketplace listings
- Dependency resolution: install an agent and all its dependencies automatically
- Composition validation: check inter-agent compatibility before publish
- Lockfile generation for reproducible installs

### A2A Commerce (Agent-to-Agent)
Agents can autonomously discover, hire, and settle with other agents:
- **Service directory** — searchable by capability slug (e.g., `search:flights`)
- **Contract negotiation** — structured service contracts between buyer and seller agents
- **x402 settlement** — post-task micropayment settlement with SHA-256 provenance hashing
- **Contract history** — full audit trail of all A2A contracts

### Incidents & SLA
- Incident creation and tracking per agent
- SLA breach detection and alerting
- Incident history for trust score computation

---

## API Reference

Base URL: `http://127.0.0.1:8005`

| Router | Prefix | Description |
|--------|--------|-------------|
| `registry.py` | `/api/v1/registry` | Publish, list, get, update agents |
| `verification.py` | `/api/v1/verification` | Trigger scans, get reports, issue badges |
| `billing.py` | `/api/v1/billing` | Meter executions, get payouts, usage stats |
| `pricing.py` | `/api/v1/pricing` | Pricing plans, tier management |
| `search.py` | `/api/v1/search` | Full-text + semantic agent search |
| `procurement.py` | `/api/v1/procurement` | Enterprise requests, approvals, budgets |
| `compositions.py` | `/api/v1/compositions` | Compose, validate, resolve dependencies |
| `a2a_commerce.py` | `/api/v1/a2a` | A2A directory, contracts, settlements |
| `incidents.py` | `/api/v1/incidents` | Create, update, resolve incidents |
| `cli_api.py` | `/api/v1/cli` | CLI-specific endpoints (lockfiles, trust gates) |

Interactive docs: **`http://127.0.0.1:8005/docs`**

### Key Endpoints

```
POST   /api/v1/registry/publish           Publish a new agent
GET    /api/v1/registry/agents            List all agents
GET    /api/v1/registry/agents/{slug}     Get agent by slug
POST   /api/v1/verification/scan/{id}     Trigger ASI scan
GET    /api/v1/verification/report/{id}   Get scan report
POST   /api/v1/billing/meter              Record execution + meter cost
GET    /api/v1/billing/payout/{builder}   Get builder revenue summary
POST   /api/v1/search/agents             Search marketplace
POST   /api/v1/procurement/request        Create procurement request
POST   /api/v1/a2a/discover              Discover agents by capability
POST   /api/v1/a2a/contracts             Create A2A service contract
POST   /api/v1/a2a/contracts/{id}/settle  Settle contract post-task
```

---

## Service Layer

| Service | File | Responsibility |
|---------|------|---------------|
| Security Scanner | `security_scanner.py` | ASI01-ASI10 scan engine |
| Verification Pipeline | `verification_pipeline.py` | Orchestrates full scan + badge issuance |
| Trust Engine | `trust_engine.py` | Computes composite trust score |
| Billing Engine | `billing_engine.py` | Execution metering + revenue share |
| Razorpay Client | `razorpay_client.py` | Payment gateway integration |
| A2A Engine | `a2a_engine.py` | Contract lifecycle + settlement |
| Search Engine | `search_engine.py` | Full-text + filter search |
| Procurement Engine | `procurement_engine.py` | Enterprise approval workflow |
| Composition Validator | `composition_validator.py` | Multi-agent compatibility checks |
| Dependency Resolver | `dependency_resolver.py` | Transitive dependency resolution |
| YAML Validator | `yaml_validator.py` | `agent.yaml` schema validation |
| Slug Generator | `slug_generator.py` | Unique `builder/name` slug creation |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (frontend only)

### Backend

```bash
cd AgentStore/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

### Frontend

```bash
cd AgentStore/frontend
npm install
npm run dev
# Runs on http://localhost:8050
```

### Environment Variables

The backend reads from the root `.env` file:

```env
AGENTSTORE_PORT=8005
AGENTSTORE_HOST=http://127.0.0.1:8005
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
```

---

## Testing

```bash
cd AgentStore/backend

# Unit tests
pytest tests/ -v

# Individual test suites
pytest tests/test_registry.py       # Registry CRUD
pytest tests/test_billing.py        # Billing + metering
pytest tests/test_procurement.py    # Enterprise procurement
pytest tests/test_a2a_commerce.py   # A2A contracts
pytest tests/test_composability.py  # Composition + deps
pytest tests/test_security_scanner.py # ASI scanner

# Full route verification
python verify_all_routes.py

# Cross-component integration
python verify_integration.py
```

---

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Marketplace home — featured + trending agents |
| `/search` | Full search with filters (trust, category, price) |
| `/agents/[builder]/[agent]` | Agent detail page |
| `/agents/[builder]/[agent]/security` | Security report + trust breakdown |
| `/agents/[builder]/[agent]/install` | Install + lockfile download |
| `/compositions` | Browse multi-agent compositions |
| `/compositions/[...slug]` | Composition detail + dependency graph |
| `/publish` | Publisher dashboard — submit new agent |
| `/pricing` | Platform pricing tiers |
| `/dashboard` | Builder analytics dashboard |
| `/dashboard/revenue` | Revenue + payout tracking |
| `/dashboard/procurement` | Enterprise procurement management |
| `/dashboard/a2a-commerce` | A2A contract history + settlements |

---

## Infrastructure

```yaml
# AgentStore/infra/docker-compose.yml
services:
  agentstore-api:
    build: ./backend
    ports: ["8005:8005"]
  agentstore-ui:
    build: ./frontend
    ports: ["8050:8050"]
```

---

## Integration with Other Pillars

| Bridge | Integration |
|--------|------------|
| AgentStudio → AgentStore | Studio publishes validated agents via `POST /api/v1/registry/publish` |
| AgentOS → AgentStore | OS fetches trust gate + lockfile before executing a store agent |
| AgentGovernOS → AgentStore | Governance catalog gate blocks non-compliant agents from enterprise procurement |
| AgentOS ↔ AgentStore | A2A commerce contracts resolved through the store's service directory |
