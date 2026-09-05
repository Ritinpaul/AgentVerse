"use client";

import React from "react";
import { cn } from "@/lib/utils";

/**
 * Compact agent inspector — small labels, tight mono rows,
 * exactly like a professional IDE's PROPERTIES / INSPECTOR panel.
 */

interface AgentInspectorProps {
  name: string;
  agentId: string;
  status: "READY" | "RUNNING" | "ERROR" | "STOPPED";
  model: string;
  fallbackModel?: string;
  tools: string[];
  trustLevel: string;
  trustScore: number;
  runtime: string;
  timeout: string;
  memory: string;
  environment: string;
  estimatedCost?: string;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="px-3 py-[5px] flex items-center justify-between gap-3 border-t border-[#1A1A22] first:border-t-0">
      <span className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#565666] font-mono shrink-0">{label}</span>
      <span className="text-[10px] text-[#C7C7D1] font-mono text-right truncate">{children}</span>
    </div>
  );
}

const statusStyle: Record<AgentInspectorProps["status"], string> = {
  READY: "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/40",
  RUNNING: "bg-[#61AFEF]/10 text-[#61AFEF] border-[#61AFEF]/40",
  ERROR: "bg-[#E5252A]/10 text-[#E5252A] border-[#E5252A]/40",
  STOPPED: "bg-neutral-500/10 text-neutral-400 border-neutral-500/40",
};

export function AgentInspector({
  name,
  agentId,
  status,
  model,
  fallbackModel,
  tools,
  trustLevel,
  trustScore,
  runtime,
  timeout,
  memory,
  environment,
  estimatedCost,
}: AgentInspectorProps) {
  return (
    <div className="flex flex-col h-full text-left">
      {/* Header */}
      <div className="px-3 py-2 flex items-center justify-between border-b border-[#1A1A22]">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#6E6E7E] font-mono">Inspector</span>
        <span
          className={cn(
            "px-1.5 py-0.5 rounded-[3px] text-[8px] font-bold tracking-wider font-mono border",
            statusStyle[status]
          )}
        >
          {status}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar">
        <div className="px-3 pt-2.5 text-[11px] font-bold text-white font-sans flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#E5252A]" />
          {name}
        </div>

        <div className="mt-2 pb-2">
          <Row label="ID">{agentId}</Row>
          <Row label="Model">{model}</Row>
          {fallbackModel && <Row label="Fallback">{fallbackModel}</Row>}
          <Row label="Env">{environment}</Row>
          <Row label="Runtime">{runtime}</Row>
          <Row label="Timeout">{timeout}</Row>
          <Row label="Memory">{memory}</Row>
          {estimatedCost && <Row label="Est. Cost">{estimatedCost}</Row>}
        </div>

        {/* Tools */}
        <div className="px-3 pb-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[#565666] font-mono">Tools</div>
        <div className="px-3 pb-2 space-y-[3px]">
          {tools.map((t) => (
            <div key={t} className="flex items-center gap-2 text-[10px] text-[#C7C7D1] font-mono">
              <span className="w-1 h-1 rounded-full bg-[#10B981]" />
              {t}
            </div>
          ))}
        </div>

        {/* Governance */}
        <div className="px-3 pb-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[#565666] font-mono">
          Governance
        </div>
        <div className="px-3 pb-3 space-y-[3px] text-[10px] font-mono">
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">Trust Level</span>
            <span className="text-[#E5C07B] font-semibold">{trustLevel}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">Trust Score</span>
            <span className={cn("font-semibold", trustScore >= 90 ? "text-[#10B981]" : trustScore >= 75 ? "text-[#61AFEF]" : "text-[#E5C07B]")}>
              {trustScore.toFixed(1)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">ASI Scan</span>
            <span className="text-[#10B981]">PASSED</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">Policy Set</span>
            <span className="text-[#C7C7D1]">strict-finance-v2</span>
          </div>
        </div>

        {/* Memory */}
        <div className="px-3 pb-1 text-[9px] font-bold uppercase tracking-[0.12em] text-[#565666] font-mono">Memory</div>
        <div className="px-3 pb-3 text-[10px] font-mono space-y-[3px]">
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">Backend</span>
            <span className="text-[#C7C7D1]">redis</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">TTL</span>
            <span className="text-[#C7C7D1]">24h</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#6E6E7E]">Persistence</span>
            <span className="text-[#10B981]">enabled</span>
          </div>
        </div>
      </div>
    </div>
  );
}