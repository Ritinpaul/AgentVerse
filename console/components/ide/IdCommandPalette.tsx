"use client";

import React, { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import MonitorHeartRoundedIcon from "@mui/icons-material/MonitorHeartRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import TimelineRoundedIcon from "@mui/icons-material/TimelineRounded";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";
import KeyboardArrowUpRoundedIcon from "@mui/icons-material/KeyboardArrowUpRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";

export interface PaletteAgent {
  id: string;
  name: string;
  status: "ready" | "running" | "error";
}

export interface PaletteFile {
  path: string;
  name: string;
}

interface IdCommandPaletteProps {
  open: boolean;
  onClose: () => void;
  agents: PaletteAgent[];
  files: PaletteFile[];
  onOpenFile: (path: string) => void;
  onOpenAgent: (id: string) => void;
  onRunAgent: () => void;
  onToggleTerminal: () => void;
  onNavigate: (href: string) => void;
}

interface PaletteEntry {
  id: string;
  label: string;
  group: "RECENT" | "AGENTS" | "COMMANDS" | "FILES";
  icon: React.ElementType;
  hint?: string;
  keywords: string;
  run: () => void;
}
export function IdCommandPalette({
  open,
  onClose,
  agents,
  files,
  onOpenFile,
  onOpenAgent,
  onRunAgent,
  onToggleTerminal,
  onNavigate,
}: IdCommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [sel, setSel] = useState(0);

  const recentAgents = agents.slice(0, 2);

  const buildEntries = useCallback((): PaletteEntry[] => {
    const entries: PaletteEntry[] = [];

    recentAgents.forEach((a) => {
      entries.push({
        id: `recent-${a.id}`,
        label: a.name,
        group: "RECENT",
        icon: SmartToyRoundedIcon,
        hint: a.status,
        keywords: a.name + a.id,
        run: () => onOpenAgent(a.id),
      });
    });

    agents.forEach((a) => {
      entries.push({
        id: `agent-${a.id}`,
        label: a.name,
        group: "AGENTS",
        icon: SmartToyRoundedIcon,
        hint: a.status,
        keywords: a.name + a.id,
        run: () => onOpenAgent(a.id),
      });
    });

    entries.push(
      {
        id: "cmd-run",
        label: "Run Agent",
        group: "COMMANDS",
        icon: PlayArrowRoundedIcon,
        hint: "⏎",
        keywords: "run agent execute start sandbox",
        run: () => {
          onClose();
          onRunAgent();
        },
      },
      {
        id: "cmd-config",
        label: "Edit Agent Config",
        group: "COMMANDS",
        icon: CodeRoundedIcon,
        hint: "agent.yaml",
        keywords: "edit config manifest yaml",
        run: () => {
          onClose();
          onOpenFile("agent.yaml");
        },
      },
      {
        id: "cmd-monitor",
        label: "Open Monitor Dashboard",
        group: "COMMANDS",
        icon: MonitorHeartRoundedIcon,
        hint: "→",
        keywords: "monitor dashboards traces telemetry",
        run: () => onNavigate("/monitor"),
      },
      {
        id: "cmd-policy",
        label: "View Governance Policy",
        group: "COMMANDS",
        icon: VerifiedUserRoundedIcon,
        hint: "govern",
        keywords: "governance policy governos sentinel",
        run: () => onNavigate("/govern/policies"),
      },
      {
        id: "cmd-traces",
        label: "Show Traces",
        group: "COMMANDS",
        icon: TimelineRoundedIcon,
        hint: "→",
        keywords: "traces logs events execution",
        run: () => onNavigate("/monitor"),
      },
      {
        id: "cmd-terminal",
        label: "Toggle Terminal",
        group: "COMMANDS",
        icon: TerminalRoundedIcon,
        hint: "⌃`",
        keywords: "terminal output debug console",
        run: () => {
          onClose();
          onToggleTerminal();
        },
      }
    );

    files.forEach((f) => {
      entries.push({
        id: `file-${f.path}`,
        label: f.path,
        group: "FILES",
        icon: DescriptionRoundedIcon,
        hint: "",
        keywords: f.path + f.name,
        run: () => {
          onClose();
          onOpenFile(f.path);
        },
      });
    });

    return entries;
  }, [recentAgents, agents, files, onClose, onOpenAgent, onRunAgent, onOpenFile, onNavigate, onToggleTerminal]);
const grouped: Record<PaletteEntry["group"], PaletteEntry[]> = {
    RECENT: [],
    AGENTS: [],
    COMMANDS: [],
    FILES: [],
  };

  const q = query.trim().toLowerCase();
  const all = buildEntries().filter((e) => !q || e.keywords.toLowerCase().includes(q));
  all.forEach((e) => grouped[e.group].push(e));

  const flat = all;
  const visibleGroups = (["RECENT", "AGENTS", "COMMANDS", "FILES"] as const).filter((g) => grouped[g].length > 0);

  const executeCurrent = (entries: PaletteEntry[], idx: number) => {
    const entry = entries[idx];
    if (entry) entry.run();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (!open) return;
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSel((s) => Math.min(s + 1, Math.max(0, flat.length - 1)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSel((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      executeCurrent(flat, sel);
    }
  };

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, flat, sel]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSel(0);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] bg-black/60 flex items-start justify-center pt-24 p-4" onMouseDown={onClose}>
      <div
        className="w-full max-w-[600px] bg-[#0E0E12] border border-[#26262E] rounded-[6px] shadow-2xl shadow-black/60 overflow-hidden"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Input bar */}
        <div className="flex items-center gap-3 px-3.5 h-11 border-b border-[#1C1C24] bg-[#111116]">
          <SearchRoundedIcon sx={{ fontSize: 16, color: "#E5252A" }} />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSel(0);
            }}
            placeholder="Search agents, files, traces, commands…"
            className="flex-1 bg-transparent text-[12px] text-[#E6EDF3] placeholder-[#4d4d5e] focus:outline-none font-mono"
          />
          <kbd className="text-[9px] px-1.5 py-0.5 rounded bg-[#1A1A22] border border-[#26262E] text-[#5C5C6C] font-mono">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[360px] overflow-y-auto py-1.5 no-scrollbar">
          {flat.length === 0 && (
            <div className="px-4 py-8 text-center text-[11px] text-[#5C5C6C] font-mono">No results for “{query}”</div>
          )}
          {visibleGroups.map((g) => (
            <div key={g}>
              <div className="px-3.5 py-1 text-[9px] font-bold uppercase tracking-[0.16em] text-[#4d4d5e] font-mono">
                {g}
              </div>
              {grouped[g].map((e) => {
                const idx = flat.indexOf(e);
                const Icon = e.icon;
                const selected = idx === sel;
                return (
                  <button
                    key={e.id}
                    onClick={() => executeCurrent(flat, idx)}
                    onMouseEnter={() => setSel(idx)}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-3.5 py-[6px] text-left transition-colors",
                      selected ? "bg-[#1A1A22] text-white" : "text-[#8B8B98] hover:bg-[#14141A]"
                    )}
                  >
                    <Icon sx={{ fontSize: 14, color: selected ? "#E5252A" : "#5C5C6C" }} />
                    <span className="text-[12px] font-mono truncate flex-1">{e.label}</span>
                    {selected && (
                      <span className="text-[9px] text-[#5C5C6C] font-mono flex items-center gap-0.5">
                        <KeyboardArrowUpRoundedIcon sx={{ fontSize: 10 }} />
                        <KeyboardArrowDownRoundedIcon sx={{ fontSize: 10 }} />
                        <span className="ml-1 text-[#E5252A]">↵</span>
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-3.5 h-8 border-t border-[#1C1C24] bg-[#111116] flex items-center justify-between text-[9px] text-[#5C5C6C] font-mono">
          <span>↑↓ navigate&nbsp;&nbsp;↵ run&nbsp;&nbsp;esc close</span>
          <span className="text-[#E5252A] font-bold">AgentVerse Studio v2.4</span>
        </div>
      </div>
    </div>
  );
}