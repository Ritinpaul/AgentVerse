"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import { useStore } from "@/hooks/useStore";
import {
  Layers,
  Handshake,
  CheckCircle2,
  DollarSign,
  Play,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

export default function StoreCompositionsPage() {
  const { compositions } = useStore();
  const [runningId, setRunningId] = useState<string | null>(null);

  const handleRunPipeline = (id: string) => {
    setRunningId(id);
    setTimeout(() => {
      setRunningId(null);
      alert("Multi-agent composition execution initiated across MicroVM clusters!");
    }, 900);
  };

  return (
    <div className="space-y-5 font-mono">
      <StoreSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              Multi-Agent Compositions & Chains
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              Automated Revenue Splitting
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            End-to-end multi-agent pipelines where cooperating agents execute task workflows and automatically split micropayments via x402 smart contracts.
          </p>
        </div>
      </div>

      {/* Compositions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {compositions.map((comp) => (
          <div
            key={comp.id}
            className="glass-card rounded-xl p-5 border border-surface-border space-y-4 flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-text-primary">{comp.title}</h3>
                <span className="text-xs font-bold text-emerald-400">
                  {formatCurrency(comp.price_per_pipeline_run)} / run
                </span>
              </div>

              <p className="text-xs text-text-muted font-sans leading-relaxed">
                {comp.description}
              </p>

              {/* Sub-Agent Revenue Split Cards */}
              <div className="space-y-1.5 pt-1">
                <div className="text-[10px] text-text-muted uppercase font-bold">
                  Cooperating Agents & Revenue Share
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  {comp.agents_involved.map((ag) => (
                    <div
                      key={ag.slug}
                      className="p-2.5 rounded-lg bg-surface-50 border border-surface-border space-y-0.5"
                    >
                      <div className="text-text-primary font-bold truncate">{ag.name}</div>
                      <div className="text-[10px] text-emerald-400 font-bold">
                        {ag.share_pct}% revenue share
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Card Footer */}
            <div className="pt-3 border-t border-surface-border/60 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-[10px] text-text-muted">
                <span>Trust: <strong className="text-emerald-400">{comp.trust_score}/100</strong></span>
                <span>·</span>
                <span>{comp.total_executions.toLocaleString()} executions</span>
              </div>

              <button
                onClick={() => handleRunPipeline(comp.id)}
                disabled={runningId === comp.id}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1 transition-all shadow-sm"
              >
                {runningId === comp.id ? (
                  <>
                    <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                    Dispatching...
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 fill-current" />
                    Hire Pipeline
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
