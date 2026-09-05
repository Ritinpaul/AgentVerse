"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiClient, AgentListing, AgentRunRecord, TrustFactorBreakdown } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TrustScore } from "@/components/shared/TrustScore";
import { MetricCard } from "@/components/shared/MetricCard";
import { RunHistoryTable } from "@/components/agents/RunHistoryTable";
import { TrustBreakdown } from "@/components/agents/TrustBreakdown";
import { RuntimeConfigViewer } from "@/components/agents/RuntimeConfigViewer";
import { MicroVMTerminal } from "@/components/agents/MicroVMTerminal";
import { formatCurrency, formatNumber, formatLatency } from "@/lib/utils";
import Link from "next/link";
import {
  Bot,
  Activity,
  ShieldCheck,
  Cpu,
  Terminal,
  Play,
  RotateCcw,
  ArrowLeft,
  DollarSign,
  FileCode,
  Zap,
} from "lucide-react";

export default function AgentDetailPage() {
  const params = useParams();
  const slug = (params?.slug as string) || "nuuvixx-job-tracker";

  const [agent, setAgent] = useState<AgentListing | null>(null);
  const [runs, setRuns] = useState<AgentRunRecord[]>([]);
  const [factors, setFactors] = useState<TrustFactorBreakdown[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "trust" | "config" | "terminal">("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      apiClient.getAgent(slug),
      apiClient.getAgentRuns(slug),
      apiClient.getTrustBreakdown(slug),
    ]).then(([agentData, runData, factorData]) => {
      if (isMounted) {
        setAgent(agentData);
        setRuns(runData);
        setFactors(factorData);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [slug]);

  if (loading || !agent) {
    return (
      <div className="p-12 text-center text-text-muted font-mono text-xs animate-pulse">
        Loading agent telemetry and MicroVM state for {slug}...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between border-b border-surface-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/agents"
            className="p-1.5 rounded-lg bg-surface-100 hover:bg-surface-hover border border-surface-border text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold font-mono text-text-primary">{agent.name}</h1>
              <StatusBadge status={agent.status as any} />
              <span className="text-xs font-mono text-text-muted">v{agent.version || (agent as any).current_version || "1.0.0"}</span>
            </div>
            <p className="text-xs font-mono text-text-muted">{agent.slug}</p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2.5">
          <Link
            href={`/monitor?agent=${agent.slug}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-hover border border-surface-border text-xs font-mono font-medium text-text-primary transition-colors"
          >
            <Activity className="w-3.5 h-3.5 text-accent-cyan" />
            Live Traces
          </Link>

          <button
            onClick={() => setActiveTab("terminal")}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Execute in MicroVM
          </button>
        </div>
      </div>

      {/* Sub-Tabs Navigator */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-1 font-mono text-xs">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === "overview"
              ? "border-primary text-primary-light font-bold"
              : "border-transparent text-text-muted hover:text-text-primary"
          }`}
        >
          Overview & Runs
        </button>

        <button
          onClick={() => setActiveTab("trust")}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === "trust"
              ? "border-primary text-primary-light font-bold"
              : "border-transparent text-text-muted hover:text-text-primary"
          }`}
        >
          Trust & Compliance ({agent.trust_score})
        </button>

        <button
          onClick={() => setActiveTab("config")}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === "config"
              ? "border-primary text-primary-light font-bold"
              : "border-transparent text-text-muted hover:text-text-primary"
          }`}
        >
          Runtime & YAML
        </button>

        <button
          onClick={() => setActiveTab("terminal")}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === "terminal"
              ? "border-primary text-primary-light font-bold"
              : "border-transparent text-text-muted hover:text-text-primary"
          }`}
        >
          MicroVM Terminal
        </button>
      </div>

      {/* Tab 1: Overview & Runs */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Total Executions"
              value={formatNumber(agent.total_executions ?? 0)}
              subtitle="All time runs"
              icon={Bot}
            />

            <MetricCard
              title="P95 Latency"
              value={formatLatency(agent.metrics?.p95_latency_ms)}
              subtitle="Sub-100ms microVM coldstart"
              icon={Activity}
              iconColor="text-accent-cyan"
            />

            <MetricCard
              title="Daily Revenue"
              value={formatCurrency(agent.metrics?.daily_revenue_usd || 1240.5)}
              subtitle="80% builder share"
              icon={DollarSign}
              iconColor="text-emerald-400"
            />

            <MetricCard
              title="Trust Score"
              value={`${agent.trust_score} / 100`}
              subtitle="0 Critical Findings"
              icon={ShieldCheck}
              iconColor="text-accent-purple"
            />
          </div>

          <RunHistoryTable runs={runs} agentSlug={agent.slug} />
        </div>
      )}

      {/* Tab 2: Trust & Governance */}
      {activeTab === "trust" && (
        <TrustBreakdown score={agent.trust_score} factors={factors} />
      )}

      {/* Tab 3: Runtime Config & Manifest */}
      {activeTab === "config" && (
        <RuntimeConfigViewer agent={agent} />
      )}

      {/* Tab 4: MicroVM Terminal */}
      {activeTab === "terminal" && (
        <MicroVMTerminal agentSlug={agent.slug} agentName={agent.name} />
      )}
    </div>
  );
}
