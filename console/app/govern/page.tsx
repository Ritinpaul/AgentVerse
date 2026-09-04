"use client";

import React from "react";
import Link from "next/link";
import { useGovernance } from "@/hooks/useGovernance";
import { GovernSubNav } from "@/components/govern/GovernSubNav";
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  FileText,
  CheckCircle2,
  Zap,
  Radio,
  Award,
  ArrowRight,
  TrendingUp,
  Clock,
  Activity,
  Cpu,
} from "lucide-react";
import { formatCurrency, formatLatency } from "@/lib/utils";

export default function GovernOverviewPage() {
  const {
    policies,
    activePolicies,
    recentAudits,
    totalEnforced,
    blockedThreats,
    complianceScore,
    pendingApprovalsCount,
    cacheMetrics,
  } = useGovernance();

  return (
    <div className="space-y-6 font-mono text-white">
      {/* ── Sub Navigation ─────────────────────────────────────────────────── */}
      <GovernSubNav />

      {/* ── Header Banner (Curved Glassmorphism) ───────────────────────────── */}
      <div className="bg-[#22252A]/60 backdrop-blur-xl text-white p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10 shadow-2xl">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#E5252A] animate-pulse shadow-md shadow-red-500/50" />
            <h1 className="text-sm font-bold tracking-wider uppercase text-white">
              AgentGovernOS Kernel & Sentinel
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#10B981]/20 text-[#10B981] font-bold border border-[#10B981]/30">
              ● Port 8025 Active
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1 max-w-2xl">
            Unbypassable zero-trust tool call evaluation, ASI01–ASI10 automated vulnerability scanner, cryptographic audit ledger, and QI semantic cache.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs shrink-0">
          <div className="px-4 py-2 rounded-xl bg-[#141619]/90 border border-white/10 text-[#10B981] font-bold flex items-center gap-2 shadow-inner">
            <ShieldCheck className="w-4 h-4 text-[#10B981]" />
            <span>Score: {complianceScore}%</span>
          </div>
        </div>
      </div>

      {/* ── Governance Metrics Ribbon (Curved Glass Cards) ──────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-2 hover:border-[#E5252A]/40 transition-all">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-[10px] uppercase font-bold tracking-wider">Active Rules</span>
            <Lock className="w-3.5 h-3.5 text-[#E5252A]" />
          </div>
          <div className="text-3xl font-extrabold text-white">{activePolicies.length} / {policies.length}</div>
          <div className="text-[10px] text-[#10B981] font-bold">100% Zero-Trust Enforced</div>
        </div>

        <div className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-2 hover:border-white/30 transition-all">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-[10px] uppercase font-bold tracking-wider">Total Enforced</span>
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="text-3xl font-extrabold text-white">{totalEnforced.toLocaleString()}</div>
          <div className="text-[10px] text-neutral-400">Tool calls audited</div>
        </div>

        <div className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-2 hover:border-[#E5252A]/40 transition-all">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-[10px] uppercase font-bold tracking-wider">Blocked Threats</span>
            <ShieldAlert className="w-3.5 h-3.5 text-[#E5252A]" />
          </div>
          <div className="text-3xl font-extrabold text-[#E5252A]">{blockedThreats}</div>
          <div className="text-[10px] text-[#E5252A] font-bold">Threats intercepted</div>
        </div>

        <div className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl space-y-2 hover:border-[#FBBF24]/40 transition-all">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-[10px] uppercase font-bold tracking-wider">QI Cache Ratio</span>
            <Zap className="w-3.5 h-3.5 text-[#FBBF24]" />
          </div>
          <div className="text-3xl font-extrabold text-white">{cacheMetrics.hit_rate_pct}%</div>
          <div className="text-[10px] text-[#10B981] font-bold">{formatCurrency(cacheMetrics.cost_saved_usd)} saved</div>
        </div>
      </div>

      {/* ── Feature Action Cards (Curved Glassmorphism) ────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ASI Scanner Action Card */}
        <Link
          href="/govern/scan"
          className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl hover:border-[#E5252A] transition-all space-y-2.5 group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="w-4 h-4 text-[#E5252A]" />
              <span className="font-bold text-xs text-white uppercase tracking-wider">
                ASI Scanner Suite
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E5252A]/20 text-[#E5252A] font-bold border border-[#E5252A]/30">
              ASI01–ASI10 Active
            </span>
          </div>
          <p className="text-xs text-neutral-300">
            Simulate runtime injection payloads, privilege escalation, and data exfiltration across agent nodes.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-[#E5252A] font-bold pt-1 group-hover:translate-x-1 transition-transform">
            <span>Run Scanner</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </Link>

        {/* Regulatory Frameworks Card */}
        <Link
          href="/govern/compliance"
          className="p-5 rounded-2xl bg-[#22252A]/60 backdrop-blur-xl border border-white/10 shadow-2xl hover:border-[#10B981] transition-all space-y-2.5 group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-[#10B981]" />
              <span className="font-bold text-xs text-white uppercase tracking-wider">
                Regulatory Frameworks
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#10B981]/20 text-[#10B981] font-bold border border-[#10B981]/30">
              SOC2 · HIPAA · GDPR
            </span>
          </div>
          <p className="text-xs text-neutral-300">
            Export continuous certification reports for enterprise security audits and SOC2 Type II compliance.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-[#10B981] font-bold pt-1 group-hover:translate-x-1 transition-transform">
            <span>Inspect Badges</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </Link>
      </div>

      {/* ── Main Split: Active Policies vs Audit Ledger (Curved Panels) ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Policy Rules */}
        <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-6 border border-white/10 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#E5252A]" /> In-Runtime Security Policies
            </h3>
            <Link
              href="/govern/policies"
              className="text-[11px] text-[#E5252A] font-bold hover:underline flex items-center gap-1"
            >
              <span>Edit Policies</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {policies.slice(0, 4).map((pol) => (
              <div
                key={pol.id}
                className="p-3.5 rounded-xl bg-[#181A1D]/80 border border-white/10 flex items-center justify-between text-xs hover:border-[#E5252A]/40 transition-colors"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[10px] px-2 py-0.5 rounded-full bg-[#E5252A]/20 text-[#E5252A] border border-[#E5252A]/30">
                      {pol.code}
                    </span>
                    <span className="font-bold text-white">{pol.name}</span>
                  </div>
                  <p className="text-[10px] text-neutral-400 truncate max-w-sm">
                    {pol.description}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-[10px]">
                  <span
                    className={`font-bold px-2 py-0.5 rounded-full ${
                      pol.severity === "Critical"
                        ? "bg-[#E5252A]/20 text-[#E5252A] border border-[#E5252A]/30"
                        : "bg-[#FBBF24]/20 text-[#FBBF24] border border-[#FBBF24]/30"
                    }`}
                  >
                    {pol.mode}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Immutable Audit Ledger */}
        <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-6 border border-white/10 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#10B981]" /> Cryptographic Audit Ledger
            </h3>
            <Link
              href="/govern/audit"
              className="text-[11px] text-[#E5252A] font-bold hover:underline flex items-center gap-1"
            >
              <span>View Full Ledger</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5 text-xs">
            {recentAudits.slice(0, 4).map((item) => (
              <div
                key={item.id}
                className="p-3.5 rounded-xl bg-[#181A1D]/80 border border-white/10 space-y-1.5 hover:border-white/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">{item.id}</span>
                    <span className="text-[10px] text-neutral-400 truncate max-w-[140px]">
                      {item.agent}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      item.action === "allow" || item.outcome === "ALLOW"
                        ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30"
                        : item.action === "blocked" || item.outcome === "BLOCKED"
                        ? "bg-[#E5252A]/20 text-[#E5252A] border border-[#E5252A]/30"
                        : "bg-[#FBBF24]/20 text-[#FBBF24] border border-[#FBBF24]/30"
                    }`}
                  >
                    {item.action ? item.action.toUpperCase() : item.outcome}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-neutral-400">
                  <span className="truncate max-w-[200px] text-neutral-300">{item.tool_scope || item.action}</span>
                  <span>{item.timestamp}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
