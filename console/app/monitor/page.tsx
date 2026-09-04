"use client";

import React, { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTrace } from "@/hooks/useTrace";
import { TraceMetricsRibbon } from "@/components/monitor/TraceMetricsRibbon";
import { TraceList } from "@/components/monitor/TraceList";
import {
  Activity,
  RefreshCw,
  Search,
  SlidersHorizontal,
  ChevronUp,
  ChevronDown,
} from "lucide-react";

export default function MonitorPage() {
  const router = useRouter();
  const {
    traces,
    selectedTrace,
    setSelectedTrace,
    isLiveStreaming,
    setIsLiveStreaming,
    fetchTraces,
  } = useTrace();

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);
  const [showMetricsRibbon, setShowMetricsRibbon] = useState(true);

  const handleManualRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchTraces();
    setTimeout(() => setRefreshing(false), 500);
  }, [fetchTraces]);

  return (
    <div className="flex flex-col h-full bg-[#0A0A0E] text-white font-sans overflow-hidden space-y-4">
      {/* ── Top Header Navigation Bar ─────────────────────────────────────────────── */}
      <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shrink-0 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#38D9A9]/15 border border-[#38D9A9]/30 text-[#38D9A9] flex items-center justify-center shrink-0">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold font-sans tracking-wide text-white">
                Observability Studio & Agent Traces
              </h1>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30 font-mono font-semibold flex items-center gap-1.5 uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse" />
                Live Stream Active
              </span>
            </div>
            <p className="text-xs text-neutral-400 font-sans mt-0.5">
              Real-time telemetry, MicroVM sandbox execution traces, and GovernOS Sentinel enforcements.
            </p>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => setShowMetricsRibbon((prev) => !prev)}
            className="px-3.5 py-2 rounded-xl bg-[#161720] hover:bg-[#20212C] border border-[#272836] text-neutral-300 text-xs font-mono transition-all flex items-center gap-1.5"
            title="Toggle Metrics Summary Bar"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#38D9A9]" />
            <span>{showMetricsRibbon ? "Hide Stats" : "Show Stats"}</span>
            {showMetricsRibbon ? <ChevronUp className="w-3 h-3 text-neutral-500" /> : <ChevronDown className="w-3 h-3 text-neutral-500" />}
          </button>

          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="px-3.5 py-2 rounded-xl bg-[#161720] hover:bg-[#20212C] border border-[#272836] text-neutral-300 hover:text-white text-xs font-mono transition-colors flex items-center gap-1.5"
            title="Sync Traces"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-[#38D9A9]" : ""}`} />
            <span>Sync</span>
          </button>

          <button
            onClick={() => setIsLiveStreaming(!isLiveStreaming)}
            className={`px-3.5 py-2 rounded-xl border text-xs font-mono font-semibold transition-colors flex items-center gap-1.5 ${
              isLiveStreaming
                ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                : "bg-[#161720] text-neutral-400 border-[#272836]"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLiveStreaming ? "bg-[#38D9A9] animate-pulse" : "bg-neutral-500"
              }`}
            />
            {isLiveStreaming ? "Live: ON" : "Live: PAUSED"}
          </button>
        </div>
      </div>

      {/* ── Top Metrics Ribbon (Collapsible) ────────────────────────────────────── */}
      {showMetricsRibbon && (
        <div className="shrink-0">
          <TraceMetricsRibbon traces={traces} />
        </div>
      )}

      {/* ── Main Full-Width Trace List Grid (No Redundant Right Window) ──────────── */}
      <div className="flex-1 overflow-hidden min-h-0">
        <TraceList
          traces={traces}
          selectedTrace={selectedTrace}
          onSelectTrace={(trace) => {
            setSelectedTrace(trace);
            router.push(`/monitor/trace/${trace.id}`);
          }}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
        />
      </div>
    </div>
  );
}
