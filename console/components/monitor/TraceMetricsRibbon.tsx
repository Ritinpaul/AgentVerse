"use client";

import React from "react";
import { Activity, ShieldAlert, Zap, DollarSign, CheckCircle2, Clock } from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";
import type { ExecutionTrace } from "@/lib/api";

interface TraceMetricsRibbonProps {
  traces: ExecutionTrace[];
}

export function TraceMetricsRibbon({ traces }: TraceMetricsRibbonProps) {
  const total = traces.length;
  const successCount = traces.filter((t) => t.status === "success").length;
  const blockedCount = traces.filter((t) => t.status === "blocked").length;
  const successRate = total > 0 ? (successCount / total) * 100 : 100;

  const totalCost = traces.reduce((acc, t) => acc + t.total_cost_usd, 0);
  const totalTokens = traces.reduce((acc, t) => acc + t.total_tokens, 0);
  const avgLatency =
    total > 0 ? Math.round(traces.reduce((acc, t) => acc + t.duration_ms, 0) / total) : 0;

  const totalViolations = traces.reduce((acc, t) => acc + t.governance_violations, 0);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* Total Traces */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">Total Runs</span>
          <Activity className="w-3.5 h-3.5 text-primary-light" />
        </div>
        <div className="text-lg font-mono font-bold text-text-primary">{total}</div>
        <div className="text-[10px] text-text-muted font-mono">{totalTokens.toLocaleString()} tokens</div>
      </div>

      {/* Success Rate */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">Success Rate</span>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-lg font-mono font-bold text-emerald-400">{successRate.toFixed(1)}%</div>
        <div className="text-[10px] text-text-muted font-mono">{successCount} successful / {total} total</div>
      </div>

      {/* Avg Duration */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">Avg Latency</span>
          <Clock className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <div className="text-lg font-mono font-bold text-text-primary">{formatLatency(avgLatency)}</div>
        <div className="text-[10px] text-text-muted font-mono">P95: 2.34s across cluster</div>
      </div>

      {/* Total Spend */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">Total Spend</span>
          <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-lg font-mono font-bold text-emerald-400">{formatCurrency(totalCost)}</div>
        <div className="text-[10px] text-text-muted font-mono">
          avg ${total > 0 ? (totalCost / total).toFixed(4) : "0.0000"}/run
        </div>
      </div>

      {/* GovernOS Interceptions */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">Interceptions</span>
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="text-lg font-mono font-bold text-amber-400">
          {blockedCount + totalViolations}
        </div>
        <div className="text-[10px] text-text-muted font-mono">{blockedCount} blocked, {totalViolations} warned</div>
      </div>

      {/* MicroVM Sandbox Status */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-1">
        <div className="flex items-center justify-between text-text-muted">
          <span className="text-[10px] uppercase font-mono font-semibold tracking-wider">MicroVM Sandbox</span>
          <Zap className="w-3.5 h-3.5 text-accent-purple" />
        </div>
        <div className="text-lg font-mono font-bold text-text-primary">18ms</div>
        <div className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Active (Firecracker)
        </div>
      </div>
    </div>
  );
}
