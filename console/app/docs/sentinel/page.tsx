"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, ApiPlayground, ApiEndpointCard } from "@/components/docs/DocComponents";
import { Shield } from "lucide-react";

export default function SentinelPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Shield className="w-3.5 h-3.5" />
          Security & Governance
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">GovernOS Sentinel</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Sentinel is an in-runtime security kernel that executes in the hotpath before every tool invocation
          and model generation dispatch. It enforces OWASP ASI-01 through ASI-06, SHA-256 Merkle audit logging,
          PII masking, and budget circuit-breaking.
        </p>
      </div>

      {/* OWASP Coverage Matrix */}
      <DocH2>OWASP ASI Coverage Matrix</DocH2>
      <div className="space-y-3 mb-8">
        {[
          {
            id: "ASI-01",
            name: "Prompt Injection & Jailbreak Shield",
            desc: "Scans incoming prompt buffers for delimiter collisions, role override tokens (IGNORE PREVIOUS INSTRUCTIONS), and indirect injection from external data sources.",
            severity: "Critical",
            status: "✓ Enforced"
          },
          {
            id: "ASI-02",
            name: "Tool Scope Authorization",
            desc: "Evaluates every MCP tool call against the agent manifest's allowed_tool_scopes allowlist. Rejects unauthorized write/admin calls with 403 before they reach the MCP server.",
            severity: "Critical",
            status: "✓ Enforced"
          },
          {
            id: "ASI-03",
            name: "PII & Secret Masking",
            desc: "Automatic regex-based scrubbing for OpenAI API keys, AWS tokens, SSNs, credit card numbers, phone numbers, and email addresses in both prompt input and model output.",
            severity: "High",
            status: "✓ Enforced"
          },
          {
            id: "ASI-04",
            name: "Runaway Cost Circuit Breaker",
            desc: "Halts recursive agent loops when cumulative execution cost surpasses the manifest budget.cost_ceiling_usd. Prevents runaway spending from agent feedback loops.",
            severity: "High",
            status: "✓ Enforced"
          },
          {
            id: "ASI-05",
            name: "Supply Chain Validation",
            desc: "Verifies SHA-256 checksums of all referenced MCP tool manifests against the AgentStore trusted registry before execution.",
            severity: "High",
            status: "✓ Enforced"
          },
          {
            id: "ASI-06",
            name: "Data Exfiltration Guard",
            desc: "Monitors all network egress from agent MicroVMs. Blocks calls to non-whitelisted domains defined in the agent.yaml network policy.",
            severity: "Medium",
            status: "✓ Enforced"
          },
        ].map(item => (
          <div key={item.id} className="p-4 rounded-xl bg-white/4 border border-white/10 hover:border-white/20 transition-colors">
            <div className="flex items-start gap-3">
              <span className="text-xs font-black text-[#E5252A] font-mono shrink-0 mt-0.5 w-14">{item.id}</span>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1.5">
                  <span className="text-sm font-bold text-white">{item.name}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold ml-auto">{item.status}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    item.severity === "Critical" ? "bg-[#E5252A]/15 text-[#E5252A]" :
                    item.severity === "High" ? "bg-orange-500/15 text-orange-400" : "bg-yellow-500/15 text-yellow-400"
                  }`}>{item.severity}</span>
                </div>
                <p className="text-xs text-white/55 font-sans leading-relaxed">{item.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* SHA-256 Audit Ledger */}
      <DocH2>SHA-256 Merkle Audit Ledger</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Every agent decision, tool call, and model response is hashed and chained into an immutable
        Merkle tree. Tamper-evident audit trails for compliance, GDPR Right-to-Erasure, and forensic investigation.
      </p>
      <CodeBlock language="json" code={`{
  "ledger_entry": {
    "id": "0x4a7b9c2e...",
    "timestamp": "2026-08-30T21:00:00Z",
    "agent_id": "nuuvixx/support-agent",
    "event_type": "tool_call",
    "tool": "zendesk:get-ticket",
    "decision": "APPROVED",
    "policy_checks": ["ASI-01", "ASI-02", "ASI-03"],
    "sha256_hash": "a8f2c1d9e4b5...",
    "prev_hash": "7c3e9f1a2b4d...",
    "merkle_root": "1d4a8c2b7f9e..."
  }
}`} />

      <Callout type="note">
        The SHA-256 decision ledger entries are queryable via the <code>/api/v1/audit/decisions</code> endpoint
        on GovernOS API (port 8025). Each entry links to the previous hash forming an immutable chain.
      </Callout>

      {/* Live API Section */}
      <DocH2>Live API — GovernOS Sentinel</DocH2>
      <p className="text-white/60 text-sm mb-4 font-sans">
        Test the Sentinel policy evaluation endpoint directly (requires GovernOS running on port 8025):
      </p>

      <DocH3>Evaluate a Policy</DocH3>
      <ApiPlayground
        method="POST"
        endpoint="/api/v1/sentinel/evaluate"
        baseUrl="http://localhost:8025"
        defaultBody={JSON.stringify({
          agent_id: "nuuvixx/support-agent",
          tool_call: {
            name: "zendesk:get-ticket",
            scope: "read",
            args: { ticket_id: "12345" }
          }
        }, null, 2)}
      />

      <DocH3>Get OWASP Coverage Report</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/governance/owasp-coverage"
        baseUrl="http://localhost:8025"
      />

      {/* Policy Set Reference */}
      <DocH2>Policy Sets</DocH2>
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 uppercase font-bold tracking-wider">Policy Set</th>
              <th className="text-left px-4 py-3 text-white/50 uppercase font-bold tracking-wider">ASI Checks</th>
              <th className="text-left px-4 py-3 text-white/50 uppercase font-bold tracking-wider">HITL Required</th>
              <th className="text-left px-4 py-3 text-white/50 uppercase font-bold tracking-wider">Use Case</th>
            </tr>
          </thead>
          <tbody>
            {[
              { name: "free",              asi: "ASI-01, 03",          hitl: "None",           use: "Personal projects, prototyping" },
              { name: "standard",          asi: "ASI-01 through 04",   hitl: "Admin scope",    use: "Production business agents" },
              { name: "enterprise-strict", asi: "ASI-01 through 06",   hitl: "Write + Admin",  use: "Regulated industries, financial, healthcare" },
            ].map(row => (
              <tr key={row.name} className="border-b border-white/6 hover:bg-white/3">
                <td className="px-4 py-3"><code className="text-[#4EC9B0]">{row.name}</code></td>
                <td className="px-4 py-3 font-sans text-white/55">{row.asi}</td>
                <td className="px-4 py-3 font-sans text-white/55">{row.hitl}</td>
                <td className="px-4 py-3 font-sans text-white/55">{row.use}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
