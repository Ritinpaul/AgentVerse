"use client";

import React from "react";
import { ShieldCheck, ShieldAlert, ShieldX, Lock, AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react";
import type { ExecutionTrace } from "@/lib/api";

interface GovernanceEventsProps {
  trace: ExecutionTrace | null;
}

const ASI_RULE_TITLES: Record<string, string> = {
  ASI01: "Prompt Injection Attack Shield",
  ASI02: "Tool Scope & Method Authorization",
  ASI03: "PII & Secret Data Redaction",
  ASI04: "Runaway Cost & Token Circuit Breaker",
  ASI05: "Sandbox Escape & Dangerous Command Gate",
  ASI06: "Fallback Model Downgrade Safeguard",
  ASI07: "Cryptographic Audit Provenance",
  ASI08: "Cross-Run Memory Isolation",
  ASI09: "A2A Escrow Micropayment Verification",
  ASI10: "Agent Whitelist & Registry Provenance",
};

export function GovernanceEvents({ trace }: GovernanceEventsProps) {
  if (!trace) {
    return (
      <div className="p-8 text-center text-text-muted text-xs font-mono">
        Select a trace to view GovernOS in-runtime decisions.
      </div>
    );
  }

  const govEvents = trace.events.filter((e) => e.type === "governos_gate" || e.status === "blocked");

  return (
    <div className="space-y-4">
      {/* Governance Scorecard */}
      <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-violet-400" />
            <span className="text-xs font-mono font-bold text-text-primary">
              GovernOS SENTINEL Policy Evaluation
            </span>
          </div>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
              trace.governance_violations === 0
                ? "bg-emerald-500/20 text-emerald-400"
                : "bg-rose-500/20 text-rose-400"
            }`}
          >
            {trace.governance_violations === 0 ? "PASSED (100/100)" : "BLOCKED BREACH"}
          </span>
        </div>

        <p className="text-[11px] text-text-muted leading-relaxed">
          Every tool invocation and LLM output passes through structural in-runtime gates. Zero unverified tool calls reach the host operating system.
        </p>

        <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-1">
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border">
            <div className="text-[10px] text-text-muted">GATES EVALUATED</div>
            <div className="font-bold text-text-primary mt-0.5">{govEvents.length}</div>
          </div>
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border">
            <div className="text-[10px] text-text-muted">BLOCKED BREACHES</div>
            <div className="font-bold text-rose-400 mt-0.5">{trace.governance_violations}</div>
          </div>
          <div className="p-2 rounded-lg bg-surface-100 border border-surface-border">
            <div className="text-[10px] text-text-muted">TRUST SCORE</div>
            <div className="font-bold text-emerald-400 mt-0.5">{trace.governance_score}/100</div>
          </div>
        </div>
      </div>

      {/* Sentinel Gates Timeline */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider font-mono">
          In-Runtime Interceptions ({govEvents.length})
        </h4>

        {govEvents.length === 0 ? (
          <div className="p-4 text-center text-text-muted text-xs font-mono border border-surface-border rounded-lg">
            No gate violations recorded for this execution.
          </div>
        ) : (
          govEvents.map((event, idx) => {
            const isBlocked = event.status === "blocked";
            const ruleCode = event.governance_rule ?? "ASI-SEC";
            const ruleTitle = ASI_RULE_TITLES[ruleCode] ?? "Runtime Policy Enforcement";

            return (
              <div
                key={idx}
                className={`p-3 rounded-xl border space-y-2 text-xs font-mono ${
                  isBlocked
                    ? "bg-rose-500/10 border-rose-500/40 text-rose-300"
                    : event.status === "warning"
                    ? "bg-amber-500/10 border-amber-500/40 text-amber-300"
                    : "bg-surface-50 border-surface-border text-text-secondary"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        isBlocked
                          ? "bg-rose-500/20 text-rose-400"
                          : event.status === "warning"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-emerald-500/20 text-emerald-400"
                      }`}
                    >
                      {ruleCode}
                    </span>
                    <span className="font-semibold text-text-primary text-[11px]">
                      {ruleTitle}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-bold uppercase ${
                      isBlocked
                        ? "text-rose-400"
                        : event.status === "warning"
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {event.governance_decision ?? event.status}
                  </span>
                </div>

                <p className="text-[11px] text-text-muted leading-relaxed">{event.label}</p>

                {event.details && (
                  <div className="p-2 rounded bg-surface-100/70 border border-surface-border text-[10px] space-y-1">
                    {Object.entries(event.details).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-text-muted">{k}:</span>
                        <span className="text-text-primary font-bold">
                          {typeof v === "object" ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
