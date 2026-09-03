"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAgents } from "@/hooks/useAgents";
import { useGovernance, useSystemHealth } from "@/hooks/useGovernance";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import MonitorHeartRoundedIcon from "@mui/icons-material/MonitorHeartRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";

export default function DashboardPage() {
  const { agents, loading } = useAgents();
  const { activePolicies, complianceScore } = useGovernance();
  const health = useSystemHealth();
  const [isRestarting, setIsRestarting] = useState(false);

  const handleRestart = () => {
    setIsRestarting(true);
    setTimeout(() => setIsRestarting(false), 1200);
  };

  const activeCount = loading ? 0 : agents.length;
  const cpuLoadPct = activeCount === 0 ? 0 : Math.min(100, Math.round(activeCount * 18.5));
  const memoryAllocPct = activeCount === 0 ? 0 : Math.min(100, Math.round(activeCount * 22.0));

  return (
    <div className="space-y-6 font-mono text-white">
      
      {/* ── 1. KERNEL STATUS BANNER (Glassmorphism + Curved Edges) ────────── */}
      <div className="bg-[#22252A]/60 backdrop-blur-xl text-white p-4 rounded-2xl flex items-center justify-between shadow-2xl border border-white/10">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-[#E5252A] animate-pulse shadow-md shadow-red-500/50" />
          <span className="font-bold text-xs tracking-wider text-white uppercase">KERNEL_STATUS: ONLINE</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#10B981]/20 text-[#10B981] font-bold border border-[#10B981]/30">
            ● {activeCount} MicroVMs
          </span>
        </div>

        <button
          onClick={handleRestart}
          className="px-4 py-1.5 rounded-xl border border-white/20 text-xs font-bold text-white hover:border-[#E5252A] hover:text-[#E5252A] transition-all uppercase flex items-center gap-1.5 bg-white/[0.03] backdrop-blur-md cursor-pointer"
        >
          <RefreshRoundedIcon sx={{ fontSize: 14, color: isRestarting ? "#E5252A" : "white", transform: isRestarting ? "rotate(180deg)" : "none", transition: "transform 0.5s" }} />
          <span>{isRestarting ? "RESTARTING..." : "RESTART KERNEL"}</span>
        </button>
      </div>

      {/* ── 2. TOP METRIC WIDGETS ROW (Curved Glassmorphism Cards) ────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* COMPUTE LOAD CARD */}
        <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-5 border border-white/10 shadow-2xl space-y-4 hover:border-[#E5252A]/40 transition-all">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider">
            <span>COMPUTE LOAD</span>
            <BoltRoundedIcon sx={{ fontSize: 16, color: "#FBBF24" }} />
          </div>

          <div className="space-y-3.5 text-xs">
            {/* CPU (Red) */}
            <div>
              <div className="flex justify-between text-neutral-300 mb-1.5">
                <span className="font-bold">CPU LOAD</span>
                <span className="font-bold text-[#E5252A]">{cpuLoadPct}%</span>
              </div>
              <div className="w-full bg-[#141619] h-2 rounded-full overflow-hidden p-0.5 border border-white/5">
                <div className="bg-[#E5252A] h-full rounded-full shadow-sm shadow-red-500/50 transition-all duration-500" style={{ width: `${cpuLoadPct}%` }} />
              </div>
            </div>

            {/* MEMORY (Yellow/White) */}
            <div>
              <div className="flex justify-between text-neutral-300 mb-1.5">
                <span className="font-bold">MEMORY ALLOCATION</span>
                <span className="font-bold text-[#FBBF24]">{memoryAllocPct}%</span>
              </div>
              <div className="w-full bg-[#141619] h-2 rounded-full overflow-hidden p-0.5 border border-white/5">
                <div className="bg-[#FBBF24] h-full rounded-full shadow-sm shadow-amber-500/50 transition-all duration-500" style={{ width: `${memoryAllocPct}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* ACTIVE AGENTS CARD */}
        <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-5 border border-white/10 shadow-2xl space-y-3 hover:border-[#10B981]/40 transition-all">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider">
            <span>ACTIVE AGENTS</span>
            <SmartToyRoundedIcon sx={{ fontSize: 16, color: "#10B981" }} />
          </div>

          <div className="flex items-baseline gap-3 pt-1">
            <span className="text-4xl font-extrabold text-white">{loading ? "0" : agents.length}</span>
            <span className="text-xs font-bold text-[#10B981] flex items-center gap-0.5">
              LIVE
            </span>
          </div>

          {/* Metric Block bars */}
          <div className="flex items-center gap-2 pt-2">
            <div className="h-3 flex-1 bg-[#141619] rounded-lg border border-white/5" />
            <div className="h-3 flex-1 bg-[#141619] rounded-lg border border-white/5" />
            <div className="h-3 flex-1 bg-[#141619] rounded-lg border border-white/5" />
            <div className="h-3 flex-1 bg-[#141619] rounded-lg border border-white/5" />
            <div className={`h-3 flex-1 rounded-lg border border-white/5 ${agents.length > 0 ? "bg-[#10B981] shadow-md shadow-emerald-600/50" : "bg-[#141619]"}`} />
          </div>
        </div>

        {/* EVENT STREAM CARD */}
        <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-5 border border-white/10 shadow-2xl space-y-3 hover:border-white/20 transition-all">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider border-b border-white/10 pb-2">
            <span>EVENT STREAM</span>
            <span className="text-[10px] text-[#10B981] font-bold">● LIVE</span>
          </div>

          <div className="space-y-2 text-[11px] text-neutral-300">
            <div className="flex items-start gap-2">
              <span className="text-neutral-400">14:32:01</span>
              <span className="text-[#E5252A] font-bold">[SYS]</span>
              <span className="text-white">AgentGovern Kernel operational</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-neutral-400">14:31:55</span>
              <span className="text-[#10B981] font-bold">[OK]</span>
              <span className="text-white">Handshake protocol established</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-neutral-400">14:31:42</span>
              <span className="text-[#FBBF24] font-bold">[WARN]</span>
              <span className="text-white">Kernel v2.4-stable loaded</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-neutral-400">14:30:10</span>
              <span className="text-white font-bold">[LOG]</span>
              <span className="text-white">System check complete. 0 errors.</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── 3. RUNNING AGENTS FLEET (Curved Glassmorphic Panel) ───────────── */}
      <div className="bg-[#22252A]/60 backdrop-blur-xl rounded-2xl p-6 border border-white/10 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <RocketLaunchRoundedIcon sx={{ fontSize: 18, color: "#E5252A" }} />
              <span>Autonomous Agent Fleet</span>
            </h2>
            <p className="text-xs text-neutral-400 mt-0.5">
              Active MicroVM runtime containers orchestrated by AgentGovern Kernel
            </p>
          </div>

          <Link
            href="/build"
            className="px-4 py-2 rounded-xl bg-[#E5252A] hover:bg-[#D91E23] text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-red-950/60 transition-transform active:scale-95 border border-red-400/30"
          >
            <AddRoundedIcon sx={{ fontSize: 16 }} />
            <span>New Agent</span>
          </Link>
        </div>

        {agents.length === 0 ? (
          <div className="py-12 px-6 rounded-2xl bg-[#181A1D]/80 border border-white/10 flex flex-col items-center justify-center gap-3 text-center">
            <RocketLaunchRoundedIcon sx={{ fontSize: 40, color: "#57595B" }} />
            <div>
              <p className="text-sm font-bold text-white">No active agents in your fleet</p>
              <p className="text-xs text-neutral-400 mt-1">You have removed all agents from your registry workspace.</p>
            </div>
            <Link
              href="/build"
              className="mt-3 px-5 py-2.5 rounded-xl bg-[#E5252A] hover:bg-[#D91E23] text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-red-950/60 transition-transform active:scale-95 border border-red-400/30"
            >
              <AddRoundedIcon sx={{ fontSize: 16 }} />
              <span>Deploy New Agent</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {agents.map((agent) => (
              <div key={agent.id} className="p-4 rounded-2xl bg-[#181A1D]/80 border border-white/10 space-y-2.5 hover:border-[#10B981]/50 transition-all group">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-white group-hover:text-[#10B981] transition-colors uppercase truncate max-w-[140px]">
                    {agent.name || agent.id}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30">
                    ACTIVE
                  </span>
                </div>
                <div className="text-[11px] text-neutral-300 line-clamp-2 min-h-[32px]">
                  {agent.description || "Stateful Autonomous AI Agent"}
                </div>
                <div className="pt-2 border-t border-white/5 flex justify-between text-[10px] text-neutral-400 font-mono">
                  <span>CPU: <strong className="text-white">12%</strong></span>
                  <span>Memory: <strong className="text-white">64MB</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
