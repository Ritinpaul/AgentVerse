"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiClient, AgentListing, TrustFactorBreakdown } from "@/lib/api";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import {
  ShoppingBag,
  ShieldCheck,
  Zap,
  Copy,
  Check,
  Terminal,
  Code2,
  Cpu,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

export default function StoreAgentDetailPage() {
  const params = useParams();
  const rawId = Array.isArray(params?.agentId) ? params.agentId[0] : params?.agentId;
  const agentSlug = rawId || "nuuvixx-job-tracker";

  const [agent, setAgent] = useState<AgentListing | null>(null);
  const [trustFactors, setTrustFactors] = useState<TrustFactorBreakdown[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState<"python" | "node" | "curl" | "a2a">("python");
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    apiClient.getAgent(agentSlug).then((a) => {
      if (a) setAgent(a);
    });
    apiClient.getTrustBreakdown(agentSlug).then(setTrustFactors);
  }, [agentSlug]);

  const handleCopySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  if (!agent) {
    return (
      <div className="space-y-6 font-mono text-center py-20">
        <StoreSubNav />
        <div className="p-12 text-[#57595B] text-xs uppercase tracking-widest">
          Loading agent listing details...
        </div>
      </div>
    );
  }

  const codeSnippets = {
    python: `from nuuvixx import AgentClient

client = AgentClient(api_key="nvx_live_981a8290f91b72a4498f3")
response = client.execute(
    agent="${agent.slug}",
    payload={"query": "Senior AI Architect", "max_results": 5}
)
print("Execution Result:", response.output)`,
    node: `import { AgentVerseClient } from "@agentverse/sdk";

const client = new AgentVerseClient({ apiKey: "nvx_live_981a8290f91b72a4498f3" });
const result = await client.runAgent("${agent.slug}", {
  query: "Senior AI Architect",
  max_results: 5
});
console.log("Result:", result.output);`,
    curl: `curl -X POST https://api.agentverse.io/v1/control/execute \\
  -H "Authorization: Bearer nvx_live_981a8290f91b72a4498f3" \\
  -H "Content-Type: application/json" \\
  -d '{"slug": "${agent.slug}", "payload": {"query": "Senior AI Architect"}}'`,
    a2a: `// Agent-to-Agent Autonomous Escrow Contract (x402 protocol)
await callerAgent.hireSubAgent({
  target_slug: "${agent.slug}",
  escrow_amount_usd: ${agent.price_per_execution},
  sla_max_latency_ms: 2500,
  provenance_verification: "REQUIRE_SHA256"
});`,
  };

  return (
    <div className="space-y-8 font-sans pb-16">
      <StoreSubNav />

      {/* Back Link */}
      <div>
        <Link
          href="/store"
          className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-[#57595B] hover:text-[#2E3033] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Store Marketplace</span>
        </Link>
      </div>

      {/* Hero Header */}
      <div
        className="rounded-3xl p-6 sm:p-8 border flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl"
        style={{ backgroundColor: "#2E3033", borderColor: "rgba(201,196,182,0.12)" }}
      >
        <div className="space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            <h1
              className="text-2xl sm:text-3xl font-extrabold uppercase"
              style={{ fontFamily: "'Anton', sans-serif", color: "#F2EFE7", letterSpacing: "-0.01em" }}
            >
              {agent.name}
            </h1>
            <span
              className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold"
              style={{ backgroundColor: "rgba(229,37,42,0.2)", color: "#E5252A", border: "1px solid rgba(229,37,42,0.4)" }}
            >
              v{agent.version}
            </span>
            <span
              className="text-xs px-2.5 py-0.5 rounded-full font-mono uppercase"
              style={{ backgroundColor: "rgba(242,239,231,0.06)", color: "#C9C4B6", border: "1px solid rgba(201,196,182,0.12)" }}
            >
              {agent.category}
            </span>
          </div>

          <p className="text-xs font-sans text-[#C9C4B6] leading-relaxed max-w-2xl">
            {agent.description}
          </p>

          <div className="flex items-center gap-3 text-xs font-mono text-[#57595B] pt-1">
            <span>Builder: <strong className="text-white font-semibold">{agent.builder || (agent as any).builder_id || "nuuvixx"}</strong></span>
            <span>·</span>
            <span>Executions: <strong className="text-[#38D9A9]">{(agent.total_executions ?? 0).toLocaleString()}</strong></span>
            <span>·</span>
            <span>Runtime: <strong className="text-[#38D9A9]">{agent.runtime?.model || "gemini-1.5-flash"}</strong></span>
          </div>
        </div>

        {/* Pricing / Install Action Card */}
        <div
          className="p-5 rounded-2xl border text-center space-y-3 shrink-0 min-w-[220px]"
          style={{ backgroundColor: "#161822", borderColor: "rgba(201,196,182,0.12)" }}
        >
          <div className="text-[10px] font-mono text-[#57595B] uppercase font-bold tracking-widest">
            Price per Execution
          </div>
          <div className="text-3xl font-extrabold font-mono text-[#38D9A9]">
            {formatCurrency(agent.price_per_execution)}
          </div>
          <div className="text-[10px] font-mono text-[#C9C4B6]">80% builder revenue share</div>

          <button
            onClick={() => setInstalled(true)}
            className="w-full py-2.5 px-4 rounded-xl bg-[#E5252A] hover:bg-[#D01E23] text-white font-mono font-bold text-xs uppercase tracking-wider transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
          >
            {installed ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-[#38D9A9]" />
                <span>Installed in Cluster</span>
              </>
            ) : (
              <>
                <ShoppingBag className="w-4 h-4" />
                <span>Hire / Install Agent</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Split: 5-Factor Trust Scorecard vs Code Snippet Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs">
        {/* Left Col: 5-Factor Trust Scorecard */}
        <div
          className="rounded-3xl p-6 border space-y-4 shadow-xl"
          style={{ backgroundColor: "#2E3033", borderColor: "rgba(201,196,182,0.12)" }}
        >
          <div className="flex items-center justify-between border-b border-[rgba(201,196,182,0.1)] pb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#34D399]" />
              <h3 className="font-mono font-bold uppercase tracking-wider text-[#F2EFE7]">
                5-Factor Computed Trust Score
              </h3>
            </div>
            <span className="text-base font-mono font-extrabold text-[#34D399]">{agent.trust_score}/100</span>
          </div>

          <div className="space-y-3">
            {trustFactors.map((tf, i) => (
              <div
                key={i}
                className="p-3.5 rounded-2xl border space-y-1.5"
                style={{ backgroundColor: "rgba(242,239,231,0.04)", borderColor: "rgba(201,196,182,0.1)" }}
              >
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-[#F2EFE7]">{tf.dimension}</span>
                  <span className="text-[#34D399] font-bold">
                    {tf.score} / {tf.max_score} pts ({tf.weight_pct}% weight)
                  </span>
                </div>
                <p className="text-xs font-sans text-[#C9C4B6] leading-relaxed">
                  {tf.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Right Col: Integration Code Snippets */}
        <div
          className="rounded-3xl p-6 border space-y-4 shadow-xl"
          style={{ backgroundColor: "#2E3033", borderColor: "rgba(201,196,182,0.12)" }}
        >
          <div className="flex items-center justify-between border-b border-[rgba(201,196,182,0.1)] pb-4">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-[#E5252A]" />
              <h3 className="font-mono font-bold uppercase tracking-wider text-[#F2EFE7]">
                Integration Code Snippet
              </h3>
            </div>

            {/* Language Switcher */}
            <div className="flex items-center rounded-xl p-1 gap-1 border border-[rgba(201,196,182,0.1)]" style={{ backgroundColor: "#161822" }}>
              {(["python", "node", "curl", "a2a"] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setSelectedLanguage(lang)}
                  className="px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold uppercase transition-all cursor-pointer"
                  style={{
                    backgroundColor: selectedLanguage === lang ? "#E5252A" : "transparent",
                    color: selectedLanguage === lang ? "#FFFFFF" : "#C9C4B6",
                  }}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          <div className="relative">
            <pre
              className="p-4 rounded-2xl text-xs font-mono text-[#38D9A9] overflow-x-auto leading-relaxed border"
              style={{ backgroundColor: "#161822", borderColor: "rgba(201,196,182,0.1)" }}
            >
              {codeSnippets[selectedLanguage]}
            </pre>

            <button
              onClick={() => handleCopySnippet(codeSnippets[selectedLanguage])}
              className="absolute top-3 right-3 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all flex items-center gap-1.5 cursor-pointer"
              style={{ backgroundColor: "#2E3033", borderColor: "rgba(201,196,182,0.2)", color: "#C9C4B6" }}
              title="Copy code snippet"
            >
              {copiedSnippet ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[#34D399]" />
                  <span className="text-[10px] text-[#34D399] font-bold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
