"use client";

import React from "react";
import { DollarSign, Zap, TrendingUp, Layers, Cpu, CheckCircle2 } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import type { ExecutionTrace } from "@/lib/api";

interface CostBreakdownProps {
  trace: ExecutionTrace | null;
}

export function CostBreakdown({ trace }: CostBreakdownProps) {
  if (!trace) {
    return (
      <div className="p-8 text-center text-text-muted text-xs font-mono">
        Select a trace to inspect token and cost attribution.
      </div>
    );
  }

  const promptCost = (trace.prompt_tokens / 1000) * 0.00125;
  const completionCost = (trace.completion_tokens / 1000) * 0.005;
  const microVmOverhead = 0.0002;
  const totalCost = trace.total_cost_usd;

  const promptPercent = totalCost > 0 ? (promptCost / totalCost) * 100 : 60;
  const completionPercent = totalCost > 0 ? (completionCost / totalCost) * 100 : 35;
  const overheadPercent = Math.max(100 - promptPercent - completionPercent, 5);

  return (
    <div className="space-y-4 font-mono">
      {/* Total Cost Hero Card */}
      <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-2">
        <div className="flex items-center justify-between text-text-muted text-xs">
          <span>Execution Cost Attribution</span>
          <DollarSign className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold text-emerald-400">
          {formatCurrency(totalCost)}
        </div>
        <div className="text-[10px] text-text-muted">
          Model: <span className="text-text-primary font-bold">{trace.model}</span> ({trace.total_tokens.toLocaleString()} total tokens)
        </div>
      </div>

      {/* Cost Distribution Progress Bar */}
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between text-[11px] text-text-secondary">
          <span>Token Cost Attribution Split</span>
          <span className="text-text-muted">100% Billable</span>
        </div>
        <div className="h-3 rounded-full bg-surface-200 overflow-hidden flex">
          <div
            style={{ width: `${Math.max(promptPercent, 10)}%` }}
            className="bg-blue-500 h-full border-r border-[#0B0D14]"
            title={`Prompt tokens: ${promptCost.toFixed(5)}`}
          />
          <div
            style={{ width: `${Math.max(completionPercent, 10)}%` }}
            className="bg-emerald-400 h-full border-r border-[#0B0D14]"
            title={`Completion tokens: ${completionCost.toFixed(5)}`}
          />
          <div
            style={{ width: `${overheadPercent}%` }}
            className="bg-violet-400 h-full"
            title="MicroVM & Governance Overhead"
          />
        </div>

        <div className="grid grid-cols-3 gap-2 text-[10px] pt-1">
          <div className="flex items-center gap-1.5 text-blue-400">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Prompt: {trace.prompt_tokens} tok</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Output: {trace.completion_tokens} tok</span>
          </div>
          <div className="flex items-center gap-1.5 text-violet-400">
            <span className="w-2 h-2 rounded-full bg-violet-400" />
            <span>MicroVM Gate</span>
          </div>
        </div>
      </div>

      {/* Line Item Breakdown */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-2 text-xs">
        <div className="text-[10px] uppercase font-bold text-text-muted tracking-wider">
          Line Item Costs
        </div>

        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between text-text-secondary">
            <span>Input Tokens ({trace.prompt_tokens.toLocaleString()})</span>
            <span className="text-text-primary">{formatCurrency(promptCost)}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Output Generation ({trace.completion_tokens.toLocaleString()})</span>
            <span className="text-text-primary">{formatCurrency(completionCost)}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Firecracker Sandbox Isolation</span>
            <span className="text-text-primary">{formatCurrency(microVmOverhead)}</span>
          </div>
          <div className="border-t border-surface-border pt-1.5 flex justify-between font-bold text-emerald-400 text-xs">
            <span>Net Run Cost</span>
            <span>{formatCurrency(totalCost)}</span>
          </div>
        </div>
      </div>

      {/* Scaling Projection */}
      <div className="p-3 rounded-xl bg-surface-50 border border-surface-border space-y-2 text-xs">
        <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-text-muted tracking-wider">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>Production Fleet Projections</span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border space-y-0.5">
            <div className="text-text-muted">1,000 runs</div>
            <div className="font-bold text-text-primary">${(totalCost * 1000).toFixed(2)}</div>
          </div>
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border space-y-0.5">
            <div className="text-text-muted">10,000 runs</div>
            <div className="font-bold text-text-primary">${(totalCost * 10000).toFixed(2)}</div>
          </div>
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border space-y-0.5">
            <div className="text-text-muted">100k runs</div>
            <div className="font-bold text-emerald-400">${(totalCost * 100000).toFixed(2)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
