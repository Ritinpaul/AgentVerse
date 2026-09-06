# AgentStudio

> **Pillar 1 of AgentVerse — The Agent Builder IDE**

AgentStudio is a VS Code extension and companion web UI for building production-grade autonomous AI agents. It treats `agent.yaml` as the source of truth and brings governance, cost estimation, red-team testing, and team collaboration directly into the developer's editor.

---

## Overview

```
AgentStudio
├── vscode-extension/           # VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts        # Extension entry point
│   │   ├── commands/           # Command handlers (run, deploy, publish)
│   │   ├── core/               # Embedded engines (AI builder, RBAC, policy)
│   │   ├── providers/          # VS Code UI providers (tree views, status bar)
│   │   └── services/           # External API clients (AgentStore, GovernOS)
│   └── webview/                # React webview panels
│       └── src/
│           ├── app/            # Feature panels
│           └── contexts/       # React contexts (RBAC)
├── agent.yaml                  # Sample agent manifest
├── agent.yaml.schema.json      # Full JSON schema for agent.yaml
└── .agentstudio/               # Workspace config (policies, audit log)
```

---

## Features

### `agent.yaml` Editor
The core of AgentStudio is a declarative YAML-based agent manifest. The extension provides:
- **JSON Schema validation** — real-time inline errors and completions as you type
- **Hover documentation** — hover over any field to see what it does and valid values
- **Inline governance warnings** — policy violations surface as VS Code diagnostics (squiggly lines) before you even save
- **YAML assistant** — AI-powered suggestions for tool declarations, model selection, and budget configuration

### Real-time Cost Estimation
The **Budget Status Bar** shows a live cost estimate per run as you edit your `agent.yaml`:
- Estimates based on declared model, max tokens, and tool call frequency
- Updates dynamically as you change runtime config
- Alerts when the budget ceiling is set above policy thresholds

### Local Agent Runner
Run your agent locally directly from VS Code without leaving the editor:
```
AgentVerse: Run Agent Locally   (Ctrl+Shift+R)
```
- Launches the AgentOS execution plane for your agent
- Streams logs directly into the VS Code Output panel
- Supports hot-reload — changes to `agent.yaml` restart the agent automatically

### Deploy to Cloud
```
AgentVerse: Deploy to Cloud     (Ctrl+Shift+D)
```
- Deploys to AgentOS staging or production
- Enforces deployment policies before allowing production deploys
- Shows deployment status and live health metrics

### Publish to AgentStore
```
AgentVerse: Publish to Store    (Ctrl+Shift+P)
```
- Validates the agent manifest against the full JSON schema
- Triggers an ASI scan via AgentGovernOS before submission
- Submits to AgentStore with pricing configuration
- Returns the public marketplace URL on success

---

## VS Code Providers

| Provider | File | Description |
|----------|------|-------------|
| Diagnostics | `diagnostics.ts` | Inline YAML validation errors + governance warnings |
| Budget Status Bar | `budgetStatusBar.ts` | Live cost estimate in the editor status bar |
| MCP Browser | `mcpBrowser.ts` | Tree view of available MCP servers and tools |
| Visualizer | `visualizer.ts` | Visual agent composition graph |
| Red Team | `redTeamProvider.ts` | Automated red-team test runner |
| Remote Debug | `remoteDebugProvider.ts` | Attach debugger to a running AgentOS instance |
| Enterprise | `enterpriseProvider.ts` | Team catalog and enterprise policy browser |

---

## Embedded Engines

AgentStudio embeds lightweight versions of the governance and RBAC engines directly in the extension — no network call required for basic checks:

| Engine | File | Purpose |
|--------|------|---------|
| Embedded Policy Engine | `core/embeddedPolicyEngine.ts` | Inline policy evaluation as you type |
| Embedded RBAC Engine | `core/embeddedRBACEngine.ts` | Role-based access control for team features |
| Embedded AI Builder | `core/embeddedAiBuilder.ts` | AI-assisted `agent.yaml` generation |
| Embedded Audit Logger | `core/embeddedAuditLogger.ts` | Local audit log for developer actions |
| YAML Assistant | `core/yamlAssistant.ts` | Contextual completions and suggestions |
| Native Git | `core/nativeGit.ts` | Git-aware merge and diff for agent.yaml |
| Native SSO | `core/nativeSSO.ts` | Enterprise SSO authentication |

---

## Webview Panels

The extension opens interactive React panels for complex workflows:

| Panel | File | Description |
|-------|------|-------------|
| Agent Builder | `app/AgentBuilderPanel.tsx` | Visual drag-and-drop agent composer |
| Red Team Panel | `app/RedTeamPanel.tsx` | Run automated adversarial probes against your agent |
| Remote Debug Panel | `app/RemoteDebugPanel.tsx` | Live debug view with variable inspector |
| Compliance Report | `app/ComplianceReport.tsx` | Full ASI01-ASI10 scan results with remediation |
| Enterprise Dashboard | `app/EnterpriseDashboard.tsx` | Team health metrics + policy compliance overview |
| Team Dashboard | `app/team/TeamDashboard.tsx` | Workspace members, roles, and deployment approvals |
| Team Management | `app/team/TeamManagement.tsx` | Add/remove members, assign roles |
| Workspace View | `app/team/WorkspaceView.tsx` | Shared workspace + agent inventory |
| Deployment Approval | `app/team/DeploymentApproval.tsx` | Review and approve/reject deployment requests |
| Deployment Policy Config | `app/team/DeploymentPolicyConfig.tsx` | Configure deployment gates and required approvers |
| Agent Health Card | `app/team/AgentHealthCard.tsx` | Per-agent health + cost metrics |

---

## `agent.yaml` Schema Reference

The full schema is defined in [`agent.yaml.schema.json`](agent.yaml.schema.json). Below is an annotated example:

```yaml
name: job-tracker                 # Unique agent name (kebab-case)
version: "1.0.0"                  # Semantic version
description: "Tracks job applications and follows up automatically"

runtime:
  model: gemini-2.5-pro           # Primary model
  fallback_model: gemini-2.0-flash # Fallback if primary unavailable/over budget
  max_tokens: 8192                # Hard token limit per run
  timeout_seconds: 30             # Hard execution timeout

tools:
  - name: web_search              # Tool name (must match MCP server declaration)
    server: mcp://tools.nuuvixx.io/search  # MCP server endpoint
    scope: read                   # Permission scope: read | read_write | admin
  - name: send_email
    server: mcp://comms.nuuvixx.io/email
    scope: read_write

memory:
  enabled: true                   # Persist conversation history
  max_messages: 50                # Rolling window size
  semantic_search: true           # Enable vector similarity search over memory

budget:
  max_cost_per_run: 0.25          # Hard cost ceiling in USD
  max_tokens_per_run: 50000       # Hard token ceiling
  alert_threshold: 0.80           # Alert when 80% of budget consumed

governance:
  policy_set: enterprise-strict   # Policy set from AgentGovernOS
  require_human_approval: false   # Require human in the loop for sensitive actions
  allowed_tool_scopes:
    - read
    - read_write

metadata:
  category: productivity          # Marketplace category
  tags: [jobs, automation, email]
  license: Apache-2.0
```

---

## RBAC System

AgentStudio supports team workspaces with role-based access control:

| Role | Permissions |
|------|-------------|
| `owner` | All permissions including delete workspace, manage billing |
| `admin` | Manage members, configure policies, approve all deployments |
| `developer` | Build, run, deploy to staging; request production deploys |
| `viewer` | Read-only access to agents, logs, and compliance reports |

RBAC context is available in all webview panels via [`RBACContext.tsx`](vscode-extension/webview/src/contexts/RBACContext.tsx).

---

## Services

| Service | File | Description |
|---------|------|-------------|
| AgentStore Client | `services/agentStoreClient.ts` | Publish and fetch agents from AgentStore |
| Deployment Policies | `services/deploymentPolicies.ts` | Load and enforce deployment gate rules |
| RBAC Service | `services/rbacService.ts` | Fetch and cache team roles |
| SSO Auth | `services/ssoAuth.ts` | Enterprise SSO token management |
| Token Store | `services/tokenStore.ts` | Secure credential storage |
| Git Workspace | `services/gitWorkspace.ts` | Git-aware workspace operations |
| Semantic Merge | `services/semanticMerge.ts` | AI-assisted agent.yaml merge conflict resolution |

---

## Getting Started

### Prerequisites
- VS Code 1.85+
- Node.js 18+
- AgentOS Control Plane running on `:8010`
- AgentStore API running on `:8005`

### Install Extension (Development Mode)

```bash
cd AgentStudio/vscode-extension
npm install
npm run compile

# Open VS Code and press F5 to launch Extension Development Host
```

### Build Webview

```bash
cd AgentStudio/vscode-extension
npm run build:webview
```

### Build Full Extension Package

```bash
cd AgentStudio/vscode-extension
npm run package
# Outputs: agentverse-studio-x.x.x.vsix
```

---

## Commands Reference

All commands are available via the Command Palette (`Ctrl+Shift+P`):

| Command | Keyboard | Description |
|---------|----------|-------------|
| `AgentVerse: Run Agent Locally` | `Ctrl+Shift+R` | Start local agent with hot-reload |
| `AgentVerse: Deploy to Cloud` | `Ctrl+Shift+D` | Deploy to staging or production |
| `AgentVerse: Publish to Store` | `Ctrl+Shift+P` | Publish to AgentStore marketplace |
| `AgentVerse: Open Red Team Panel` | — | Launch automated adversarial testing |
| `AgentVerse: View Compliance Report` | — | Show ASI scan results |
| `AgentVerse: Open Team Dashboard` | — | Manage workspace and team |
| `AgentVerse: Attach Remote Debugger` | — | Debug a live AgentOS instance |

---

## Workspace Config (`.agentstudio/`)

AgentStudio maintains a `.agentstudio/` directory in your workspace:

```
.agentstudio/
├── policies.json    # Active governance policy configuration
└── audit.json       # Local developer action audit log
```

These files are committed to your repo so policy configuration is version-controlled alongside your agent code.

---

## Integration with Other Pillars

| Direction | Integration |
|-----------|------------|
| AgentStudio → AgentOS | `Run Locally` and `Deploy` commands call the Control Plane API at `:8010` |
| AgentStudio → AgentStore | `Publish` command submits the validated agent manifest to AgentStore at `:8005` |
| AgentStudio → AgentGovernOS | Embedded policy engine mirrors GovernOS rules locally; full scan triggered via API before publish |
