"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import InputBase from "@mui/material/InputBase";
import Tooltip from "@mui/material/Tooltip";

// MUI Icons
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import ConstructionRoundedIcon from "@mui/icons-material/ConstructionRounded";
import MonitorHeartRoundedIcon from "@mui/icons-material/MonitorHeartRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import StorefrontRoundedIcon from "@mui/icons-material/StorefrontRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import MenuBookRoundedIcon from "@mui/icons-material/MenuBookRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import PaidRoundedIcon from "@mui/icons-material/PaidRounded";
import RadioRoundedIcon from "@mui/icons-material/RadioRounded";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";

interface CommandItem {
  id: string;
  title: string;
  category: "Navigation" | "Action" | "GovernOS" | "Store";
  icon: React.ElementType;
  href: string;
  shortcut?: string;
}

const COMMANDS: CommandItem[] = [
  { id: "nav-overview", title: "Go to Overview Dashboard", category: "Navigation", icon: DashboardRoundedIcon, href: "/" },
  { id: "nav-build", title: "Open AgentStudio Monaco IDE & Canvas", category: "Navigation", icon: ConstructionRoundedIcon, href: "/build" },
  { id: "nav-agents", title: "Browse Fleet Catalog & Agents", category: "Navigation", icon: SmartToyRoundedIcon, href: "/agents" },
  { id: "nav-monitor", title: "View Observability Traces & Live Feed", category: "Navigation", icon: MonitorHeartRoundedIcon, href: "/monitor" },
  { id: "nav-govern", title: "Open GovernOS Sentinel Kernel", category: "Navigation", icon: VerifiedUserRoundedIcon, href: "/govern" },
  { id: "nav-store", title: "Explore AgentStore & A2A Marketplace", category: "Navigation", icon: StorefrontRoundedIcon, href: "/store" },
  { id: "nav-settings", title: "Organization Settings & API Keys", category: "Navigation", icon: SettingsRoundedIcon, href: "/settings" },
  { id: "nav-docs", title: "Architecture & Kernel Documentation", category: "Navigation", icon: MenuBookRoundedIcon, href: "/docs" },
  { id: "act-create-agent", title: "Create New Agent (Monaco IDE)", category: "Action", icon: CodeRoundedIcon, href: "/build", shortcut: "N" },
  { id: "act-hitl-approvals", title: "Review Pending HITL Approvals", category: "GovernOS", icon: VerifiedUserRoundedIcon, href: "/govern/approvals" },
  { id: "act-redteam-scan", title: "Trigger ASI01–ASI10 Red-Team Scan", category: "GovernOS", icon: RadioRoundedIcon, href: "/govern/scan" },
  { id: "act-audit-ledger", title: "Inspect Immutable SHA-256 Audit Ledger", category: "GovernOS", icon: VerifiedUserRoundedIcon, href: "/govern/audit" },
  { id: "act-publish-agent", title: "Publish Agent to Store (80% Cut)", category: "Store", icon: PaidRoundedIcon, href: "/store/publish" },
  { id: "act-creator-revenue", title: "View Creator Revenue & x402 Payouts", category: "Store", icon: PaidRoundedIcon, href: "/store/revenue" },
  { id: "act-a2a-contracts", title: "Inspect A2A Micropayment Escrow", category: "Store", icon: BoltRoundedIcon, href: "/store/a2a" },
];

export function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredCommands = COMMANDS.filter(
    (cmd) =>
      cmd.title.toLowerCase().includes(query.toLowerCase()) ||
      cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onClose();
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filteredCommands.length || 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % (filteredCommands.length || 1));
      } else if (e.key === "Enter" && filteredCommands[selectedIndex]) {
        e.preventDefault();
        router.push(filteredCommands[selectedIndex].href);
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, router, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20 p-4 font-mono">
      <div className="w-full max-w-xl glass-card rounded-xl border border-surface-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-border bg-surface-100/60">
          <SearchRoundedIcon sx={{ fontSize: 16, color: "#34d399", flexShrink: 0 }} />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command, search pages, or jump to tab..."
            className="w-full bg-transparent text-xs text-text-primary placeholder:text-text-dim focus:outline-none font-mono"
          />
          <kbd className="px-1.5 py-0.5 rounded bg-surface-50 border border-surface-border text-[10px] text-text-muted">
            ESC
          </kbd>
        </div>

        {/* Command Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1 text-xs">
          {filteredCommands.length === 0 ? (
            <div className="p-6 text-center text-text-muted text-xs font-sans">
              No matching commands or routes found for <span className="text-text-primary font-mono">"{query}"</span>
            </div>
          ) : (
            filteredCommands.map((cmd, idx) => {
              const Icon = cmd.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={cmd.id}
                  onClick={() => { router.push(cmd.href); onClose(); }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-surface-100 text-text-primary font-bold border border-emerald-500/40"
                      : "text-text-secondary hover:bg-surface-100/50"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon sx={{ fontSize: 14, color: isSelected ? "#34d399" : "#71717a" }} />
                    <span className="truncate">{cmd.title}</span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-text-muted px-1.5 py-0.5 rounded bg-surface-50 border border-surface-border">
                      {cmd.category}
                    </span>
                    {cmd.shortcut && (
                      <kbd className="text-[9px] text-text-dim px-1 rounded bg-surface-50 border border-surface-border">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-surface-200/50 border-t border-surface-border flex items-center justify-between text-[10px] text-text-muted">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>Esc Close</span>
          </div>
          <span className="text-emerald-400 font-bold">AgentVerse v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
