"use client";

import React from "react";
import { DocH2, DocH3, Callout, PortBadge, ApiEndpointCard, CodeBlock } from "@/components/docs/DocComponents";
import { Layers } from "lucide-react";

export default function ArchitecturePage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Layers className="w-3.5 h-3.5" />
          Getting Started
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">Platform Architecture</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          AgentVerse is a horizontally scalable, multi-tenant operating system for autonomous AI agents.
          It splits workloads across three independent service tiers to guarantee zero-latency hotpaths
          and unbypassable kernel isolation.
        </p>
      </div>

      <DocH2>Three-Tier Service Topology</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <PortBadge port="8005" label="AgentStore API" desc="Verified marketplace. YAML registry, semantic search, A2A commerce, billing, and x402 micropayment settlement." />
        <PortBadge port="8010–8014" label="AgentOS Planes" desc="Control, Execution, and State planes. MicroVM lifecycle management, Firecracker sandbox pooling, and state streaming." />
        <PortBadge port="8025" label="GovernOS API" desc="In-runtime policy enforcement, JWT/API-key auth, SHA-256 Merkle audit ledger, GDPR data export, OWASP ASI coverage." />
      </div>

      {/* Architecture Diagram */}
      <DocH2>Service Communication Map</DocH2>
      <div className="rounded-xl border border-white/10 bg-[#070910] p-6 font-mono text-xs mb-6 overflow-x-auto">
        <pre className="text-white/70 leading-relaxed">{`
  ┌─────────────────────────────────────────────────────────┐
  │                   AgentVerse Console :3051              │
  │            (Next.js unified operator dashboard)         │
  └───────────────┬────────────────┬────────────────┬───────┘
                  │                │                │
        ┌─────────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
        │  AgentStore API │  │ AgentOS     │  │ GovernOS    │
        │     :8005       │  │ Planes      │  │ API :8025   │
        │  Registry       │  │ :8010-8014  │  │ Policy+Auth │
        │  Search         │  │ MicroVMs    │  │ Audit Ledger│
        │  Billing        │  │ Firecracker │  │ OWASP ASI   │
        └─────────────────┘  └─────────────┘  └─────────────┘
                  │                │                │
        ┌─────────▼──────────────────▼────────────────┐
        │            Shared Docker Network             │
        │            agentverse-net (bridge)           │
        └─────────────────────────────────────────────┘
`}</pre>
      </div>

      <DocH2>AgentOS Execution Model</DocH2>
      <DocH3>MicroVM Isolation</DocH3>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Each agent execution runs in a dedicated Firecracker MicroVM — hardware-level isolation with
        sub-100ms cold start. No shared process space, no shared file system, no container escape vectors.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {[
          { label: "Isolation Level", value: "Hardware MicroVM (Firecracker)" },
          { label: "Cold Start Latency", value: "< 100ms" },
          { label: "Network Policy", value: "Zero-trust overlay (deny all by default)" },
          { label: "File System", value: "ephemeral tmpfs, read-only rootfs" },
          { label: "Memory Limit", value: "Configurable per agent.yaml" },
          { label: "CPU Quota", value: "cgroup v2 enforced" },
        ].map(item => (
          <div key={item.label} className="flex items-center justify-between p-3 rounded-lg bg-white/4 border border-white/10">
            <span className="text-white/50 text-xs font-sans">{item.label}</span>
            <span className="text-emerald-400 text-xs font-mono font-bold">{item.value}</span>
          </div>
        ))}
      </div>

      <DocH3>Tool Dispatch Protocol (MCP)</DocH3>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        All agent tool calls flow through the Model Context Protocol (MCP). The GovernOS Sentinel kernel
        intercepts every tool call before execution and evaluates it against the agent's policy set.
      </p>
      <CodeBlock language="yaml" code={`# Tool call flow:
# 1. Agent generates tool_call request
# 2. Control Plane intercepts → GovernOS Sentinel evaluates
# 3. Sentinel checks: scope, PII, cost budget, OWASP policies
# 4. If APPROVED: Execution Plane dispatches to MCP server
# 5. Result flows back → State Plane logs SHA-256 hash
# 6. Response returned to agent within execution context`} />

      <DocH2>Data Persistence Architecture</DocH2>
      <Callout type="note">
        Local development uses SQLite for zero-configuration startup. Production deployments should
        replace all SQLite instances with PostgreSQL 15+ for full ACID compliance and horizontal scaling.
      </Callout>
      <div className="space-y-2 mb-6">
        {[
          { service: "AgentStore API", db: "SQLite → PostgreSQL", path: "agentstore.db" },
          { service: "GovernOS API",   db: "SQLite → PostgreSQL", path: "sqlite.db" },
          { service: "AgentOS Planes", db: "SQLite (aiosqlite)",  path: "agentos.db" },
        ].map(item => (
          <div key={item.service} className="flex items-center gap-4 p-3 rounded-lg bg-white/4 border border-white/8">
            <span className="text-white/80 text-xs w-32 shrink-0">{item.service}</span>
            <span className="text-emerald-400 text-xs font-mono">{item.db}</span>
            <span className="text-white/30 text-xs ml-auto font-mono">{item.path}</span>
          </div>
        ))}
      </div>

      <DocH2>Docker Compose Services</DocH2>
      <CodeBlock language="bash" code={`# Check all service health:
docker compose ps

# Expected output:
# agentstore-backend    running (healthy)   0.0.0.0:8005
# agentos-control-plane running (healthy)   0.0.0.0:8010
# agentos-execution-plane running           0.0.0.0:8012
# agentos-state-plane   running             0.0.0.0:8014
# agentgovernos-api     running (healthy)   0.0.0.0:8025
# agentverse-console    running             0.0.0.0:3051`} />
    </article>
  );
}
