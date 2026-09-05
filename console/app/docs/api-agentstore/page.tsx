"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, ApiPlayground, ApiEndpointCard } from "@/components/docs/DocComponents";
import { Server } from "lucide-react";

export default function AgentStoreApiPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Server className="w-3.5 h-3.5" />
          API Reference
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">AgentStore API</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          REST API for the AgentStore marketplace registry. Covers agent publishing, versioning, search,
          billing, A2A commerce, and enterprise procurement.
          Running on <code className="text-[#4EC9B0]">localhost:8005</code>.
        </p>
      </div>

      {/* Interactive Docs Link */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-white/4 border border-white/10 mb-8">
        <Server className="w-5 h-5 text-[#E5252A] shrink-0" />
        <div>
          <div className="text-sm font-semibold text-white">Swagger UI</div>
          <div className="text-xs text-white/50 font-sans">Full interactive API documentation with request/response examples</div>
        </div>
        <a
          href="http://localhost:8005/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto px-4 py-2 rounded-lg bg-[#E5252A] text-white text-xs font-bold hover:bg-[#E5252A]/80 transition-colors shrink-0"
        >
          Open Swagger →
        </a>
      </div>

      <DocH2>Authentication</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Write endpoints (publish, versions, delete) require an <code className="text-[#4EC9B0]">X-API-Key</code> header.
        Read endpoints (list, search, get detail) are public.
      </p>
      <CodeBlock language="bash" code={`# All write requests require:
curl -H "X-API-Key: your-api-key" \\
  -H "Content-Type: application/json" \\
  ...`} />

      <DocH2>Registry — Agents</DocH2>
      <div className="space-y-1 mb-6 rounded-xl border border-white/10 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 text-[10px] text-white/30 font-bold uppercase tracking-wider">
          Base path: /api/v1/registry/agents
        </div>
        <ApiEndpointCard method="GET"    path=""                           desc="List all active agents. Supports category filter and pagination." />
        <ApiEndpointCard method="POST"   path=""                           desc="Publish a new agent. Requires X-API-Key. Validates agent.yaml." />
        <ApiEndpointCard method="GET"    path="/{slug}"                    desc="Get full agent detail including all versions." />
        <ApiEndpointCard method="GET"    path="/{slug}/versions"           desc="List all published versions for an agent." />
        <ApiEndpointCard method="POST"   path="/{slug}/versions"           desc="Publish a new version for an existing agent." />
        <ApiEndpointCard method="DELETE" path="/{slug}/versions/{version}" desc="Retract a specific version (sets status=retracted)." />
      </div>

      <DocH3>Try It — List Agents</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/api/v1/registry/agents?limit=5"
        baseUrl="http://localhost:8005"
      />

      <DocH3>Try It — Publish an Agent</DocH3>
      <ApiPlayground
        method="POST"
        endpoint="/api/v1/registry/agents"
        baseUrl="http://localhost:8005"
        defaultBody={JSON.stringify({
          builder_id: "my-org",
          category: "automation",
          agent_yaml: "name: hello-agent\nversion: 1.0.0\ndescription: My first AgentVerse agent\nruntime:\n  model: gpt-4o\n  max_tokens: 2048"
        }, null, 2)}
      />

      <DocH2>Search</DocH2>
      <div className="space-y-1 mb-6 rounded-xl border border-white/10 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 text-[10px] text-white/30 font-bold uppercase tracking-wider">
          Base path: /api/v1/search
        </div>
        <ApiEndpointCard method="GET" path="/agents?q={query}" desc="Semantic or keyword search across agent name, description, and tags." />
        <ApiEndpointCard method="GET" path="/agents?category={cat}" desc="Filter agents by category (support, finance, devops, research, etc)." />
      </div>

      <DocH3>Try It — Search Agents</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/api/v1/search/agents?q=support"
        baseUrl="http://localhost:8005"
      />

      <DocH2>CLI API</DocH2>
      <div className="space-y-1 mb-6 rounded-xl border border-white/10 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 text-[10px] text-white/30 font-bold uppercase tracking-wider">
          Base path: /api/v1/cli
        </div>
        <ApiEndpointCard method="POST" path="/validate" desc="Validate an agent.yaml manifest against the JSON Schema." />
        <ApiEndpointCard method="POST" path="/publish"  desc="Publish via CLI (wraps registry publish with CLI-specific auth)." />
        <ApiEndpointCard method="GET"  path="/status"   desc="Get CLI authentication and account status." />
      </div>

      <Callout type="note">
        The full OpenAPI spec is always available at{" "}
        <a href="http://localhost:8005/openapi.json" className="text-[#4EC9B0] underline" target="_blank" rel="noopener noreferrer">
          http://localhost:8005/openapi.json
        </a>. Import it into Postman or Insomnia for a complete testing environment.
      </Callout>

      <DocH2>Rate Limits</DocH2>
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Endpoint Class</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Limit</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Window</th>
            </tr>
          </thead>
          <tbody>
            {[
              { cls: "Read (GET)",      limit: "100 req",  window: "Per minute, per IP" },
              { cls: "Write (POST)",    limit: "10 req",   window: "Per minute, per API key" },
              { cls: "Publish",         limit: "10 agents", window: "Per day, per API key" },
              { cls: "Search",          limit: "60 req",   window: "Per minute, per IP" },
            ].map(row => (
              <tr key={row.cls} className="border-b border-white/6 hover:bg-white/3">
                <td className="px-4 py-3 text-white/80">{row.cls}</td>
                <td className="px-4 py-3 text-emerald-400 font-mono font-bold">{row.limit}</td>
                <td className="px-4 py-3 text-white/50 font-sans">{row.window}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
