"use client";

import React from "react";
import Link from "next/link";
import {
  Search,
  ShieldAlert,
  CheckCircle2,
  Clock,
  ExternalLink,
  Cpu,
  ShieldCheck,
  Zap,
  ArrowRight,
  Terminal,
  Activity,
} from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";
import type { ExecutionTrace } from "@/lib/api";

interface TraceListProps {
  traces: ExecutionTrace[];
  selectedTrace: ExecutionTrace | null;
  onSelectTrace: (trace: ExecutionTrace) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
}

const TRIGGER_LABELS: Record<string, { label: string; color: string }> = {
  api: { label: "API", color: "bg-blue-500/20 text-blue-400 border border-blue-500/30" },
  a2a_contract: { label: "A2A", color: "bg-violet-500/20 text-violet-400 border border-violet-500/30" },
  cron: { label: "CRON", color: "bg-amber-500/20 text-amber-400 border border-amber-500/30" },
  manual: { label: "MANUAL", color: "bg-[#38D9A9]/20 text-[#38D9A9] border border-[#38D9A9]/30" },
};

export function TraceList({
  traces,
  onSelectTrace,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
}: TraceListProps) {
  const filtered = traces.filter((t) => {
    const matchesStatus =
      statusFilter === "all" ||
      t.status.toLowerCase() === statusFilter.toLowerCase();

    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      t.id.toLowerCase().includes(q) ||
      t.agent_name.toLowerCase().includes(q) ||
      t.agent_slug.toLowerCase().includes(q) ||
      t.session_id.toLowerCase().includes(q) ||
      t.model.toLowerCase().includes(q);

    return matchesStatus && matchesSearch;
  });

  return (
    <div className="flex flex-col h-full space-y-4 font-sans w-full">
      {/* Search & Status Filter Ribbon */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shrink-0 bg-[#12131A] p-4 rounded-2xl border border-[#22222E]">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-neutral-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search run ID, agent name, session, model..."
            className="w-full bg-[#14151D] border border-[#242532] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-[#38D9A9] font-mono"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {["all", "success", "blocked", "running", "failed"].map((status) => {
            const count =
              status === "all"
                ? traces.length
                : traces.filter((t) => t.status === status).length;

            const isActive = statusFilter === status;

            return (
              <button
                key={status}
                onClick={() => onStatusFilterChange(status)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono capitalize whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-[#E5252A] text-white font-bold border border-[#F5353A] shadow-md shadow-[#E5252A]/20"
                    : "text-neutral-400 hover:text-white bg-[#14151D] border border-[#20212C] hover:bg-[#1C1D28]"
                }`}
              >
                {status} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Spacious Full-Width Grid of Execution Cards */}
      <div className="flex-1 overflow-y-auto min-h-0 pr-1">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-neutral-400 text-xs font-mono bg-[#12131A] rounded-2xl border border-[#22222E]">
            <Activity className="w-10 h-10 text-neutral-600 mx-auto mb-2" />
            No agent execution traces match the selected filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filtered.map((trace) => {
              const triggerInfo =
                trace.trigger && TRIGGER_LABELS[trace.trigger]
                  ? TRIGGER_LABELS[trace.trigger]
                  : {
                      label: trace.trigger || "manual",
                      color: "bg-[#181924] text-neutral-400 border border-[#242532]",
                    };

              return (
                <div
                  key={trace.id}
                  onClick={() => onSelectTrace(trace)}
                  className="p-5 rounded-2xl bg-[#12131A] border border-[#22222E] hover:border-[#38D9A9]/50 transition-all cursor-pointer shadow-lg space-y-4 group"
                >
                  {/* Card Header: Agent Name, Run ID, Status, Trigger */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-[#38D9A9]" />
                        <h3 className="font-bold text-white text-base font-sans group-hover:text-[#38D9A9] transition-colors">
                          {trace.agent_name}
                        </h3>
                        <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-[#1C1D28] text-neutral-300 border border-[#28293A]">
                          {trace.id}
                        </span>
                      </div>
                      <p className="text-xs text-neutral-400 font-mono mt-1">
                        slug: <span className="text-neutral-300">{trace.agent_slug}</span>
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${triggerInfo.color}`}
                      >
                        {triggerInfo.label}
                      </span>

                      <span
                        className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1 border ${
                          trace.status === "success"
                            ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                            : trace.status === "blocked"
                            ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                            : trace.status === "running"
                            ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/30 animate-pulse"
                            : "bg-red-500/15 text-red-400 border-red-500/30"
                        }`}
                      >
                        {trace.status === "success" && <CheckCircle2 className="w-3 h-3" />}
                        {trace.status === "blocked" && <ShieldAlert className="w-3 h-3" />}
                        {trace.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Metadata Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-xl bg-[#090A0E] border border-[#1C1D26] text-xs font-mono">
                    <div>
                      <div className="text-[10px] text-neutral-500 uppercase">Session ID</div>
                      <div className="text-neutral-200 font-semibold truncate mt-0.5">{trace.session_id}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-neutral-500 uppercase">Sandbox VM</div>
                      <div className="text-neutral-200 font-semibold truncate mt-0.5">{trace.vm_id}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-neutral-500 uppercase">LLM Model</div>
                      <div className="text-[#38D9A9] font-semibold truncate mt-0.5">{trace.model}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-neutral-500 uppercase">GovernOS Score</div>
                      <div className="text-violet-400 font-semibold truncate mt-0.5">{trace.governance_score}/100</div>
                    </div>
                  </div>

                  {/* Execution Event Summary */}
                  {trace.events && trace.events.length > 0 && (
                    <div className="p-3 rounded-xl bg-[#14151E] border border-[#20212C] text-xs font-sans space-y-1">
                      <div className="text-[10px] font-mono text-neutral-400 uppercase font-semibold flex items-center justify-between">
                        <span>Latest Causal Step</span>
                        <span className="text-[#38D9A9] font-normal">{trace.events.length} Causal Steps</span>
                      </div>
                      <div className="text-white font-medium truncate">
                        {trace.events[trace.events.length - 1]?.label || "Execution Completed"}
                      </div>
                    </div>
                  )}

                  {/* Card Footer: Metrics & Full Trace CTA */}
                  <div className="flex items-center justify-between pt-3 border-t border-[#1E1E28] font-mono text-xs">
                    <div className="flex items-center gap-4 text-neutral-400">
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-neutral-400" />
                        <strong className="text-white">{formatLatency(trace.duration_ms)}</strong>
                      </span>
                      <span>
                        <strong className="text-white">{trace.total_tokens.toLocaleString()}</strong> tok
                      </span>
                      <span className="text-emerald-400 font-bold">
                        {formatCurrency(trace.total_cost_usd)}
                      </span>
                    </div>

                    <Link
                      href={`/monitor/trace/${trace.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="px-3.5 py-1.5 rounded-xl bg-[#E5252A]/15 hover:bg-[#E5252A] text-white border border-[#E5252A]/40 font-semibold flex items-center gap-1.5 transition-all text-xs shadow-xs"
                    >
                      <span>View Full Trace</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
