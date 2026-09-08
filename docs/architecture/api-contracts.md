# AgentStudio — API Contracts Specification

## Versioning & Standards

- All Control Plane endpoints are prefixed with `/v1`.
- All mutating endpoints (`POST`, `PUT`, `DELETE`) require `Idempotency-Key` header.
- Errors follow RFC 7807 Problem Details format.

---

## 1. Manifest & Versioning Endpoints

### POST `/v1/agents/validate`
Validates a raw YAML or JSON manifest string.
- **Request Body**: `{ "yaml": "..." }`
- **Response**: `{ "valid": true|false, "errors": [ { "severity": "error", "code": "...", "message": "...", "path": "..." } ] }`

### POST `/v1/agents/plan`
Generates execution plan, estimates tokens and USD cost, and performs pre-flight policy check.
- **Request Body**: `{ "yaml": "..." }`
- **Response**: `{ "canonicalHash": "sha256:...", "estimatedCostUsd": 0.05, "policyVerdict": "ALLOW", "plan": { "nodes": [...], "edges": [...] } }`

### POST `/v1/agents/versions`
Creates an immutable version record.
- **Request Body**: `{ "agentId": "...", "yaml": "..." }`
- **Response**: `{ "versionId": "...", "manifestHash": "sha256:...", "version": "1.0.0", "createdAt": "..." }`

---

## 2. Run Endpoints

### POST `/v1/runs`
Queues a new run.
- **Request Body**: `{ "agentVersionId": "...", "input": "...", "env": {} }`
- **Response**: `{ "runId": "...", "status": "QUEUED", "createdAt": "..." }`

### GET `/v1/runs/{runId}`
Fetches run status and step summary.
- **Response**: `{ "runId": "...", "status": "RUNNING", "policyVerdict": "ALLOW", "actualCostUsd": 0.012, "startedAt": "..." }`

### POST `/v1/runs/{runId}:cancel`
Cancels an active run.
- **Response**: `{ "status": "CANCELLED" }`

### POST `/v1/runs/{runId}:approve`
Resolves an `ESCALATED` run approval gate.
- **Request Body**: `{ "approved": true|false, "notes": "..." }`
- **Response**: `{ "status": "RUNNING" | "CANCELLED" }`

---

## 3. WebSockets

### `/ws/v1/runs/{runId}/events`
Subscribes to live step-by-step trace events for a specific run.
