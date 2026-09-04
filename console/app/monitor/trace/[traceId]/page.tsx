"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient, ExecutionTrace, TraceEvent } from "@/lib/api";
import { GovernanceEvents } from "@/components/monitor/GovernanceEvents";
import { CostBreakdown } from "@/components/monitor/CostBreakdown";
import { LiveFeed } from "@/components/monitor/LiveFeed";
import {
  ArrowLeft,
  Activity,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Download,
  Play,
  ChevronDown,
  ChevronRight,
  Globe,
  Zap,
  Cpu,
  Code2,
  Terminal,
  DollarSign,
  Layers,
} from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";

type ViewTab = "waterfall" | "governance" | "cost" | "live_feed";

function getEventIcon(type: TraceEvent["type"]) {
  switch (type) {
    case "agent_start":
      return Cpu;
    case "tool_call":
      return Globe;
    case "governos_gate":
      return ShieldCheck;
    case "llm_call":
      return Cpu;
    case "tool_response":
      return Zap;
    case "agent_complete":
      return CheckCircle2;
    case "error":
      return AlertTriangle;
    default:
      return Activity;
  }
}

export default function DedicatedTracePage() {
  const params = useParams();
  const router = useRouter();
  const traceId = (params.traceId as string) || "run-94821";

  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ViewTab>("waterfall");
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({ 0: true, 1: true, 3: true, 4: true });
  const [copiedSession, setCopiedSession] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [reRunning, setReRunning] = useState(false);

  useEffect(() => {
    async function loadTrace() {
      setLoading(true);
      const data = await apiClient.getTrace(traceId);
      setTrace(data);
      setLoading(false);
    }
    loadTrace();
  }, [traceId]);

  const toggleStep = useCallback((index: number) => {
    setExpandedSteps((prev) => ({ ...prev, [index]: !prev[index] }));
  }, []);

  const handleCopySession = useCallback(() => {
    if (!trace) return;
    navigator.clipboard.writeText(trace.session_id);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 2000);
  }, [trace]);

  const handleCopyJson = useCallback(() => {
    if (!trace) return;
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  }, [trace]);

  const handleDownloadJson = useCallback(() => {
    if (!trace) return;
    const blob = new Blob([JSON.stringify(trace, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace-${trace.id}-${trace.session_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [trace]);

  const handleExecuteReRun = useCallback(() => {
    if (!trace) return;
    setReRunning(true);
    setTimeout(() => {
      setReRunning(false);
      alert(`Re-executing ${trace.agent_name} (${trace.id}) in isolated MicroVM sandbox...`);
    }, 900);
  }, [trace]);

  if (loading) {
    return (
      <div className="h-full w-full bg-[#0A0A0E] text-white flex items-center justify-center font-mono text-xs">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-[#38D9A9] border-t-transparent rounded-full animate-spin" />
          <span>Loading execution trace {traceId}...</span>
        </div>
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="h-full w-full bg-[#0A0A0E] text-white flex flex-col items-center justify-center p-6 text-center font-sans">
        <Activity className="w-12 h-12 text-rose-500 mb-3" />
        <h2 className="text-lg font-bold">Execution Trace Not Found</h2>
        <p className="text-xs text-neutral-400 mt-1 mb-4">No trace record matching ID &quot;{traceId}&quot; exists.</p>
        <button
          onClick={() => router.push("/monitor")}
          className="px-4 py-2 rounded-xl bg-[#161722] border border-[#282938] text-white text-xs font-mono"
        >
          ← Return to Monitor Overview
        </button>
      </div>
    );
  }

  const maxDuration = Math.max(trace.duration_ms, 1);

  return (
    <div className="flex-1 flex flex-col h-full min-h-0 bg-[#0A0A0E] text-white font-sans overflow-hidden">
      {/* ── Fixed Top Header Bar (Pinned - Never Scrolls Away) ──────────────── */}
      <div className="bg-[#0E0F14] border-b border-[#1E1E28] px-6 py-3 flex items-center justify-between gap-4 shrink-0 z-20 shadow-md">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => router.push("/monitor")}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#14151D] hover:bg-[#1E1F2A] border border-[#242532] text-xs font-mono text-neutral-300 hover:text-white transition-all shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-[#38D9A9]" />
            <span className="whitespace-nowrap">Back to Observability</span>
          </button>

          <div className="h-5 w-px bg-[#20212C] shrink-0" />

          {/* Agent Title & Metadata Badges */}
          <div className="flex items-center gap-2.5 min-w-0 overflow-x-auto no-scrollbar">
            <h1 className="text-base font-bold text-white tracking-wide font-sans whitespace-nowrap shrink-0">
              {trace.agent_name}
            </h1>
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-[#161722] text-neutral-300 border border-[#282938] whitespace-nowrap shrink-0">
              {trace.id}
            </span>
            <span
              className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full uppercase border whitespace-nowrap shrink-0 ${
                trace.status === "success"
                  ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                  : trace.status === "blocked"
                  ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                  : "bg-cyan-500/15 text-cyan-400 border-cyan-500/30"
              }`}
            >
              {trace.status}
            </span>

            <span className="text-xs font-mono text-neutral-500 hidden xl:inline">·</span>
            <span className="text-xs font-mono text-neutral-400 hidden xl:inline whitespace-nowrap">
              Slug: <strong className="text-white">{trace.agent_slug}</strong>
            </span>
            <span className="text-xs font-mono text-neutral-500 hidden xl:inline">·</span>
            <button
              onClick={handleCopySession}
              className="text-xs font-mono text-neutral-400 hover:text-white hidden xl:flex items-center gap-1 transition-colors whitespace-nowrap"
              title="Copy Session ID"
            >
              <span>Session: <strong className="text-white">{trace.session_id}</strong></span>
              {copiedSession ? <Check className="w-3 h-3 text-[#38D9A9]" /> : <Copy className="w-3 h-3 text-neutral-500" />}
            </button>
            <span className="text-xs font-mono text-neutral-500 hidden xl:inline">·</span>
            <span className="text-xs font-mono text-neutral-400 hidden xl:inline whitespace-nowrap">
              VM: <strong className="text-white">{trace.vm_id}</strong>
            </span>
            <span className="text-xs font-mono text-neutral-500 hidden xl:inline">·</span>
            <span className="text-xs font-mono text-neutral-400 hidden xl:inline whitespace-nowrap">
              Model: <strong className="text-[#38D9A9]">{trace.model}</strong>
            </span>
          </div>
        </div>

        {/* Top Header Right Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowRawJson((prev) => !prev)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono font-semibold transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              showRawJson
                ? "bg-[#222432] text-white border-[#323446]"
                : "bg-[#14151D] hover:bg-[#1C1D28] text-neutral-300 border-[#242532]"
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-[#38D9A9]" />
            <span>{showRawJson ? "Waterfall View" : "Raw JSON"}</span>
          </button>

          <button
            onClick={handleCopyJson}
            className="p-2 rounded-xl bg-[#14151D] hover:bg-[#1C1D28] border border-[#242532] text-neutral-300 text-xs transition-colors"
            title="Copy trace JSON"
          >
            {copiedJson ? <Check className="w-3.5 h-3.5 text-[#38D9A9]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleDownloadJson}
            className="p-2 rounded-xl bg-[#14151D] hover:bg-[#1C1D28] border border-[#242532] text-neutral-300 text-xs transition-colors"
            title="Download trace JSON"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleExecuteReRun}
            disabled={reRunning}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-[#E5252A] hover:bg-[#D01E23] text-white text-xs font-bold font-mono transition-all shadow-md shadow-[#E5252A]/20 whitespace-nowrap"
          >
            {reRunning ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Executing...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Re-run</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Scrollable Body Area (Only Content Scrolls) ────────────────────── */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Sub-tab navigation */}
          <div className="flex items-center justify-between border-b border-[#1E1E28] pb-4">
            <div className="flex items-center rounded-xl bg-[#14151D] p-1 border border-[#242532] text-xs font-mono">
              <button
                onClick={() => setActiveTab("waterfall")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === "waterfall"
                    ? "bg-[#222432] text-white font-bold border border-[#323446] shadow-xs"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <Layers className="w-4 h-4 text-[#38D9A9]" />
                Waterfall Trace
              </button>
              <button
                onClick={() => setActiveTab("governance")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === "governance"
                    ? "bg-[#222432] text-white font-bold border border-[#323446] shadow-xs"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <ShieldCheck className="w-4 h-4 text-violet-400" />
                GovernOS Sentinel
                {trace.governance_violations > 0 && (
                  <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
                )}
              </button>
              <button
                onClick={() => setActiveTab("cost")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === "cost"
                    ? "bg-[#222432] text-white font-bold border border-[#323446] shadow-xs"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <DollarSign className="w-4 h-4 text-emerald-400" />
                Cost Attribution
              </button>
              <button
                onClick={() => setActiveTab("live_feed")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === "live_feed"
                    ? "bg-[#222432] text-white font-bold border border-[#323446] shadow-xs"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <Terminal className="w-4 h-4 text-cyan-400" />
                Live Feed
              </button>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs text-neutral-400">
              <span>Trigger: <strong className="text-white uppercase">{trace.trigger}</strong></span>
              <span>·</span>
              <span>Start: <strong className="text-white">{new Date(trace.start_time).toLocaleTimeString()}</strong></span>
            </div>
          </div>

          {/* Sub-tab Views */}
          {activeTab === "governance" && (
            <div className="p-6 bg-[#12131A] border border-[#22222E] rounded-2xl">
              <GovernanceEvents trace={trace} />
            </div>
          )}

          {activeTab === "cost" && (
            <div className="p-6 bg-[#12131A] border border-[#22222E] rounded-2xl">
              <CostBreakdown trace={trace} />
            </div>
          )}

          {activeTab === "live_feed" && (
            <div className="h-[600px] p-6 bg-[#12131A] border border-[#22222E] rounded-2xl">
              <LiveFeed />
            </div>
          )}

          {activeTab === "waterfall" && (
            <>
              {/* ── 4 Key Metric Summary Cards ─────────────────────────────────── */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
                <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] shadow-lg">
                  <div className="text-[11px] text-neutral-400 uppercase font-semibold">Total Duration</div>
                  <div className="text-xl font-bold text-white mt-1">
                    {formatLatency(trace.duration_ms)}
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-1">P95: 1,240ms baseline</div>
                </div>

                <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] shadow-lg">
                  <div className="text-[11px] text-neutral-400 uppercase font-semibold">Token Breakdown</div>
                  <div className="text-xl font-bold text-[#38D9A9] mt-1">
                    {trace.total_tokens.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-1">
                    {trace.prompt_tokens} in / {trace.completion_tokens} out
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] shadow-lg">
                  <div className="text-[11px] text-neutral-400 uppercase font-semibold">Execution Spend</div>
                  <div className="text-xl font-bold text-emerald-400 mt-1">
                    {formatCurrency(trace.total_cost_usd)}
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-1">
                    ${(trace.total_cost_usd / (trace.total_tokens / 1000 || 1)).toFixed(5)}/k tok
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] shadow-lg">
                  <div className="text-[11px] text-neutral-400 uppercase font-semibold">GovernOS Sentinel</div>
                  <div
                    className={`text-xl font-bold mt-1 ${
                      trace.governance_violations > 0 ? "text-amber-400" : "text-[#38D9A9]"
                    }`}
                  >
                    {trace.governance_violations === 0 ? "100% Passed" : `${trace.governance_violations} Violation`}
                  </div>
                  <div className="text-[11px] text-neutral-500 mt-1">
                    Trust score: {trace.governance_score}/100
                  </div>
                </div>
              </div>

              {/* ── Main View: Waterfall vs Raw JSON ──────────────────────────── */}
              {showRawJson ? (
                <div className="bg-[#090A0E] p-6 rounded-2xl border border-[#1E1E28] overflow-y-auto">
                  <pre className="text-xs font-mono text-[#38D9A9] leading-relaxed">
                    {JSON.stringify(trace, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Visual Execution Timeline Bar Header */}
                  <div className="p-4 rounded-2xl bg-[#12131A] border border-[#22222E] space-y-3 shadow-lg">
                    <div className="flex items-center justify-between text-xs font-mono text-neutral-300">
                      <span className="font-bold text-white text-sm">Visual Execution Timeline (0ms → {trace.duration_ms}ms)</span>
                      <span className="text-neutral-400">{trace.events.length} Causal Steps</span>
                    </div>

                    {/* Proportional Segmented Timeline Bar */}
                    <div className="h-4 rounded-xl bg-[#1A1C26] overflow-hidden flex border border-[#262838]">
                      {trace.events.map((event, i) => {
                        const widthPercent = Math.max(
                          ((event.step_duration_ms ?? 10) / maxDuration) * 100,
                          3
                        );

                        const segColor =
                          event.type === "agent_start"
                            ? "bg-blue-500"
                            : event.type === "tool_call"
                            ? "bg-cyan-500"
                            : event.type === "governos_gate"
                            ? event.status === "blocked"
                              ? "bg-rose-500"
                              : "bg-violet-500"
                            : event.type === "llm_call"
                            ? "bg-amber-400"
                            : event.type === "error"
                            ? "bg-red-500"
                            : "bg-[#38D9A9]";

                        return (
                          <div
                            key={i}
                            style={{ width: `${widthPercent}%` }}
                            className={`${segColor} h-full border-r border-[#090A0E] cursor-pointer hover:opacity-80 transition-opacity`}
                            title={`${event.label} (+${event.timestamp_offset_ms}ms, duration: ${event.step_duration_ms ?? 0}ms)`}
                            onClick={() => toggleStep(i)}
                          />
                        );
                      })}
                    </div>

                    {/* Legend */}
                    <div className="flex items-center gap-5 text-xs font-mono text-neutral-400 flex-wrap pt-1">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Start
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Tool Request
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-violet-500" /> GovernOS Gate
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> LLM Generation
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-[#38D9A9]" /> Output Complete
                      </span>
                    </div>
                  </div>

                  {/* ── Causal Event Waterfall Steps (Full Page View) ───────────── */}
                  <div className="space-y-3">
                    {trace.events.map((event, idx) => {
                      const Icon = getEventIcon(event.type);
                      const isExpanded = !!expandedSteps[idx];

                      return (
                        <div
                          key={idx}
                          className={`rounded-2xl border transition-all shadow-md ${
                            isExpanded
                              ? "bg-[#14151E] border-[#323446]"
                              : "bg-[#101117] border-[#1E1E28] hover:bg-[#14151E] hover:border-[#282A3A]"
                          }`}
                        >
                          {/* Step Row Header */}
                          <div
                            onClick={() => toggleStep(idx)}
                            className="p-4 flex items-center justify-between gap-4 cursor-pointer text-xs select-none"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="text-neutral-400">
                                {isExpanded ? (
                                  <ChevronDown className="w-4 h-4 text-[#38D9A9]" />
                                ) : (
                                  <ChevronRight className="w-4 h-4" />
                                )}
                              </div>

                              {/* Icon */}
                              <div
                                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
                                  event.status === "allowed" || event.status === "success"
                                    ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                                    : event.status === "blocked"
                                    ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                    : event.status === "warning"
                                    ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                                    : "bg-[#222432] text-white border-[#323446]"
                                }`}
                              >
                                <Icon className="w-4 h-4" />
                              </div>

                              {/* Offset & Step Info */}
                              <div className="min-w-0">
                                <div className="flex items-center gap-2.5">
                                  <span className="font-mono text-sm font-bold text-white truncate">
                                    {event.label}
                                  </span>
                                  {event.governance_rule && (
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 font-bold">
                                      {event.governance_rule}
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-3 text-xs font-mono text-neutral-400 mt-1">
                                  <span>+{event.timestamp_offset_ms}ms</span>
                                  {event.step_duration_ms !== undefined && (
                                    <>
                                      <span>·</span>
                                      <span>Δ {event.step_duration_ms}ms</span>
                                    </>
                                  )}
                                  {event.model && (
                                    <>
                                      <span>·</span>
                                      <span className="text-[#38D9A9]">{event.model}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Right: Badge & Cost */}
                            <div className="flex items-center gap-3 shrink-0 font-mono text-xs">
                              {event.cost_usd !== undefined && (
                                <span className="text-xs text-emerald-400 font-semibold">
                                  {formatCurrency(event.cost_usd)}
                                </span>
                              )}
                              <span
                                className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase border ${
                                  event.status === "allowed" || event.status === "success"
                                    ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                                    : event.status === "blocked"
                                    ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                    : event.status === "warning"
                                    ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                                    : "bg-[#1C1D28] text-neutral-300 border-[#282A3A]"
                                }`}
                              >
                                {event.status}
                              </span>
                            </div>
                          </div>

                          {/* Expanded Step Payload Inspector (Full Width Code Boxes) */}
                          {isExpanded && (
                            <div className="px-5 pb-5 pt-3 border-t border-[#20212C] space-y-4 font-mono text-xs bg-[#0C0D12] rounded-b-2xl">
                              {/* Input Payload */}
                              {event.input_payload && (
                                <div>
                                  <div className="text-xs text-neutral-400 uppercase font-semibold mb-1.5 flex items-center justify-between">
                                    <span>Input Payload / Arguments</span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigator.clipboard.writeText(
                                          typeof event.input_payload === "string"
                                            ? event.input_payload
                                            : JSON.stringify(event.input_payload, null, 2)
                                        );
                                      }}
                                      className="text-xs text-[#38D9A9] hover:underline flex items-center gap-1 font-mono"
                                    >
                                      <Copy className="w-3 h-3" /> Copy Input Payload
                                    </button>
                                  </div>
                                  <pre className="p-4 rounded-xl bg-[#07080B] border border-[#1C1D26] text-xs text-emerald-300 overflow-x-auto leading-relaxed shadow-inner">
                                    {typeof event.input_payload === "string"
                                      ? event.input_payload
                                      : JSON.stringify(event.input_payload, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {/* Output Payload */}
                              {event.output_payload && (
                                <div>
                                  <div className="text-xs text-neutral-400 uppercase font-semibold mb-1.5 flex items-center justify-between">
                                    <span>Output / Response Payload</span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigator.clipboard.writeText(
                                          typeof event.output_payload === "string"
                                            ? event.output_payload
                                            : JSON.stringify(event.output_payload, null, 2)
                                        );
                                      }}
                                      className="text-xs text-[#38D9A9] hover:underline flex items-center gap-1 font-mono"
                                    >
                                      <Copy className="w-3 h-3" /> Copy Output Response
                                    </button>
                                  </div>
                                  <pre className="p-4 rounded-xl bg-[#07080B] border border-[#1C1D26] text-xs text-cyan-300 overflow-x-auto leading-relaxed shadow-inner">
                                    {typeof event.output_payload === "string"
                                      ? event.output_payload
                                      : JSON.stringify(event.output_payload, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {/* Raw Details / Metadata */}
                              {event.details && Object.keys(event.details).length > 0 && (
                                <div>
                                  <div className="text-xs text-neutral-400 uppercase font-semibold mb-1.5">
                                    Step Telemetry Metadata
                                  </div>
                                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-[#12131A] border border-[#20212C] text-xs">
                                    {Object.entries(event.details).map(([k, v]) => (
                                      <div key={k}>
                                        <span className="text-neutral-400">{k}: </span>
                                        <span className="text-white font-bold">
                                          {typeof v === "object" ? JSON.stringify(v) : String(v)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
