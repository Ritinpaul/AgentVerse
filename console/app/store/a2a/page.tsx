"use client";

import React, { useState, useCallback } from "react";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import { useStore } from "@/hooks/useStore";
import {
  Handshake,
  ShieldCheck,
  DollarSign,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ArrowRight,
  Check,
  Copy,
} from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";

export default function A2AContractsPage() {
  const { contracts, settleContract, activeContractsCount } = useStore();
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const handleCopy = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-5 font-mono">
      <StoreSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Handshake className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              Agent-to-Agent (A2A) Micropayment Escrow
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              {activeContractsCount} Active Contracts
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Autonomous machine-to-machine micropayments adhering to the x402 protocol with automatic SLA compliance and escrow lockups.
          </p>
        </div>
      </div>

      {/* Contracts Table */}
      <div className="glass-card rounded-xl border border-surface-border overflow-hidden text-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-surface-200/80 text-[10px] text-text-muted uppercase border-b border-surface-border">
              <tr>
                <th className="py-2.5 px-3">Contract ID</th>
                <th className="py-2.5 px-3">Initiator Agent</th>
                <th className="py-2.5 px-3">Provider Agent</th>
                <th className="py-2.5 px-3">Escrow Locked</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">SLA Target</th>
                <th className="py-2.5 px-3">Created</th>
                <th className="py-2.5 px-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {contracts.map((item) => (
                <tr key={item.id} className="hover:bg-surface-100/50 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-bold text-text-primary">{item.id}</div>
                    <button
                      onClick={() => handleCopy(item.contract_hash)}
                      className="text-[10px] text-text-muted hover:text-primary-light flex items-center gap-0.5 mt-0.5"
                      title="Copy contract hash"
                    >
                      <span className="truncate max-w-[100px]">{item.contract_hash}</span>
                      {copiedHash === item.contract_hash ? (
                        <Check className="w-2.5 h-2.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-2.5 h-2.5 opacity-50" />
                      )}
                    </button>
                  </td>
                  <td className="py-3 px-3 text-text-secondary">{item.initiator_agent}</td>
                  <td className="py-3 px-3 text-text-primary font-semibold">{item.provider_agent}</td>
                  <td className="py-3 px-3 text-emerald-400 font-bold">
                    {formatCurrency(item.escrow_amount_usd)}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        item.status === "settled"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : item.status === "escrow_locked"
                          ? "bg-cyan-500/20 text-cyan-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-text-muted">
                    {formatLatency(item.sla_latency_ms_max)} max
                    {item.actual_latency_ms && (
                      <div className="text-[10px] text-emerald-400 font-bold">
                        Actual: {formatLatency(item.actual_latency_ms)}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-3 text-[10px] text-text-muted whitespace-nowrap">
                    {item.created_at}
                  </td>
                  <td className="py-3 px-3">
                    {item.status !== "settled" ? (
                      <button
                        onClick={() => settleContract(item.id)}
                        className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] transition-all"
                      >
                        Settle Now
                      </button>
                    ) : (
                      <span className="text-[10px] text-text-muted">Settled</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
