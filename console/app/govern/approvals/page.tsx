"use client";

import React, { useState } from "react";
import { GovernSubNav } from "@/components/govern/GovernSubNav";
import { useGovernance, ApprovalRequest } from "@/hooks/useGovernance";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  Layers,
  ChevronDown,
  ChevronRight,
  Code2,
} from "lucide-react";

export default function ApprovalsPage() {
  const { approvals, approveRequest, rejectRequest, pendingApprovalsCount } = useGovernance();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((curr) => (curr === id ? null : id));
  };

  return (
    <div className="space-y-5">
      <GovernSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-amber-400" />
            <h1 className="text-xl font-bold font-mono text-text-primary">
              Human-in-the-Loop (HITL) Approvals Queue
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-mono font-semibold">
              {pendingApprovalsCount} Pending
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Admin-scoped operations and destructive tool calls intercepted by GovernOS Sentinel awaiting cryptographic authorization.
          </p>
        </div>
      </div>

      {/* Approvals List */}
      <div className="space-y-3 font-mono">
        {approvals.length === 0 ? (
          <div className="p-12 text-center text-text-muted text-xs glass-card rounded-xl">
            <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            Approvals queue is clear. Zero pending human authorizations.
          </div>
        ) : (
          approvals.map((item) => {
            const isExpanded = expandedId === item.id;
            const isPending = item.status === "pending";

            return (
              <div
                key={item.id}
                className={`glass-card rounded-xl p-4 border transition-all space-y-3 ${
                  item.status === "approved"
                    ? "border-emerald-500/30 bg-emerald-500/5"
                    : item.status === "rejected"
                    ? "border-rose-500/30 bg-rose-500/5 opacity-60"
                    : "border-surface-border hover:border-surface-border/80"
                }`}
              >
                {/* Main Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleExpand(item.id)}
                      className="text-text-muted hover:text-text-primary transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-text-primary">{item.id}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-primary/20 text-primary-light font-semibold">
                          {item.requested_scope.toUpperCase()}
                        </span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                            item.risk_level === "Critical"
                              ? "bg-rose-500/20 text-rose-400"
                              : "bg-amber-500/20 text-amber-400"
                          }`}
                        >
                          Risk: {item.risk_score}/100
                        </span>
                      </div>
                      <div className="text-[11px] text-text-secondary mt-0.5">
                        <span className="font-semibold text-text-primary">{item.agent_name}</span>{" "}
                        wants to execute <span className="text-cyan-300 font-bold">{item.tool_name}</span> on{" "}
                        <span className="text-text-primary underline">{item.target_resource}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions or Status Badge */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isPending ? (
                      <>
                        <div className="flex items-center gap-1 text-[10px] text-text-muted mr-2">
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span>{item.timeout_seconds}s timeout</span>
                        </div>

                        <button
                          onClick={() => rejectRequest(item.id)}
                          className="px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-rose-500/20 border border-surface-border text-rose-400 text-xs font-semibold transition-colors flex items-center gap-1"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Reject
                        </button>

                        <button
                          onClick={() => approveRequest(item.id)}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors flex items-center gap-1 shadow-sm"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Approve & Sign
                        </button>
                      </>
                    ) : (
                      <span
                        className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase ${
                          item.status === "approved"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-rose-500/20 text-rose-400"
                        }`}
                      >
                        {item.status}
                      </span>
                    )}
                  </div>
                </div>

                {/* Expanded Payload Drawer */}
                {isExpanded && (
                  <div className="pt-2 border-t border-surface-border/60 space-y-2 text-xs">
                    <div className="flex items-center justify-between text-[10px] text-text-muted uppercase font-bold">
                      <span>Intercepted Execution Payload</span>
                      <span>Session: {item.session_id}</span>
                    </div>

                    <pre className="p-3 rounded-lg bg-[#0B0D14] border border-surface-border text-[11px] text-emerald-300 overflow-x-auto">
                      {JSON.stringify(item.payload, null, 2)}
                    </pre>
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
