"use client";

import React, { useState } from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Code2, Copy, Check } from "lucide-react";

const FULL_YAML = `name: autonomous-researcher
version: "1.0.0"
description: A research agent that summarizes documents and answers questions.

# ── Runtime Configuration ───────────────────────────────────
runtime:
  model: gemini-2.5-pro
  fallback_model: gemini-2.0-flash
  max_tokens: 8192
  timeout_seconds: 45
  temperature: 0.3

# ── Governance & Compliance ─────────────────────────────────
governance:
  policy_set: enterprise-strict
  pii_scan: true
  secret_scan: true
  human_approval_scopes:
    - write
    - admin
    - external_api
  allowed_tool_scopes:
    - read
    - summarize

# ── Tool Declarations ───────────────────────────────────────
tools:
  - name: web_search
    type: mcp
    server: brave-search
    scope: read
    rate_limit: 10/minute

  - name: read_file
    type: mcp
    server: filesystem
    scope: read
    allowed_paths:
      - /tmp/agent-workspace

  - name: summarize_doc
    type: builtin
    scope: summarize

# ── Budget Controls ─────────────────────────────────────────
budget:
  cost_ceiling_usd: 0.50
  token_budget: 50000
  alert_threshold_pct: 80

# ── Memory Configuration ────────────────────────────────────
memory:
  type: ephemeral          # ephemeral | persistent | vector
  max_turns: 50

# ── Publishing Metadata ─────────────────────────────────────
metadata:
  category: research
  tags: [research, summarization, documents]
  icon: 🔭
  builder: my-org
  license: MIT`;

export default function AgentYamlPage() {
  const [copied, setCopied] = useState(false);

  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Code2 className="w-3.5 h-3.5" />
          Agent Development
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">agent.yaml Reference</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Every agent in AgentVerse is defined by a portable declarative manifest — <InlineCode>agent.yaml</InlineCode>.
          Validated against JSON Schema draft-07 at publish time. All fields are documented below.
        </p>
      </div>

      {/* Full Example */}
      <DocH2>Complete Example</DocH2>
      <div className="relative">
        <button
          onClick={() => { navigator.clipboard.writeText(FULL_YAML); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
          className="absolute top-3 right-3 z-10 flex items-center gap-1.5 text-[11px] text-white/40 hover:text-white/70 transition-colors bg-[#070910] px-2 py-1 rounded"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied!" : "Copy"}
        </button>
        <CodeBlock language="yaml" code={FULL_YAML} filename="agent.yaml" />
      </div>

      {/* Field Reference */}
      <DocH2>Field Reference</DocH2>

      <DocH3>Top-Level Fields</DocH3>
      <div className="overflow-x-auto rounded-xl border border-white/10 mb-6">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Field</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Type</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Required</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Description</th>
            </tr>
          </thead>
          <tbody>
            {[
              { field: "name",        type: "string",  req: "✓",  desc: "Unique agent identifier. Kebab-case, max 64 chars." },
              { field: "version",     type: "semver",  req: "✓",  desc: "Semantic version (e.g. 1.0.0). Must increment on each publish." },
              { field: "description", type: "string",  req: "✓",  desc: "Human-readable description shown in AgentStore." },
              { field: "runtime",     type: "object",  req: "✓",  desc: "LLM model configuration and execution limits." },
              { field: "governance",  type: "object",  req: "–",  desc: "Policy set, PII scanning, and approval scopes." },
              { field: "tools",       type: "array",   req: "–",  desc: "List of MCP tools and builtin capabilities." },
              { field: "budget",      type: "object",  req: "–",  desc: "Cost ceiling and token budget controls." },
              { field: "memory",      type: "object",  req: "–",  desc: "Memory backend configuration." },
              { field: "metadata",    type: "object",  req: "–",  desc: "AgentStore publishing metadata (tags, category)." },
            ].map(row => (
              <tr key={row.field} className="border-b border-white/6 hover:bg-white/3 transition-colors">
                <td className="px-4 py-3"><code className="text-[#4EC9B0]">{row.field}</code></td>
                <td className="px-4 py-3"><span className="text-yellow-300/80">{row.type}</span></td>
                <td className="px-4 py-3 text-center">
                  <span className={row.req === "✓" ? "text-[#E5252A]" : "text-white/20"}>{row.req}</span>
                </td>
                <td className="px-4 py-3 text-white/55 font-sans">{row.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DocH3>runtime Object</DocH3>
      <div className="overflow-x-auto rounded-xl border border-white/10 mb-6">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Field</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Default</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Description</th>
            </tr>
          </thead>
          <tbody>
            {[
              { field: "model",            def: "gpt-4o",      desc: "Primary LLM. Supports Gemini, GPT-4o, Claude, Llama." },
              { field: "fallback_model",   def: "–",           desc: "Automatic fallback on primary model timeout/error." },
              { field: "max_tokens",       def: "4096",        desc: "Max completion tokens per inference call." },
              { field: "timeout_seconds",  def: "30",          desc: "Hard timeout for a single agent execution run." },
              { field: "temperature",      def: "0.7",         desc: "LLM sampling temperature (0.0 = deterministic)." },
            ].map(row => (
              <tr key={row.field} className="border-b border-white/6 hover:bg-white/3">
                <td className="px-4 py-3"><code className="text-[#4EC9B0]">{row.field}</code></td>
                <td className="px-4 py-3 font-mono text-white/40">{row.def}</td>
                <td className="px-4 py-3 text-white/55 font-sans">{row.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DocH3>governance Object</DocH3>
      <CodeBlock language="yaml" code={`governance:
  policy_set: enterprise-strict    # free | standard | enterprise-strict
  pii_scan: true                   # Auto-mask SSNs, credit cards, API keys
  secret_scan: true                # Block accidental secret leakage
  human_approval_scopes:           # Ops requiring human HITL approval
    - write
    - admin
    - external_api
  allowed_tool_scopes:             # Whitelist of allowed tool scope types
    - read
    - summarize`} />

      <DocH3>tools Array</DocH3>
      <CodeBlock language="yaml" code={`tools:
  - name: web_search              # Unique name within this agent
    type: mcp                     # mcp | builtin | custom
    server: brave-search          # MCP server identifier
    scope: read                   # read | write | admin
    rate_limit: 10/minute         # Optional: max calls per period

  - name: custom_api_call
    type: custom
    endpoint: https://api.myservice.com/v1/action
    auth:
      type: bearer
      token_env: MY_SERVICE_TOKEN  # Env var for secret injection`} />

      <Callout type="important">
        The <InlineCode>scope</InlineCode> field on each tool must be a subset of{" "}
        <InlineCode>governance.allowed_tool_scopes</InlineCode>. GovernOS Sentinel will reject any
        tool call that exceeds the declared scope at runtime.
      </Callout>

      <DocH2>Validation</DocH2>
      <CodeBlock language="bash" code={`# Validate locally with the CLI:
nuuvixx validate agent.yaml

# Validate via API:
curl -X POST http://localhost:8005/api/v1/cli/validate \\
  -H "Content-Type: application/json" \\
  -d '{"agent_yaml": "name: test\\nversion: 1.0.0"}'`} />
    </article>
  );
}
