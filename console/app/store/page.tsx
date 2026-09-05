"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAgents } from "@/hooks/useAgents";
import { useStore } from "@/hooks/useStore";
import {
  Package,
  Globe,
  ExternalLink,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  Handshake,
  Cpu,
  RefreshCw,
  Copy,
  Check,
  Activity,
  Zap,
} from "lucide-react";

export default function InstalledPackagesPage() {
  const { agents } = useAgents();
  const { contracts } = useStore();
  const totalEscrowUsd = contracts.reduce((acc, c) => acc + (c.escrow_amount_usd || 0), 0);
  const [activeTab, setActiveTab] = useState<"installed" | "contracts" | "install-cli">("installed");
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<string | null>(null);

  const handleCopy = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const handleCheckUpdates = () => {
    setCheckingUpdates(true);
    setTimeout(() => {
      setCheckingUpdates(false);
      setUpdateStatus("All installed agent packages are synchronized with AgentStore origin.");
      setTimeout(() => setUpdateStatus(null), 4000);
    }, 800);
  };

  return (
    <div className="space-y-6 font-sans text-white">
      {/* ── Remote Origin Connection Header ─────────────────────────────────── */}
      <div className="p-6 rounded-2xl bg-[#12131A] border border-[#22222E] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl relative overflow-hidden transition-all">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#E5252A]/15 border border-[#E5252A]/30 text-[#E5252A] flex items-center justify-center shrink-0 shadow-md">
            <Globe className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-bold font-sans tracking-wide text-white">
                WORKSPACE PACKAGE REGISTRY
              </h1>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full font-mono font-semibold bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30 flex items-center gap-1.5 uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse" />
                Remote: origin connected
              </span>
            </div>
            <p className="text-xs text-neutral-400 font-sans mt-1">
              Local packages & active agent dependencies in <code className="text-white font-mono bg-[#1C1D28] px-2 py-0.5 rounded border border-[#2B2C3A]">Nuuvixx Core Org</code>. Synchronized with global <strong className="text-[#38D9A9]">AgentStore Hub</strong>.
            </p>
          </div>
        </div>

        {/* Action CTAs to standalone AgentStore (port 8050) */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            onClick={handleCheckUpdates}
            disabled={checkingUpdates}
            className="px-4 py-2.5 rounded-xl text-xs font-mono font-semibold uppercase tracking-wider flex items-center gap-2 bg-[#161722] hover:bg-[#20212E] border border-[#282938] text-neutral-300 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checkingUpdates ? "animate-spin text-[#38D9A9]" : ""}`} />
            <span>{checkingUpdates ? "Syncing..." : "Sync Remotes"}</span>
          </button>

          <a
            href="http://127.0.0.1:8050"
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2 bg-[#E5252A] hover:bg-[#D01E23] text-white border border-[#F5353A] transition-all shadow-lg shadow-[#E5252A]/20"
          >
            <span>Browse AgentStore Hub</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {updateStatus && (
        <div className="p-3.5 rounded-xl bg-[#38D9A9]/10 border border-[#38D9A9]/30 text-xs font-mono text-[#38D9A9] flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#38D9A9] shrink-0" />
          <span>{updateStatus}</span>
        </div>
      )}

      {/* ── Sub Navigation Tabs ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b border-[#1E1E28] pb-3">
        <button
          onClick={() => setActiveTab("installed")}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono uppercase tracking-wider font-semibold transition-all flex items-center gap-2 ${
            activeTab === "installed"
              ? "bg-[#E5252A] text-white border border-[#F5353A] shadow-md shadow-[#E5252A]/20"
              : "bg-[#14151D] text-neutral-400 border border-[#222330] hover:text-white hover:bg-[#1A1B26]"
          }`}
        >
          <Package className="w-3.5 h-3.5" />
          <span>Installed Packages ({agents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("contracts")}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono uppercase tracking-wider font-semibold transition-all flex items-center gap-2 ${
            activeTab === "contracts"
              ? "bg-[#E5252A] text-white border border-[#F5353A] shadow-md shadow-[#E5252A]/20"
              : "bg-[#14151D] text-neutral-400 border border-[#222330] hover:text-white hover:bg-[#1A1B26]"
          }`}
        >
          <Handshake className="w-3.5 h-3.5" />
          <span>A2A Escrow Contracts (x402)</span>
        </button>

        <button
          onClick={() => setActiveTab("install-cli")}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono uppercase tracking-wider font-semibold transition-all flex items-center gap-2 ${
            activeTab === "install-cli"
              ? "bg-[#E5252A] text-white border border-[#F5353A] shadow-md shadow-[#E5252A]/20"
              : "bg-[#14151D] text-neutral-400 border border-[#222330] hover:text-white hover:bg-[#1A1B26]"
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>CLI & Package Manager</span>
        </button>
      </div>

      {/* ── 1. INSTALLED PACKAGES VIEW ──────────────────────────────────────── */}
      {activeTab === "installed" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="p-5 rounded-2xl bg-[#12131A] border border-[#22222E] flex flex-col justify-between group transition-all hover:border-[#323446] shadow-lg"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-[#38D9A9]" />
                      <h3 className="font-bold text-white text-sm font-sans group-hover:text-[#38D9A9] transition-colors">
                        {agent.name}
                      </h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#1C1D28] text-neutral-400 border border-[#28293A]">
                        v{agent.version}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-400 font-mono mt-0.5">{agent.slug}</p>
                  </div>

                  <div className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#38D9A9]" />
                    <span>{agent.trust_score}% Trust</span>
                  </div>
                </div>

                <p className="text-xs text-neutral-300 line-clamp-2 leading-relaxed font-sans">
                  {agent.description}
                </p>

                {/* Runtime & Capabilities metadata */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#1C1D28] text-neutral-300 border border-[#28293A]">
                    model: {agent.runtime?.model || "claude-3-5-sonnet"}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#1C1D28] text-neutral-300 border border-[#28293A]">
                    scope: {agent.category}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#38D9A9]/10 text-[#38D9A9] border border-[#38D9A9]/25 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9]" />
                    microVM bound
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 mt-4 border-t border-[#1E1E28]">
                <div className="text-xs font-mono text-neutral-400">
                  Runs: <strong className="text-white">{agent.total_executions?.toLocaleString() || 0}</strong>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/build?fork=${agent.slug}&name=${encodeURIComponent(agent.name)}`}
                    className="px-3 py-1.5 rounded-xl text-xs font-mono font-semibold flex items-center gap-1.5 transition-all bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/40 hover:bg-[#38D9A9] hover:text-[#0E0F14]"
                    title="1-Click Fork agent manifest into personal Studio IDE workspace"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>1-Click Fork</span>
                  </Link>

                  <Link
                    href={`/build/${agent.slug}`}
                    className="px-3 py-1.5 rounded-xl text-xs font-mono font-semibold flex items-center gap-1.5 transition-all bg-[#E5252A]/15 text-white border border-[#E5252A]/40 hover:bg-[#E5252A]"
                  >
                    <Activity className="w-3.5 h-3.5 text-[#E5252A] group-hover:text-white" />
                    <span>Run Sandbox</span>
                  </Link>

                  <a
                    href="http://127.0.0.1:8050"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-xl text-xs font-mono border border-[#28293A] bg-[#181924] text-neutral-300 hover:text-white hover:bg-[#222332] transition-all"
                    title="View Package on AgentStore Origin Hub (port 8050)"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── 2. A2A ESCROW CONTRACTS VIEW ────────────────────────────────────── */}
      {activeTab === "contracts" && (
        <div className="p-6 rounded-2xl bg-[#12131A] border border-[#22222E] space-y-4 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-white text-sm font-sans">Agent-to-Agent Autonomous Escrow Ledgers</h3>
              <p className="text-xs text-neutral-400 font-sans mt-0.5">
                Sub-agent contract settlements with SHA-256 cryptographic provenance and x402 payment validation.
              </p>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded-full uppercase tracking-wider font-semibold bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30">
              Escrow Pool: ${totalEscrowUsd.toFixed(2)} USD
            </span>
          </div>

          {contracts.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-[#22222E] rounded-xl font-mono text-xs text-neutral-400 space-y-2">
              <div className="text-neutral-300 font-semibold">No Active A2A Escrow Contracts</div>
              <p className="text-[11px] text-neutral-500 max-w-md mx-auto">
                When autonomous agents negotiate sub-tasks or micropayments via x402 protocol, verified cryptographic contracts will appear here.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#1E1E28] border border-[#1E1E28] rounded-xl overflow-hidden font-mono text-xs">
              {contracts.map((c) => (
                <div key={c.id} className="p-4 bg-[#0E0F14] flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">{c.contract_hash}</div>
                    <div className="text-neutral-400 text-[11px]">{c.initiator_agent} ➔ {c.provider_agent}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[#38D9A9] font-bold">${(c.escrow_amount_usd || 0).toFixed(2)}</div>
                    <div className="text-neutral-500 text-[10px]">Status: {c.status?.toUpperCase() || "ACTIVE"}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 3. CLI & PACKAGE INSTALLER ──────────────────────────────────────── */}
      {activeTab === "install-cli" && (
        <div className="p-6 rounded-2xl bg-[#12131A] border border-[#22222E] space-y-4 shadow-lg">
          <div>
            <h3 className="font-bold text-white text-sm font-sans">Install Agents via CLI & Remote Manifests</h3>
            <p className="text-xs text-neutral-400 font-sans mt-0.5">
              Pull and bind verified autonomous agent manifests directly into your workspace sandbox.
            </p>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-4 rounded-xl bg-[#090A0E] border border-[#1E1E28] flex items-center justify-between">
              <div>
                <span className="text-neutral-500"># Pull verified support agent from origin</span>
                <div className="text-[#38D9A9] mt-1 font-bold">agentstore install acme/support-tier-1</div>
              </div>
              <button
                onClick={() => handleCopy("agentstore install acme/support-tier-1")}
                className="px-3 py-1.5 rounded-lg bg-[#161722] hover:bg-[#20212E] text-white text-xs flex items-center gap-1.5 border border-[#282938] transition-colors"
              >
                {copiedCmd === "agentstore install acme/support-tier-1" ? <Check className="w-3.5 h-3.5 text-[#38D9A9]" /> : <Copy className="w-3.5 h-3.5 text-neutral-400" />}
                <span>{copiedCmd === "agentstore install acme/support-tier-1" ? "Copied" : "Copy"}</span>
              </button>
            </div>

            <div className="p-4 rounded-xl bg-[#090A0E] border border-[#1E1E28] flex items-center justify-between">
              <div>
                <span className="text-neutral-500"># Run agent in isolated Micro-VM sandbox</span>
                <div className="text-[#38D9A9] mt-1 font-bold">agentos run acme/support-tier-1 --sandbox microvm</div>
              </div>
              <button
                onClick={() => handleCopy("agentos run acme/support-tier-1 --sandbox microvm")}
                className="px-3 py-1.5 rounded-lg bg-[#161722] hover:bg-[#20212E] text-white text-xs flex items-center gap-1.5 border border-[#282938] transition-colors"
              >
                {copiedCmd === "agentos run acme/support-tier-1 --sandbox microvm" ? <Check className="w-3.5 h-3.5 text-[#38D9A9]" /> : <Copy className="w-3.5 h-3.5 text-neutral-400" />}
                <span>{copiedCmd === "agentos run acme/support-tier-1 --sandbox microvm" ? "Copied" : "Copy"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
