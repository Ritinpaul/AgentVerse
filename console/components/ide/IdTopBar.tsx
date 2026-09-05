"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import WorkspacesRoundedIcon from "@mui/icons-material/WorkspacesRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import ViewSidebarRoundedIcon from "@mui/icons-material/ViewSidebarRounded";
import MemoryRoundedIcon from "@mui/icons-material/MemoryRounded";

interface IdTopBarProps {
  agentId: string;
  agentName: string;
  agentModelLabel?: string;
  userName: string;
  userEmail: string;
  workspaceLabel: string;
  onOpenPalette: () => void;
  onSave: () => void;
  saved: boolean;
  onRun: () => void;
  running: boolean;
  watching: boolean;
  onDeploy: () => void;
  deploying: boolean;
  deployed: boolean;
  explorerOpen: boolean;
  onToggleExplorer: () => void;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
  availableAgents?: Array<{ id: string; name: string; slug: string; status?: string }>;
  onSelectAgent?: (id: string) => void;
}

const WORKSPACES = [
  { id: "nuuvixx-production", label: "nuuvixx-production", tier: "Enterprise" },
  { id: "nuuvixx-staging", label: "nuuvixx-staging", tier: "Staging" },
  { id: "nuuvixx-sandbox", label: "nuuvixx-sandbox", tier: "Sandbox" },
];

export function IdTopBar({
  agentId,
  agentName,
  agentModelLabel,
  userName,
  userEmail,
  workspaceLabel,
  onOpenPalette,
  onSave,
  saved,
  onRun,
  running,
  watching,
  onDeploy,
  deploying,
  deployed,
  explorerOpen,
  onToggleExplorer,
  inspectorOpen,
  onToggleInspector,
  availableAgents,
  onSelectAgent,
}: IdTopBarProps) {
  const [wsOpen, setWsOpen] = useState(false);
  const [wsLabel, setWsLabel] = useState(workspaceLabel);
  const wsRef = useRef<HTMLDivElement>(null);
  const [agentSelectOpen, setAgentSelectOpen] = useState(false);
  const agentSelectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (wsRef.current && !wsRef.current.contains(e.target as Node)) setWsOpen(false);
      if (agentSelectRef.current && !agentSelectRef.current.contains(e.target as Node)) setAgentSelectOpen(false);
    };
    window.addEventListener("mousedown", h);
    return () => window.removeEventListener("mousedown", h);
  }, []);

  return (
    <div className="h-11 shrink-0 bg-[#0A0A0C] border-b border-[#1E1E24] flex items-center justify-between px-2.5 select-none z-30 gap-2">
      {/* ── Left: brand + workspace + breadcrumb ────────────────────────── */}
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onToggleExplorer}
          title="Toggle Explorer (⌃B)"
          className="p-1.5 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
        >
          <ViewSidebarRoundedIcon sx={{ fontSize: 16 }} />
        </button>

        <Link href="/console" className="flex items-center gap-2 pr-1 hover:opacity-80 transition-opacity">
          <img src="/logo.png" alt="AgentVerse" className="w-[18px] h-[18px] object-contain filter brightness-0 invert" />
          <span className="text-[12px] font-bold text-white font-sans tracking-tight hidden md:block">
            AgentVerse <span className="text-[#E5252A]">Studio</span>
          </span>
        </Link>

        {/* Workspace selector */}
        <div className="relative" ref={wsRef}>
          <button
            onClick={() => setWsOpen((v) => !v)}
            className="flex items-center gap-1.5 h-6 px-2 bg-[#121216] border border-[#26262E] rounded-[3px] text-[11px] text-[#C7C7D1] font-mono hover:border-[#3A3A46] transition-colors"
          >
            <WorkspacesRoundedIcon sx={{ fontSize: 12, color: "#8B8B98" }} />
            <span className="truncate max-w-[130px]">{wsLabel}</span>
            <KeyboardArrowDownRoundedIcon sx={{ fontSize: 12, color: "#5C5C6C" }} />
          </button>
          {wsOpen && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-[#111115] border border-[#26262E] rounded-[4px] shadow-xl z-50 py-1">
              <div className="px-2.5 py-1 text-[9px] font-bold uppercase tracking-widest text-[#4d4d5e] font-mono">
                Workspaces
              </div>
              {WORKSPACES.map((w) => (
                <button
                  key={w.id}
                  onClick={() => {
                    setWsLabel(w.label);
                    setWsOpen(false);
                  }}
                  className={cn(
                    "w-full text-left px-2.5 py-1.5 text-[11px] font-mono flex items-center justify-between hover:bg-[#181820] transition-colors",
                    w.label === wsLabel ? "text-white" : "text-[#8B8B98]"
                  )}
                >
                  {w.label}
                  <span className="text-[9px] text-[#5C5C6C]">{w.tier}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Breadcrumb with interactive Agent Switcher */}
        <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono text-[#5C5C6C] min-w-0">
          <span>/</span>
          <Link href="/console" className="text-[#8B8B98] hover:text-white hover:underline transition-colors">
            workspace
          </Link>
          <span>/</span>
          <Link href="/agents" className="text-[#8B8B98] hover:text-white hover:underline transition-colors">
            agents
          </Link>
          <span>/</span>
          <div className="relative" ref={agentSelectRef}>
            <button
              onClick={() => setAgentSelectOpen((v) => !v)}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10 text-white font-semibold hover:text-primary-light transition-colors"
              title="Switch Agent Workspace"
            >
              <span className="truncate max-w-[150px]">{agentName || agentId}</span>
              <KeyboardArrowDownRoundedIcon sx={{ fontSize: 13, color: "#8B8B98" }} />
            </button>
            {agentSelectOpen && availableAgents && availableAgents.length > 0 && (
              <div className="absolute top-full left-0 mt-1.5 w-60 bg-[#111115] border border-[#26262E] rounded-lg shadow-2xl z-50 py-1.5">
                <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-widest text-[#5C5C6C] font-mono border-b border-white/5 mb-1">
                  Active Agent Fleet ({availableAgents.length})
                </div>
                <div className="max-h-56 overflow-y-auto no-scrollbar">
                  {availableAgents.map((ag) => (
                    <button
                      key={ag.slug || ag.id}
                      onClick={() => {
                        setAgentSelectOpen(false);
                        onSelectAgent?.(ag.slug || ag.id);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs font-mono flex items-center justify-between hover:bg-[#181820] transition-colors",
                        (ag.slug === agentId || ag.id === agentId)
                          ? "text-[#38D9A9] font-bold bg-[#14141B]"
                          : "text-neutral-300"
                      )}
                    >
                      <span className="truncate">{ag.name}</span>
                      <span className="text-[10px] text-neutral-500 font-sans ml-2">
                        {ag.slug.replace(/\//g, "-")}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
{/* ── Right: search · model · env · actions · profile ───────── */}
      <div className="flex items-center gap-1.5 min-w-0">
        {/* Command search */}
        <button
          onClick={onOpenPalette}
          className="hidden xl:flex items-center gap-2 h-6 w-52 px-2 bg-[#121216] border border-[#26262E] rounded-[3px] text-[10px] text-[#5C5C6C] font-mono hover:border-[#3A3A46] transition-colors"
        >
          <SearchRoundedIcon sx={{ fontSize: 12 }} />
          <span className="truncate flex-1 text-left">Search agents, files, commands…</span>
          <kbd className="text-[9px] px-1 py-px rounded bg-[#1A1A22] border border-[#26262E]">⌘K</kbd>
        </button>
        <button
          onClick={onOpenPalette}
          className="xl:hidden p-1.5 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
          title="Command Search"
        >
          <SearchRoundedIcon sx={{ fontSize: 16 }} />
        </button>

        {/* Agent Engine Badge (Manifest Model) */}
        {agentModelLabel && (
          <div className="hidden md:flex items-center gap-1.5 h-6 px-2 bg-[#121216] border border-[#26262E] rounded-[3px] text-[11px] font-mono text-[#8B8B98]">
            <MemoryRoundedIcon sx={{ fontSize: 13, color: "#61AFEF" }} />
            <span className="text-white font-medium">{agentModelLabel}</span>
          </div>
        )}

        {/* Save / Run / Deploy */}
        <div className="flex items-center gap-1 border-l border-[#1C1C24] pl-1.5 ml-0.5">
          <button
            onClick={onSave}
            disabled={watching}
            className={cn(
              "flex items-center gap-1 h-6 px-2 border rounded-[3px] text-[10px] font-mono font-semibold transition-all",
              watching
                ? "opacity-30 cursor-not-allowed border-[#26262E] text-[#8B8B98]"
                : saved
                ? "border-[#10B981]/50 bg-[#10B981]/10 text-[#10B981]"
                : "border-[#26262E] bg-[#121216] text-[#A6A6B2] hover:border-[#3A3A46] hover:text-white"
            )}
          >
            {saved ? <CheckRoundedIcon sx={{ fontSize: 12 }} /> : <SaveRoundedIcon sx={{ fontSize: 12 }} />}
            <span>{saved ? "Saved" : "Save"}</span>
          </button>

          <button
            onClick={onRun}
            className={cn(
              "flex items-center gap-1 h-6 px-2 border rounded-[3px] text-[10px] font-mono font-semibold transition-all",
              running
                ? "border-[#E5252A] bg-red-950/40 text-[#E5252A]"
                : "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981] hover:bg-[#10B981]/20"
            )}
          >
            {running ? <StopRoundedIcon sx={{ fontSize: 12 }} /> : <PlayArrowRoundedIcon sx={{ fontSize: 12 }} />}
            <span>{running ? "Stop" : "Run"}</span>
          </button>

          <button
            onClick={onDeploy}
            disabled={deploying}
            className={cn(
              "flex items-center gap-1 h-6 px-2 rounded-[3px] text-[10px] font-mono font-bold uppercase tracking-wider transition-all",
              deployed
                ? "bg-[#10B981] text-white"
                : deploying
                ? "bg-red-950 text-red-400 opacity-70 cursor-not-allowed"
                : "bg-[#E5252A] hover:bg-[#D01E23] text-white shadow-[0_0_10px_rgba(229,37,42,0.3)]"
            )}
          >
            {deployed ? <CheckRoundedIcon sx={{ fontSize: 12 }} /> : <RocketLaunchRoundedIcon sx={{ fontSize: 12 }} />}
            <span>{deployed ? "Deployed!" : deploying ? "Awaiting…" : "Deploy"}</span>
          </button>
        </div>

        {/* Profile & Controls */}
        <div className="flex items-center gap-1.5 border-l border-[#1C1C24] pl-1.5 ml-0.5">
          <button
            onClick={onToggleInspector}
            title="Toggle Inspector"
            className={cn(
              "p-1.5 rounded transition-colors hidden sm:block",
              inspectorOpen ? "text-blue-400" : "text-[#5C5C6C] hover:text-white hover:bg-[#16161D]"
            )}
          >
            <ViewSidebarRoundedIcon sx={{ fontSize: 15, transform: "rotate(180deg)" }} />
          </button>
          <button
            className="flex items-center gap-1.5 h-6 px-1.5 bg-[#121216] border border-[#26262E] rounded-[3px] hover:border-[#3A3A46] transition-colors"
            title={userEmail}
          >
            <span className="w-4 h-4 rounded-full bg-[#E5252A] text-[8px] font-bold text-white flex items-center justify-center">
              {(userName || "A").charAt(0).toUpperCase()}
            </span>
            <span className="hidden md:block max-w-[80px] truncate text-[10px] text-[#A6A6B2] font-sans font-medium">
              {userName || "user"}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}