"use client";

import React from "react";
import { CodeBlock, DocH2, DocH3, Callout, PortBadge } from "@/components/docs/DocComponents";
import Link from "next/link";
import { ExternalLink, Zap } from "lucide-react";

export default function QuickstartPage() {
  return (
    <article className="docs-article">
      {/* Page Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Zap className="w-3.5 h-3.5" />
          Getting Started
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">Quickstart</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Get AgentVerse running locally in under 5 minutes. Build, deploy, and govern autonomous AI agents
          with enterprise-grade security baked in from day one.
        </p>
      </div>

      {/* Prerequisites */}
      <DocH2>Prerequisites</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        {[
          { name: "Docker Desktop", version: "v24+", url: "https://docker.com" },
          { name: "Node.js", version: "v18 LTS+", url: "https://nodejs.org" },
          { name: "Git", version: "v2.30+", url: "https://git-scm.com" },
        ].map(dep => (
          <a key={dep.name} href={dep.url} target="_blank" rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-white/4 border border-white/10 hover:border-white/25 hover:bg-white/7 transition-all group"
          >
            <div>
              <div className="text-white text-sm font-semibold">{dep.name}</div>
              <div className="text-white/40 text-xs">{dep.version}</div>
            </div>
            <ExternalLink className="w-3.5 h-3.5 text-white/20 group-hover:text-white/50" />
          </a>
        ))}
      </div>

      {/* Step 1 */}
      <DocH2>Step 1 — Clone the Repository</DocH2>
      <CodeBlock language="bash" code={`git clone https://github.com/nuuvixx/agentsecosystem
cd agentsecosystem`} />

      {/* Step 2 */}
      <DocH2>Step 2 — Configure Environment</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Copy the example environment file. For local development the defaults work out of the box.
        For production, rotate all secrets before deploying.
      </p>
      <CodeBlock language="bash" code={`cp .env.example .env
# Edit .env and replace placeholder values with real secrets`} />

      <Callout type="warning">
        Never commit your <code>.env</code> file to version control. The real <code>.env</code> is in{" "}
        <code>.gitignore</code>. Only commit <code>.env.example</code>.
      </Callout>

      {/* Step 3 */}
      <DocH2>Step 3 — Start All Services</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        One command launches the entire 7-service stack. First run downloads ~2 GB of Docker images.
      </p>
      <CodeBlock language="bash" code={`docker compose up -d
# Wait ~60 seconds for all services to become healthy
docker compose ps`} />

      <Callout type="tip">
        You can watch live logs with <code>docker compose logs -f agentverse-console</code> to see
        when the console Next.js build finishes.
      </Callout>

      {/* Step 4 — Service Map */}
      <DocH2>Step 4 — Open the Services</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        <PortBadge port="3051" label="AgentVerse Console" desc="Main unified UI — deploy, govern, and monitor agents." />
        <PortBadge port="8050" label="AgentStore Marketplace" desc="Browse, publish, and install verified community agents." />
        <PortBadge port="8005" label="AgentStore API" desc="REST API for registry, search, billing, and A2A commerce." />
        <PortBadge port="8025" label="GovernOS API" desc="JWT auth, OWASP policy enforcement, SHA-256 audit ledger." />
        <PortBadge port="8010" label="Control Plane" desc="MicroVM lifecycle management and agent execution dispatch." />
        <PortBadge port="8012" label="Execution Plane" desc="Firecracker MicroVM pool and sandboxed tool execution." />
      </div>

      {/* Step 5 */}
      <DocH2>Step 5 — Publish Your First Agent</DocH2>
      <DocH3>Using the CLI</DocH3>
      <CodeBlock language="bash" code={`# Install the AgentVerse CLI
npm install -g @nuuvixx/cli

# Authenticate
nuuvixx login

# Create a new agent project
nuuvixx init my-first-agent
cd my-first-agent

# Validate the manifest
nuuvixx validate agent.yaml

# Publish to AgentStore
nuuvixx publish`} />

      <DocH3>Using the API directly</DocH3>
      <CodeBlock language="bash" code={`curl -X POST http://localhost:8005/api/v1/registry/agents \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{
    "builder_id": "my-org",
    "category": "automation",
    "agent_yaml": "name: hello-agent\\nversion: 1.0.0\\ndescription: My first agent"
  }'`} />

      {/* Next Steps */}
      <DocH2>Next Steps</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {[
          { href: "/docs/architecture", label: "Platform Architecture", desc: "Understand the 3-tier microservice topology" },
          { href: "/docs/agent-yaml",   label: "agent.yaml Reference", desc: "Full annotated manifest schema" },
          { href: "/docs/sentinel",     label: "GovernOS Sentinel",    desc: "OWASP ASI security enforcement" },
          { href: "/docs/sdk-python",   label: "Python SDK",           desc: "Build agents in Python" },
        ].map(item => (
          <Link key={item.href} href={item.href}
            className="p-4 rounded-xl bg-white/4 border border-white/10 hover:border-[#E5252A]/40 hover:bg-[#E5252A]/5 transition-all group"
          >
            <div className="text-sm font-semibold text-white group-hover:text-[#E5252A] transition-colors mb-1">{item.label} →</div>
            <div className="text-xs text-white/50 font-sans">{item.desc}</div>
          </Link>
        ))}
      </div>
    </article>
  );
}
