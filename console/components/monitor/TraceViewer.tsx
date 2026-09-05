"use client";

import React, { useState, useCallback } from "react";
import {
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
  ChevronsUpDown,
  Maximize2,
} from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";
import type { ExecutionTrace, TraceEvent } from "@/lib/api";

interface TraceViewerProps {
  trace: ExecutionTrace | null;
  onReRun?: (slug: string) => void;
}

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

export function TraceViewer({ trace, onReRun }: TraceViewerProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});
  const [copiedSession, setCopiedSession] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [reRunning, setReRunning] = useState(false);

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
      onReRun?.(trace.agent_slug);
    }, 900);
  }, [trace, onReRun]);

  if (!trace) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 text-center text-neutral-400">
        <Activity className="w-12 h-12 text-[#38D9A9]/40 mb-3 animate-pulse" />
        <h3 className="text-sm font-semibold text-white font-mono">
          Select an execution trace to inspect
        </h3>
        <p className="text-xs max-w-sm mt-1 text-neutral-400">
          Explore causal reasoning chains, MCP tool input/output payloads, and in-runtime GovernOS policy decisions.
        </p>
      </div>
    );
  }

  const maxDuration = Math.max(trace.duration_ms, 1);

  return (
    <div className="flex flex-col h-full space-y-3 min-h-0 text-white font-sans">
      {/* ── Trace Header Bar ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1E1E28] pb-3 shrink-0">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="font-mono font-bold text-base text-white">
              {trace.agent_name}
            </h2>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#14151D] text-neutral-300 border border-[#242532]">
              {trace.id}
            </span>
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                trace.status === "success"
                  ? "bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30"
                  : trace.status === "blocked"
                  ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                  : "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
              }`}
            >
              {trace.status.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] font-mono text-neutral-400 mt-1 flex-wrap">
            <span>Slug: <strong className="text-neutral-200">{trace.agent_slug}</strong></span>
            <span>·</span>
            <button
              onClick={handleCopySession}
              className="hover:text-white flex items-center gap-1 transition-colors"
              title="Copy session ID"
            >
              <span>Session: <strong className="text-neutral-200">{trace.session_id}</strong></span>
              {copiedSession ? (
                <Check className="w-3 h-3 text-[#38D9A9]" />
              ) : (
                <Copy className="w-3 h-3 text-neutral-500" />
              )}
            </button>
            <span>·</span>
            <span>VM: <strong className="text-neutral-200">{trace.vm_id}</strong></span>
            <span>·</span>
            <span>Model: <strong className="text-[#38D9A9]">{trace.model}</strong></span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => setShowRawJson((prev) => !prev)}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono transition-colors flex items-center gap-1 ${
              showRawJson
                ? "bg-[#222432] text-white border-[#323446]"
                : "bg-[#14151D] hover:bg-[#1C1D28] text-neutral-300 border-[#242532]"
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-[#38D9A9]" />
            {showRawJson ? "Waterfall View" : "Raw JSON"}
          </button>

          <button
            onClick={handleCopyJson}
            className="p-1.5 rounded-lg bg-[#14151D] hover:bg-[#1C1D28] border border-[#242532] text-neutral-300 text-xs transition-colors"
            title="Copy trace JSON"
          >
            {copiedJson ? <Check className="w-3.5 h-3.5 text-[#38D9A9]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <a
            href={`/monitor/trace/${trace.id}`}
            className="p-1.5 rounded-lg bg-[#14151D] hover:bg-[#E5252A] border border-[#242532] text-neutral-300 hover:text-white text-xs transition-colors flex items-center gap-1 font-mono"
            title="Open Dedicated Full-Page Trace Route"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </a>

          <button
            onClick={handleDownloadJson}
            className="p-1.5 rounded-lg bg-[#14151D] hover:bg-[#1C1D28] border border-[#242532] text-neutral-300 text-xs transition-colors"
            title="Download trace JSON"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleExecuteReRun}
            disabled={reRunning}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-bold font-mono transition-all shadow-xs"
          >
            {reRunning ? (
              <>
                <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Re-run
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Summary Stats Ribbon ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 shrink-0 font-mono text-xs">
        <div className="p-2.5 rounded-xl bg-[#12131A] border border-[#22222E]">
          <div className="text-[10px] text-neutral-400 uppercase font-semibold">Total Duration</div>
          <div className="text-sm font-bold text-white mt-0.5">
            {formatLatency(trace.duration_ms)}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">P95: 1,240ms baseline</div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#12131A] border border-[#22222E]">
          <div className="text-[10px] text-neutral-400 uppercase font-semibold">Token Breakdown</div>
          <div className="text-sm font-bold text-[#38D9A9] mt-0.5">
            {trace.total_tokens.toLocaleString()}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            {trace.prompt_tokens} in / {trace.completion_tokens} out
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#12131A] border border-[#22222E]">
          <div className="text-[10px] text-neutral-400 uppercase font-semibold">Execution Spend</div>
          <div className="text-sm font-bold text-emerald-400 mt-0.5">
            {formatCurrency(trace.total_cost_usd)}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            ${(trace.total_cost_usd / (trace.total_tokens / 1000 || 1)).toFixed(5)}/k tok
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-[#12131A] border border-[#22222E]">
          <div className="text-[10px] text-neutral-400 uppercase font-semibold">GovernOS Sentinel</div>
          <div
            className={`text-sm font-bold mt-0.5 ${
              trace.governance_violations > 0 ? "text-amber-400" : "text-[#38D9A9]"
            }`}
          >
            {trace.governance_violations === 0 ? "100% Passed" : `${trace.governance_violations} Violation`}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            Trust score: {trace.governance_score}/100
          </div>
        </div>
      </div>

      {/* ── Main View: Waterfall vs Raw JSON ───────────────────────────────── */}
      {showRawJson ? (
        <div className="flex-1 min-h-0 bg-[#090A0E] p-4 rounded-xl border border-[#1E1E28] overflow-y-auto">
          <pre className="text-xs font-mono text-[#38D9A9] leading-relaxed">
            {JSON.stringify(trace, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="flex-1 flex flex-col space-y-3 min-h-0 overflow-hidden">
          {/* Visual Timeline Bar Header */}
          <div className="p-3 rounded-xl bg-[#12131A] border border-[#22222E] space-y-2 shrink-0">
            <div className="flex items-center justify-between text-[11px] font-mono text-neutral-300">
              <span className="font-bold text-white">Visual Execution Timeline (0ms → {trace.duration_ms}ms)</span>
              <span className="text-neutral-400">{trace.events.length} Causal Steps</span>
            </div>

            {/* Proportional Segmented Timeline Bar */}
            <div className="h-3.5 rounded-lg bg-[#1A1C26] overflow-hidden flex border border-[#262838]">
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
            <div className="flex items-center gap-4 text-[10px] font-mono text-neutral-400 flex-wrap pt-0.5">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500" /> Start
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-500" /> Tool Request
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-violet-500" /> GovernOS Gate
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400" /> LLM Generation
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#38D9A9]" /> Output Complete
              </span>
            </div>
          </div>

          {/* ── Causal Event Waterfall Steps ───────────────────────────────── */}
          <div className="flex-1 overflow-y-auto min-h-0 pr-1 space-y-2">
            {trace.events.map((event, idx) => {
              const Icon = getEventIcon(event.type);
              const isExpanded = !!expandedSteps[idx];

              return (
                <div
                  key={idx}
                  className={`rounded-xl border transition-all ${
                    isExpanded
                      ? "bg-[#14151E] border-[#323446] shadow-lg"
                      : "bg-[#101117] border-[#1E1E28] hover:bg-[#14151E] hover:border-[#282A3A]"
                  }`}
                >
                  {/* Step Row Header */}
                  <div
                    onClick={() => toggleStep(idx)}
                    className="p-3 flex items-center justify-between gap-3 cursor-pointer text-xs select-none"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="text-neutral-400">
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-[#38D9A9]" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </div>

                      {/* Icon */}
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                          event.status === "allowed" || event.status === "success"
                            ? "bg-[#38D9A9]/15 text-[#38D9A9] border-[#38D9A9]/30"
                            : event.status === "blocked"
                            ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                            : event.status === "warning"
                            ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                            : "bg-[#222432] text-white border-[#323446]"
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </div>

                      {/* Offset & Step Info */}
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-white truncate">
                            {event.label}
                          </span>
                          {event.governance_rule && (
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 font-bold">
                              {event.governance_rule}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-neutral-400 mt-0.5">
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
                    <div className="flex items-center gap-2 shrink-0 font-mono text-xs">
                      {event.cost_usd !== undefined && (
                        <span className="text-[11px] text-emerald-400 font-semibold">
                          {formatCurrency(event.cost_usd)}
                        </span>
                      )}
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase border ${
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

                  {/* Expanded Step Payload Inspector */}
                  {isExpanded && (
                    <div className="px-3.5 pb-3.5 pt-2 border-t border-[#20212C] space-y-3 font-mono text-xs bg-[#0C0D12] rounded-b-xl">
                      {/* Input Payload */}
                      {event.input_payload && (
                        <div>
                          <div className="text-[10px] text-neutral-400 uppercase font-semibold mb-1 flex items-center justify-between">
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
                              className="text-[9px] text-[#38D9A9] hover:underline flex items-center gap-0.5"
                            >
                              <Copy className="w-2.5 h-2.5" /> Copy Input
                            </button>
                          </div>
                          <pre className="p-3 rounded-lg bg-[#07080B] border border-[#1C1D26] text-[11px] text-emerald-300 overflow-x-auto leading-relaxed">
                            {typeof event.input_payload === "string"
                              ? event.input_payload
                              : JSON.stringify(event.input_payload, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Output Payload */}
                      {event.output_payload && (
                        <div>
                          <div className="text-[10px] text-neutral-400 uppercase font-semibold mb-1 flex items-center justify-between">
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
                              className="text-[9px] text-[#38D9A9] hover:underline flex items-center gap-0.5"
                            >
                              <Copy className="w-2.5 h-2.5" /> Copy Output
                            </button>
                          </div>
                          <pre className="p-3 rounded-lg bg-[#07080B] border border-[#1C1D26] text-[11px] text-cyan-300 overflow-x-auto leading-relaxed">
                            {typeof event.output_payload === "string"
                              ? event.output_payload
                              : JSON.stringify(event.output_payload, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Raw Details / Metadata */}
                      {event.details && Object.keys(event.details).length > 0 && (
                        <div>
                          <div className="text-[10px] text-neutral-400 uppercase font-semibold mb-1">
                            Step Telemetry Metadata
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 p-2.5 rounded-lg bg-[#12131A] border border-[#20212C] text-[10px]">
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
    </div>
  );
}
