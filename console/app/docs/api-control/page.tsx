"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, ApiPlayground, ApiEndpointCard } from "@/components/docs/DocComponents";
import { Server } from "lucide-react";

export default function ControlPlaneApiPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Server className="w-3.5 h-3.5" />API Reference
        </div>
        <h1 className="text-4xl font-black text-white mb-4">Control Plane API</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The AgentOS Control Plane manages MicroVM lifecycle, tool dispatch, agent execution scheduling,
          and state management. Running on <code className="text-[#4EC9B0]">localhost:8010</code>.
        </p>
      </div>

      <div className="flex items-center gap-3 p-4 rounded-xl bg-white/4 border border-white/10 mb-8">
        <Server className="w-5 h-5 text-[#E5252A] shrink-0" />
        <div>
          <div className="text-sm font-semibold text-white">Swagger UI — Control Plane API</div>
          <div className="text-xs text-white/50 font-sans">Full interactive endpoint documentation</div>
        </div>
        <a href="http://localhost:8010/docs" target="_blank" rel="noopener noreferrer"
          className="ml-auto px-4 py-2 rounded-lg bg-[#E5252A] text-white text-xs font-bold hover:bg-[#E5252A]/80 transition-colors shrink-0">
          Open Swagger →
        </a>
      </div>

      <DocH2>Execution Endpoints</DocH2>
      <div className="space-y-1 mb-6 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="POST" path="/api/v1/run"               desc="Launch a new agent execution (returns run_id)" />
        <ApiEndpointCard method="GET"  path="/api/v1/run/{run_id}"      desc="Get execution status and output" />
        <ApiEndpointCard method="POST" path="/api/v1/run/{run_id}/stop" desc="Gracefully terminate a running execution" />
        <ApiEndpointCard method="GET"  path="/api/v1/run/{run_id}/logs" desc="Stream execution logs in real-time (SSE)" />
      </div>

      <DocH3>Try It — Launch an Execution</DocH3>
      <ApiPlayground
        method="POST"
        endpoint="/api/v1/run"
        baseUrl="http://localhost:8010"
        defaultBody={JSON.stringify({
          agent_id: "nuuvixx/support-agent",
          prompt: "Summarize open tickets",
          max_turns: 10
        }, null, 2)}
      />

      <DocH2>Health & Metrics</DocH2>
      <ApiPlayground method="GET" endpoint="/health" baseUrl="http://localhost:8010" />
    </article>
  );
}
