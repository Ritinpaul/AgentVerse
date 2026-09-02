"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAgents } from "@/hooks/useAgents";
import { apiClient } from "@/lib/api";
import { STARTER_TEMPLATES, getStarterTemplate, fetchTemplatesFromStore, StarterTemplate } from "@/lib/templates";
import {
  StudioSession,
  getStoredSessions,
  saveStoredSession,
  deleteStoredSession,
  touchStoredSession,
  saveStoredAgentFiles,
  checkCanCreateAgent,
  MAX_FREE_AGENTS,
  syncSessionsFromCloud,
  getActiveUserTier,
} from "@/lib/agentPersistence";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";
import GitHubIcon from "@mui/icons-material/GitHub";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import PauseRoundedIcon from "@mui/icons-material/PauseRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";
import WorkspacePremiumRoundedIcon from "@mui/icons-material/WorkspacePremiumRounded";

interface Session {
  id: string;
  name: string;
  branch: string;
  status: "running" | "paused" | "needs-approval" | "idle";
  model: string;
  fallback?: string;
  files: string[];
  plan: { current: number; total: number };
  collaborators: string[];
  pendingApprovals: number;
  lastModified: string;
  lastAction: string;
}

interface GovernAlert {
  id: string;
  agentId: string;
  agentName: string;
  message: string;
  severity: "block" | "warn";
}

const AVAILABLE_MODELS = [
  "claude-3-5-sonnet",
  "gpt-4o",
  "gpt-4o-mini",
  "codex-r1",
  "qwen3-coder",
];

const STARTER_FILE_CONTENTS: Record<string, string> = {
  "agent.yaml": `version: "2.4"
name: finance-analyst-v2
description: "Autonomous financial risk & compliance auditor"
runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
policy:
  max_cost_per_run_usd: 0.25
  require_human_approval: true
  allowed_tools:
    - web_search
    - execute_sql
    - query_ledger`,
  "tools.py": `import os
from nuuvixx.sdk import tool, Context

@tool(name="execute_sql", description="Run query against PostgreSQL read replica")
async def execute_sql(ctx: Context, query: str):
    ctx.logger.info(f"Executing query: {query}")
    # Enforced by GovernOS seccomp filter
    return await ctx.db.fetch_all(query)`,
  "memory.json": `{
  "context_window_tokens": 128000,
  "short_term_memory": [
    "User requested quarterly earnings audit",
    "Verified GAAP compliance rules ASI-01"
  ],
  "decision_ledger_id": "dl_9981a_2026"
}`,
  "triggers.yaml": `triggers:
  - event: webhook.github.push
    action: run_compliance_scan
  - event: cron.daily_0000
    action: generate_financial_report`,
};

const STATUS_CFG = {
  running: {
    label: "RUNNING",
    dot: "bg-emerald-400",
    text: "text-emerald-400 font-bold",
    badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    glow: "border-emerald-500/20 hover:border-emerald-500/40 shadow-md",
  },
  paused: {
    label: "PAUSED",
    dot: "bg-blue-400",
    text: "text-blue-400 font-bold",
    badge: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    glow: "border-blue-500/20 hover:border-blue-500/40 shadow-md",
  },
  "needs-approval": {
    label: "NEEDS YOU",
    dot: "bg-amber-400 animate-pulse",
    text: "text-amber-400 font-bold",
    badge: "bg-amber-500/10 border-amber-500/30 text-amber-300",
    glow: "border-amber-500/25 hover:border-amber-500/50 shadow-md",
  },
  idle: {
    label: "IDLE",
    dot: "bg-neutral-500",
    text: "text-neutral-400 font-bold",
    badge: "bg-neutral-800/40 border-neutral-700/60 text-neutral-400",
    glow: "border-white/10 hover:border-white/20 shadow-md",
  },
};

const AVATAR_COLORS = ["bg-emerald-800", "bg-blue-800", "bg-violet-800", "bg-amber-800"];

function Avatar({ letters, color }: { letters: string; color: string }) {
  return (
    <div className={`w-6 h-6 rounded-full ${color} flex items-center justify-center text-[9px] font-bold text-white border border-white/20 shadow-sm`}>
      {letters}
    </div>
  );
}

function PlanBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-1.5 flex-1 rounded-full transition-all ${
            i < current ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" : "bg-[#252832]"
          }`}
        />
      ))}
    </div>
  );
}

export default function AgentStudioPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents } = useAgents();
  const [sessions, setSessions] = useState<Session[]>(() => getStoredSessions());
  const [alerts, setAlerts] = useState<GovernAlert[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTab, setSelectedTab] = useState<"all" | "running" | "needs-approval" | "paused">("all");
  
  // Interactive Modals & Plan Quota
  const [showNew, setShowNew] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [userTier, setUserTier] = useState<"Free" | "Pro" | "Enterprise">("Free");
  const [newName, setNewName] = useState("");
  const [newTemplate, setNewTemplate] = useState("custom");
  const [catalogTemplates, setCatalogTemplates] = useState<StarterTemplate[]>(() => Object.values(STARTER_TEMPLATES));
  const [templateCategory, setTemplateCategory] = useState<string>("all");
  const [selectedCapability, setSelectedCapability] = useState<string | null>(null);
  const [templateSearch, setTemplateSearch] = useState<string>("");
  const [templatesLoading, setTemplatesLoading] = useState<boolean>(false);

  const [previewFile, setPreviewFile] = useState<{ filename: string; content: string } | null>(null);
  const [reviewAlert, setReviewAlert] = useState<GovernAlert | null>(null);

  // Fetch dynamic template catalog with capability tagging
  useEffect(() => {
    let isMounted = true;
    setTemplatesLoading(true);
    fetchTemplatesFromStore()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setCatalogTemplates(data);
        }
      })
      .finally(() => {
        if (isMounted) setTemplatesLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Listen for 1-Click Fork or template selection from URL query parameters
  useEffect(() => {
    const forkSlug = searchParams?.get("fork");
    const forkName = searchParams?.get("name");
    const tplParam = searchParams?.get("template");

    if (forkSlug || tplParam) {
      if (forkName) {
        setNewName(decodeURIComponent(forkName));
      } else if (forkSlug) {
        setNewName(
          forkSlug
            .replace(/[-/]/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase())
        );
      }
      if (tplParam) {
        setNewTemplate(tplParam);
      }
      setShowNew(true);
    }
  }, [searchParams]);

  // Load stored sessions immediately on client mount and sync from cloud
  useEffect(() => {
    setUserTier(getActiveUserTier());
    const stored = getStoredSessions();
    if (stored && stored.length > 0) {
      setSessions(stored);
    }
    // Background cloud sync to merge across devices
    syncSessionsFromCloud().then((cloudSessions) => {
      if (cloudSessions && cloudSessions.length > 0) {
        setSessions(cloudSessions);
      }
    });
  }, []);

  // Pulse alert strip in after 600ms
  const [alertsVisible, setAlertsVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setAlertsVisible(true), 600);
    return () => clearTimeout(t);
  }, []);

  // Sync sessions dynamically from live registered agent fleet while preserving all stored/local sessions
  useEffect(() => {
    if (!agents || agents.length === 0) return;
    setSessions((prev) => {
      const stored = getStoredSessions();
      const sessionMap = new Map<string, Session>();

      // 1. First populate all stored sessions
      for (const s of stored) {
        sessionMap.set(s.id, s);
      }

      // 2. Preserve any in-memory sessions
      for (const s of prev) {
        if (!sessionMap.has(s.id)) {
          sessionMap.set(s.id, s);
        }
      }

      // 3. Integrate fleet agents from backend API
      for (const agent of agents) {
        const sessionId = agent.slug.replace(/\//g, "-");
        if (!sessionMap.has(sessionId)) {
          const fleetSess: Session = {
            id: sessionId,
            name: agent.name,
            branch: `workspace/${sessionId}`,
            status: (agent.status === "active" || agent.status === "running" ? "running" : "idle") as Session["status"],
            model: agent.runtime?.model || "gemini-1.5-flash",
            fallback: agent.runtime?.fallback_model || "gpt-4o-mini",
            files: ["agent.yaml", "tools.py"],
            plan: { current: 3, total: 3 },
            collaborators: [agent.builder ? agent.builder.substring(0, 2).toUpperCase() : "NV"],
            pendingApprovals: 0,
            lastModified: "Synchronized",
            lastAction: "Ready in MicroVM Sandbox",
          };
          sessionMap.set(sessionId, fleetSess);
          saveStoredSession({
            ...fleetSess,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          });
        }
      }

      return Array.from(sessionMap.values());
    });
  }, [agents]);

  // Query real GovernOS pending approvals
  useEffect(() => {
    let active = true;
    apiClient
      .getPendingApprovals()
      .then((approvals) => {
        if (!active) return;
        if (Array.isArray(approvals) && approvals.length > 0) {
          setAlerts(
            approvals.map((app: any) => ({
              id: app.id,
              agentId: app.agent_slug || "agent",
              agentName: app.agent_name || "Agent",
              message: `${app.tool_name || "Execution"} requires approval: ${app.target_resource || app.reason || "Policy threshold reached"}`,
              severity: (app.risk_level === "Critical" ? "block" : "warn") as "block" | "warn",
            }))
          );
        } else {
          setAlerts([]);
        }
      })
      .catch(() => {
        if (active) setAlerts([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const toggleStatus = (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== sessionId) return s;
        const nextStatus = s.status === "running" ? "paused" : "running";
        const updated = {
          ...s,
          status: nextStatus as Session["status"],
          lastAction: `Just now — User ${nextStatus === "running" ? "resumed" : "paused"} MicroVM session`,
        };
        touchStoredSession(sessionId, { status: nextStatus, lastAction: updated.lastAction });
        return updated;
      })
    );
  };

  const changeModel = (sessionId: string, newModel: string, e: React.ChangeEvent<HTMLSelectElement>) => {
    e.stopPropagation();
    const model = e.target.value;
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== sessionId) return s;
        const updated = {
          ...s,
          model,
          lastAction: `Just now — Switched LLM backend to ${model}`,
        };
        touchStoredSession(sessionId, { model, lastAction: updated.lastAction });
        return updated;
      })
    );
  };

  const approveSession = (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== sessionId) return s;
        const updated = {
          ...s,
          status: "running" as const,
          pendingApprovals: 0,
          lastAction: "Just now — GovernOS policy override approved by user",
        };
        touchStoredSession(sessionId, { status: "running", pendingApprovals: 0, lastAction: updated.lastAction });
        return updated;
      })
    );
    setAlerts((prev) => prev.filter((a) => a.agentId !== sessionId));
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    deleteStoredSession(sessionId);
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
  };

  const handleOpenNew = () => {
    const quota = checkCanCreateAgent(sessions);
    if (!quota.allowed) {
      setShowUpgradeModal(true);
      return;
    }
    setShowNew(true);
  };

  const onCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    // Enforce 5-agent limit on Free tier
    const quota = checkCanCreateAgent(sessions);
    if (!quota.allowed) {
      setShowNew(false);
      setShowUpgradeModal(true);
      return;
    }

    const selectedTpl =
      catalogTemplates.find((t) => t.id === newTemplate) ||
      STARTER_TEMPLATES[newTemplate] ||
      STARTER_TEMPLATES.custom;

    const slug = newName.trim().toLowerCase().replace(/\s+/g, "-");
    const tplFiles = selectedTpl.files(newName.trim(), slug);
    const initialFiles = {
      ...STARTER_FILE_CONTENTS,
      ...tplFiles,
    };
    saveStoredAgentFiles(slug, initialFiles);

    const newSess: StudioSession = {
      id: slug,
      name: newName.trim(),
      branch: `session/${slug}`,
      status: "running",
      model: selectedTpl.recommendedModel || "gemini-2.0-flash",
      fallback: selectedTpl.fallbackModel || "gpt-4o-mini",
      templateId: newTemplate,
      files: Object.keys(initialFiles).slice(0, 6),
      plan: { current: 1, total: 5 },
      collaborators: ["DEV"],
      pendingApprovals: 0,
      lastModified: "Just now",
      lastAction: `Just now — Initialized from ${selectedTpl.name} template`,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    saveStoredSession(newSess);
    setSessions((prev) => [newSess, ...prev.filter((s) => s.id !== newSess.id)]);
    setShowNew(false);
    setNewName("");
    router.push(`/build/${slug}?template=${newTemplate}`);
  };

  const handleForkTemplate = (tpl: StarterTemplate) => {
    const quota = checkCanCreateAgent(sessions);
    if (!quota.allowed) {
      setShowNew(false);
      setShowUpgradeModal(true);
      return;
    }
    const defaultName = tpl.name;
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const slug = `${tpl.id}-agent-${randomSuffix}`;
    const tplFiles = tpl.files(defaultName, slug);
    const initialFiles = {
      ...STARTER_FILE_CONTENTS,
      ...tplFiles,
    };
    saveStoredAgentFiles(slug, initialFiles);

    const newSess: StudioSession = {
      id: slug,
      name: `${defaultName} (${randomSuffix})`,
      branch: `session/${slug}`,
      status: "running",
      model: tpl.recommendedModel || "gemini-2.0-flash",
      fallback: tpl.fallbackModel || "gpt-4o-mini",
      templateId: tpl.id,
      files: Object.keys(initialFiles).slice(0, 6),
      plan: { current: 1, total: 5 },
      collaborators: ["DEV"],
      pendingApprovals: 0,
      lastModified: "Just now",
      lastAction: `Just now — 1-Click Forked from ${tpl.name}`,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    saveStoredSession(newSess);
    setSessions((prev) => [newSess, ...prev.filter((s) => s.id !== newSess.id)]);
    setShowNew(false);
    router.push(`/build/${slug}?template=${tpl.id}`);
  };


  const dismissAlert = (id: string) => setAlerts((p) => p.filter((a) => a.id !== id));

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.branch.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.model.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab = selectedTab === "all" || s.status === selectedTab;
    return matchesSearch && matchesTab;
  });

  const runningCount = sessions.filter((s) => s.status === "running").length;
  const approvalsCount = sessions.reduce((a, s) => a + s.pendingApprovals, 0);

  return (
    <div className="min-h-screen bg-[#0E0F14] text-white font-mono flex flex-col space-y-4 p-4 lg:p-6">
      
      {/* ── 1. GLASSMORPHIC TOP NAVBAR ───────────────────────────────────────── */}
      <div className="bg-[#181A24]/90 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/40 text-primary-light flex items-center justify-center shrink-0 shadow-lg shadow-primary/20">
            <CodeRoundedIcon sx={{ fontSize: 22 }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white tracking-wide">
                Agent Studio & MicroVM IDE
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#10B981]/20 text-[#10B981] font-bold border border-[#10B981]/30">
                ● Live Engine
              </span>
            </div>
            <p className="text-xs text-neutral-400 font-sans mt-0.5">
              Interactive session workspace, LLM model routing, and GovernOS policy gates.
            </p>
          </div>
        </div>

        {/* Live Counters & CTA */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end shrink-0">
          <div className="flex items-center gap-4 text-xs bg-[#10111A] px-3.5 py-2 rounded-xl border border-white/10">
            <span className="text-neutral-400">
              SESSIONS: <strong className="text-white">{sessions.length}</strong>
            </span>
            {runningCount > 0 && (
              <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                {runningCount} running
              </span>
            )}
            {approvalsCount > 0 && (
              <span className="flex items-center gap-1.5 text-amber-400 font-bold">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
                {approvalsCount} need review
              </span>
            )}

            {/* Plan Quota Badge */}
            <div className="flex items-center gap-1.5 border-l border-white/10 pl-3">
              <span className="text-neutral-400">PLAN:</span>
              <span className={`px-2 py-0.5 rounded-lg text-[11px] font-bold border ${
                userTier === "Free"
                  ? sessions.length >= MAX_FREE_AGENTS
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : "bg-blue-500/15 text-blue-300 border-blue-500/30"
                  : "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
              }`}>
                {userTier} ({sessions.length}/{userTier === "Free" ? MAX_FREE_AGENTS : "∞"})
              </span>
              {userTier === "Free" && sessions.length >= MAX_FREE_AGENTS && (
                <button
                  onClick={() => setShowUpgradeModal(true)}
                  className="px-2 py-0.5 bg-[#E5252A] hover:bg-[#D01E23] text-white text-[10px] font-bold uppercase tracking-wider rounded transition-all active:scale-95 shadow-sm shadow-[#E5252A]/40"
                >
                  Upgrade
                </button>
              )}
            </div>
          </div>

          <button
            onClick={handleOpenNew}
            className="px-4 py-2 bg-[#E5252A] hover:bg-[#D01E23] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg shadow-[#E5252A]/30 border border-[#F5353A] transition-all active:scale-95 flex items-center gap-1.5 shrink-0"
          >
            <AddRoundedIcon sx={{ fontSize: 16 }} />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* ── 2. GOVERNOS ALERT STRIP (Interactive) ────────────────────────────── */}
      <div
        className={`transition-all duration-500 overflow-hidden ${
          alertsVisible && alerts.length > 0 ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="bg-[#181A24]/90 backdrop-blur-xl border border-white/10 rounded-2xl p-3 space-y-2 shadow-md">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl text-xs font-mono transition-all ${
                a.severity === "block"
                  ? "bg-red-950/25 border border-red-500/25"
                  : "bg-amber-950/25 border border-amber-500/25"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                {a.severity === "block" ? (
                  <ShieldRoundedIcon sx={{ fontSize: 16, color: "#E5252A" }} />
                ) : (
                  <WarningAmberRoundedIcon sx={{ fontSize: 16, color: "#FBBF24" }} />
                )}
                <span className={a.severity === "block" ? "text-red-400 font-bold" : "text-amber-400 font-bold"}>
                  {a.agentName}
                </span>
                <span className="text-neutral-300 truncate">— {a.message}</span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setReviewAlert(a)}
                  className="px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg text-xs font-bold text-white transition-all flex items-center gap-1"
                >
                  <span>Review</span>
                  <ChevronRightRoundedIcon sx={{ fontSize: 14 }} />
                </button>
                <button
                  onClick={() => dismissAlert(a.id)}
                  className="p-1 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
                >
                  <CloseRoundedIcon sx={{ fontSize: 14 }} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 3. SEARCH & FILTER TOOLBAR ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-[#181A24]/60 backdrop-blur-xl border border-white/10 rounded-2xl p-3 shadow-md">
        <div className="relative w-full sm:w-80">
          <SearchRoundedIcon sx={{ fontSize: 18 }} className="text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter sessions by name, branch, or model..."
            className="w-full bg-[#10111A] border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary/60 font-mono"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {(["all", "running", "needs-approval", "paused"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all uppercase font-mono ${
                selectedTab === tab
                  ? "bg-primary/20 text-primary-light border border-primary/40 shadow-sm"
                  : "bg-[#10111A] text-neutral-400 hover:text-white border border-white/5 hover:border-white/20"
              }`}
            >
              {tab === "all" ? `All (${sessions.length})` : tab.replace("-", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* ── 4. SESSIONS GRID (Glowing Dark Grey Cards) ────────────────────────── */}
      <div className="space-y-4">
        <div className="text-xs font-bold text-neutral-400 uppercase tracking-widest font-mono flex items-center gap-2">
          <TuneRoundedIcon sx={{ fontSize: 16, color: "#38D9A9" }} />
          <span>Active MicroVM Build Sessions</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSessions.map((s) => {
            const cfg = STATUS_CFG[s.status];
            return (
              <div
                key={s.id}
                onClick={() => router.push(`/build/${s.id}`)}
                className={`bg-[#181A24]/90 backdrop-blur-xl border rounded-2xl p-5 space-y-4 cursor-pointer transition-all duration-300 group ${cfg.glow}`}
              >
                {/* Header Row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h2 className="text-sm font-bold text-white font-mono truncate group-hover:text-primary-light transition-colors">
                      {s.name}
                    </h2>
                    <div className="flex items-center gap-1.5 text-[11px] text-neutral-400 font-mono mt-1">
                      <GitHubIcon sx={{ fontSize: 13, color: "#9CA3AF" }} />
                      <span className="truncate">{s.branch}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {/* Play/Pause Quick Action */}
                    <button
                      onClick={(e) => toggleStatus(s.id, e)}
                      className="p-1.5 rounded-xl bg-white/5 hover:bg-white/15 border border-white/10 text-neutral-300 hover:text-white transition-all"
                      title={s.status === "running" ? "Pause Session" : "Resume Session"}
                    >
                      {s.status === "running" ? (
                        <PauseRoundedIcon sx={{ fontSize: 16, color: "#38D9A9" }} />
                      ) : (
                        <PlayArrowRoundedIcon sx={{ fontSize: 16, color: "#60A5FA" }} />
                      )}
                    </button>
                    {/* Delete Session Action */}
                    <button
                      onClick={(e) => handleDeleteSession(s.id, e)}
                      className="p-1.5 rounded-xl bg-white/5 hover:bg-red-500/20 border border-white/10 hover:border-red-500/40 text-neutral-400 hover:text-red-400 transition-all"
                      title="Delete MicroVM session"
                    >
                      <DeleteOutlineRoundedIcon sx={{ fontSize: 16 }} />
                    </button>
                  </div>
                </div>

                {/* Status Badge & Pending Approval Actions */}
                <div className="flex items-center justify-between gap-2">
                  <div className={`flex items-center gap-2 text-xs font-mono py-1 px-3 rounded-full border ${cfg.badge}`}>
                    <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                    <span className={cfg.text}>{cfg.label}</span>
                  </div>

                  {s.status === "needs-approval" && (
                    <button
                      onClick={(e) => approveSession(s.id, e)}
                      className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/50 rounded-lg text-[11px] font-bold text-amber-300 transition-all flex items-center gap-1"
                      title="Click to approve pending GovernOS gate"
                    >
                      <CheckCircleRoundedIcon sx={{ fontSize: 13 }} />
                      <span>Quick Approve</span>
                    </button>
                  )}
                </div>

                {/* Plan Execution Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[11px] font-mono text-neutral-400">
                    <span>EXECUTION PLAN</span>
                    <span>Step {s.plan.current} / {s.plan.total}</span>
                  </div>
                  <PlanBar current={s.plan.current} total={s.plan.total} />
                </div>

                {/* Interactive Model Switcher & Fallback */}
                <div className="flex items-center gap-2 flex-wrap text-[11px] font-mono border-t border-white/5 pt-3">
                  <span className="text-neutral-500">MODEL:</span>
                  <div className="relative inline-flex items-center">
                    <select
                      value={s.model}
                      onChange={(e) => changeModel(s.id, s.model, e)}
                      onClick={(e) => e.stopPropagation()}
                      className="appearance-none bg-[#10111A] border border-white/10 hover:border-primary/50 text-neutral-200 text-[11px] pl-2.5 pr-6 py-0.5 rounded-lg font-mono focus:outline-none cursor-pointer transition-colors"
                    >
                      {AVAILABLE_MODELS.map((m) => (
                        <option key={m} value={m} className="bg-[#181A24] text-white">
                          {m}
                        </option>
                      ))}
                    </select>
                    <KeyboardArrowDownRoundedIcon sx={{ fontSize: 15 }} className="pointer-events-none absolute right-1 text-neutral-400" />
                  </div>
                  {s.fallback && (
                    <span className="text-[10px] px-2 py-0.5 bg-[#10111A] border border-white/5 text-neutral-400 rounded-lg">
                      fb: {s.fallback}
                    </span>
                  )}
                </div>

                {/* Interactive File Pills */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {s.files.map((f) => (
                    <button
                      key={f}
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewFile({ filename: f, content: STARTER_FILE_CONTENTS[f] || `# ${f}\n# Verified manifest` });
                      }}
                      className="text-[10px] font-mono text-neutral-300 bg-[#10111A] hover:bg-white/10 border border-white/10 hover:border-white/30 rounded-lg px-2 py-1 flex items-center gap-1 transition-all"
                      title="Click to preview file"
                    >
                      <CodeRoundedIcon sx={{ fontSize: 12, color: "#E5252A" }} />
                      <span>{f}</span>
                    </button>
                  ))}
                </div>

                {/* Last action line */}
                <div className="text-[11px] font-mono text-neutral-400 border-l-2 border-primary/40 pl-2.5 truncate">
                  {s.lastAction}
                </div>

                {/* Collaborators & Timestamp */}
                <div className="flex items-center justify-between pt-2 border-t border-white/5">
                  <div className="flex -space-x-1.5">
                    {s.collaborators.slice(0, 3).map((c, i) => (
                      <Avatar key={i} letters={c} color={AVATAR_COLORS[i % AVATAR_COLORS.length]} />
                    ))}
                  </div>
                  <span className="text-[10px] font-mono text-neutral-500">{s.lastModified}</span>
                </div>
              </div>
            );
          })}

          {/* New Session Dotted Add Card */}
          <button
            onClick={handleOpenNew}
            className="bg-[#181A24]/40 hover:bg-[#181A24]/80 border-2 border-dashed border-white/10 hover:border-primary/50 transition-all duration-300 rounded-2xl flex flex-col items-center justify-center gap-3 p-8 text-neutral-400 hover:text-white group min-h-[260px] shadow-lg"
          >
            <div className="w-12 h-12 rounded-2xl border border-dashed border-white/20 group-hover:border-primary group-hover:bg-primary/10 flex items-center justify-center text-primary-light transition-all">
              <AddRoundedIcon sx={{ fontSize: 24 }} />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold text-white group-hover:text-primary-light font-mono">
                + New MicroVM Session
              </div>
              <div className="text-xs text-neutral-500 mt-1 font-mono">
                Spin up Firecracker sandbox & agent manifest
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* ── 5. DEPLOYED FLEET SECTION ────────────────────────────────────────── */}
      {agents.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-white/10">
          <div className="text-xs font-bold text-neutral-400 uppercase tracking-widest font-mono">
            Deployed Agent Fleet ({agents.length} Registered)
          </div>
          <div className="bg-[#181A24]/90 backdrop-blur-xl border border-white/10 rounded-2xl divide-y divide-white/5 overflow-hidden shadow-xl">
            {agents.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-white/5 transition-colors">
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      a.status === "running" || a.status === "active"
                        ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                        : "bg-neutral-600"
                    }`}
                  />
                  <span className="text-xs font-bold text-white font-mono">{a.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 bg-[#10111A] border border-white/10 text-neutral-400 rounded-lg">
                    {a.slug}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 bg-primary/15 text-primary-light border border-primary/30 rounded-lg">
                    {a.category}
                  </span>
                </div>
                <div className="flex items-center gap-5 text-xs font-mono text-neutral-400">
                  <span>v{a.version}</span>
                  <span className="text-emerald-400 font-bold">Trust {a.trust_score}%</span>
                  <Link href={`/build/${a.slug}`} className="text-primary-light hover:underline font-bold">
                    Open IDE →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 6. DYNAMIC TEMPLATE CATALOG & 1-CLICK FORK MODAL ────────────────── */}
      {showNew && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4"
          onClick={() => setShowNew(false)}
        >
          <div
            className="bg-[#14151F] border border-white/20 rounded-2xl w-full max-w-3xl p-6 space-y-5 shadow-[0_0_60px_rgba(0,0,0,0.85)] max-h-[92vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-white/10 pb-4 shrink-0">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold text-[#E5252A] uppercase tracking-widest font-mono bg-[#E5252A]/10 px-2 py-0.5 rounded border border-[#E5252A]/30">
                    AgentStudio Template Catalog
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Store Synced
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white font-sans tracking-wide">
                  New MicroVM Agent Workspace
                </h2>
                <p className="text-xs text-neutral-400 mt-1 font-sans">
                  Choose a verified template with capability tagging, customize your agent, or 1-Click Fork instantly.
                </p>
              </div>
              <button
                onClick={() => setShowNew(false)}
                className="p-1.5 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
              >
                <CloseRoundedIcon sx={{ fontSize: 20 }} />
              </button>
            </div>

            {/* Custom Name & Config Bar */}
            <form onSubmit={onCreate} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div>
                <label className="text-xs text-neutral-300 font-mono uppercase tracking-wider block mb-1.5">
                  Agent Workspace Name
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Acme Financial Risk Auditor"
                    autoFocus
                    className="flex-1 bg-[#0E0F16] border border-white/15 focus:border-[#E5252A] px-3.5 py-2.5 text-sm text-white outline-none rounded-xl font-mono placeholder-neutral-600 transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!newName.trim()}
                    className="px-5 py-2.5 bg-[#E5252A] hover:bg-[#D01E23] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg shadow-[#E5252A]/30 border border-[#F5353A] transition-all shrink-0"
                  >
                    Launch IDE →
                  </button>
                </div>
                {newName.trim() && (
                  <div className="text-[11px] text-neutral-500 font-mono mt-1">
                    Slug: <span className="text-neutral-300">{newName.trim().toLowerCase().replace(/\s+/g, "-")}</span>
                  </div>
                )}
              </div>

              {/* Template Category Tabs & Search Bar */}
              <div className="space-y-2.5 pt-1">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="text-xs font-mono uppercase tracking-wider text-neutral-300">
                    Select Starter Template ({catalogTemplates.length} Available)
                  </div>
                  {selectedCapability && (
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                      <span>Tag: #{selectedCapability}</span>
                      <button
                        type="button"
                        onClick={() => setSelectedCapability(null)}
                        className="hover:text-white"
                      >
                        ×
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row gap-2">
                  {/* Category Pills */}
                  <div className="flex gap-1.5 overflow-x-auto pb-1 flex-1">
                    {["all", "General", "Finance & FinTech", "Cloud & DevOps", "Security & DevSecOps", "Data & Analytics", "E-Commerce"].map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => {
                          setTemplateCategory(cat);
                          setSelectedCapability(null);
                        }}
                        className={`text-[11px] font-mono px-2.5 py-1 rounded-lg border whitespace-nowrap transition-all ${
                          templateCategory.toLowerCase() === cat.toLowerCase()
                            ? "bg-[#E5252A]/20 text-[#E5252A] border-[#E5252A]/50 font-bold"
                            : "bg-[#10111A] text-neutral-400 border-white/10 hover:border-white/25 hover:text-white"
                        }`}
                      >
                        {cat === "all" ? "All Categories" : cat}
                      </button>
                    ))}
                  </div>

                  {/* Search box */}
                  <div className="relative sm:w-48 shrink-0">
                    <input
                      type="text"
                      value={templateSearch}
                      onChange={(e) => setTemplateSearch(e.target.value)}
                      placeholder="Filter templates..."
                      className="w-full bg-[#0E0F16] border border-white/15 focus:border-[#E5252A] pl-7 pr-3 py-1.5 text-xs text-white outline-none rounded-lg font-mono placeholder-neutral-500"
                    />
                    <SearchRoundedIcon sx={{ fontSize: 16 }} className="absolute left-2 top-2 text-neutral-500" />
                  </div>
                </div>
              </div>

              {/* Template Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                {catalogTemplates
                  .filter((t) => {
                    const matchCat =
                      templateCategory === "all" ||
                      t.category.toLowerCase().includes(templateCategory.toLowerCase());
                    const matchCap =
                      !selectedCapability ||
                      t.capabilities.some((c) =>
                        c.toLowerCase().includes(selectedCapability.toLowerCase())
                      );
                    const matchSearch =
                      !templateSearch ||
                      t.name.toLowerCase().includes(templateSearch.toLowerCase()) ||
                      t.description.toLowerCase().includes(templateSearch.toLowerCase()) ||
                      t.capabilities.some((c) =>
                        c.toLowerCase().includes(templateSearch.toLowerCase())
                      );
                    return matchCat && matchCap && matchSearch;
                  })
                  .map((tpl) => {
                    const isSelected = newTemplate === tpl.id;
                    return (
                      <div
                        key={tpl.id}
                        onClick={() => {
                          setNewTemplate(tpl.id);
                          if (!newName.trim()) {
                            setNewName(tpl.name);
                          }
                        }}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                          isSelected
                            ? "bg-[#1B1D2C] border-[#E5252A] shadow-md shadow-[#E5252A]/10"
                            : "bg-[#10111A] border-white/10 hover:border-white/20 hover:bg-[#161724]"
                        }`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-1.5">
                            <div className="font-bold text-xs text-white font-mono flex items-center gap-1.5">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  isSelected ? "bg-[#E5252A]" : "bg-neutral-600"
                                }`}
                              />
                              {tpl.name}
                            </div>
                            <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-[#E5252A]/15 text-primary-light border border-[#E5252A]/30 shrink-0">
                              {tpl.badge}
                            </span>
                          </div>

                          <p className="text-[11px] text-neutral-400 font-sans line-clamp-2 leading-relaxed mb-2.5">
                            {tpl.description}
                          </p>

                          {/* Capability Tag Pills */}
                          <div className="flex flex-wrap gap-1 mb-3">
                            {tpl.capabilities.slice(0, 4).map((cap) => (
                              <button
                                key={cap}
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedCapability(cap === selectedCapability ? null : cap);
                                }}
                                className={`text-[9px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
                                  selectedCapability === cap
                                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                                    : "bg-white/5 text-neutral-400 border-white/5 hover:border-emerald-400/40 hover:text-emerald-300"
                                }`}
                              >
                                #{cap}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Card Footer with 1-Click Fork CTA */}
                        <div className="flex items-center justify-between border-t border-white/5 pt-2.5 mt-auto">
                          <span className="text-[10px] font-mono text-neutral-500">
                            Model: <span className="text-neutral-300">{tpl.recommendedModel || "gemini-2.0-flash"}</span>
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleForkTemplate(tpl);
                            }}
                            className="text-[10px] font-mono font-bold px-2.5 py-1 bg-white/10 hover:bg-[#E5252A] hover:text-white text-neutral-200 rounded-lg border border-white/15 transition-all flex items-center gap-1"
                          >
                            <RocketLaunchRoundedIcon sx={{ fontSize: 13 }} />
                            1-Click Fork
                          </button>
                        </div>
                      </div>
                    );
                  })}
              </div>

              {/* Bottom Action Footer */}
              <div className="flex gap-3 pt-3 border-t border-white/10 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowNew(false)}
                  className="flex-1 py-2.5 border border-white/15 hover:border-white/30 rounded-xl text-xs font-bold text-neutral-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newName.trim()}
                  className="flex-1 py-2.5 bg-[#E5252A] hover:bg-[#D01E23] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg shadow-[#E5252A]/30 border border-[#F5353A] transition-all"
                >
                  Launch IDE with Selected Template →
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 7. FILE PREVIEW MODAL ────────────────────────────────────────────── */}
      {previewFile && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewFile(null)}
        >
          <div
            className="bg-[#181A24] border border-white/20 rounded-2xl w-full max-w-xl p-6 space-y-4 shadow-[0_0_50px_rgba(0,0,0,0.8)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 text-sm font-mono font-bold text-white">
                <CodeRoundedIcon sx={{ color: "#E5252A" }} />
                <span>{previewFile.filename}</span>
              </div>
              <button
                onClick={() => setPreviewFile(null)}
                className="p-1 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10"
              >
                <CloseRoundedIcon sx={{ fontSize: 16 }} />
              </button>
            </div>

            <pre className="bg-[#10111A] border border-white/10 rounded-xl p-4 text-xs font-mono text-emerald-300 overflow-x-auto max-h-80 leading-relaxed">
              {previewFile.content}
            </pre>

            <div className="flex justify-end">
              <button
                onClick={() => setPreviewFile(null)}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-xs font-bold text-white transition-all"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 8. GOVERNOS REVIEW MODAL ─────────────────────────────────────────── */}
      {reviewAlert && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4"
          onClick={() => setReviewAlert(null)}
        >
          <div
            className="bg-[#181A24] border border-amber-500/40 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-[0_0_50px_rgba(245,158,11,0.2)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 text-sm font-mono font-bold text-amber-400">
                <ShieldRoundedIcon sx={{ color: "#FBBF24" }} />
                <span>GovernOS Sentinel Enforcement</span>
              </div>
              <button onClick={() => setReviewAlert(null)} className="p-1 text-neutral-400 hover:text-white">
                <CloseRoundedIcon sx={{ fontSize: 16 }} />
              </button>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="text-neutral-400">Target Agent: <strong className="text-white">{reviewAlert.agentName}</strong></div>
              <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300">
                {reviewAlert.message}
              </div>
              <p className="text-neutral-400 font-sans leading-relaxed pt-1">
                GovernOS policy gate blocked execution to prevent unauthorized API spending or prompt injection. You may inspect the audit ledger or authorize a manual override below.
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setReviewAlert(null)}
                className="flex-1 py-2.5 border border-white/15 rounded-xl text-xs font-bold text-neutral-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={(e) => {
                  approveSession(reviewAlert.agentId, e);
                  setReviewAlert(null);
                }}
                className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg transition-all"
              >
                Approve Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 9. PLAN LIMIT UPGRADE MODAL ────────────────────────────────────────── */}
      {showUpgradeModal && (
        <div
          className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setShowUpgradeModal(false)}
        >
          <div
            className="bg-[#181A24] border border-[#E5252A]/40 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-[0_0_60px_rgba(229,37,42,0.25)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2.5 text-sm font-mono font-bold text-white">
                <div className="w-7 h-7 rounded-lg bg-[#E5252A]/20 border border-[#E5252A]/50 flex items-center justify-center text-[#E5252A]">
                  <RocketLaunchRoundedIcon sx={{ fontSize: 16 }} />
                </div>
                <span>Free Plan Limit Reached (5/5 Agents)</span>
              </div>
              <button
                onClick={() => setShowUpgradeModal(false)}
                className="p-1 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
              >
                <CloseRoundedIcon sx={{ fontSize: 16 }} />
              </button>
            </div>

            <div className="space-y-3 text-xs font-sans text-neutral-300">
              <p className="leading-relaxed">
                The <strong>Free Plan</strong> allows running up to <strong>5 autonomous MicroVM agents</strong>. You currently have <strong>{sessions.length} agents</strong> active in your workspace.
              </p>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="bg-[#10111A] border border-white/10 rounded-xl p-3 space-y-1.5 font-mono">
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 font-bold">Current: Free</div>
                  <div className="text-white font-bold text-sm">5 Agents Max</div>
                  <div className="text-[11px] text-neutral-400">Shared Sandbox MicroVM</div>
                  <div className="text-[11px] text-neutral-400">Community Support</div>
                </div>
                <div className="bg-gradient-to-b from-[#E5252A]/15 to-[#181A24] border border-[#E5252A]/50 rounded-xl p-3 space-y-1.5 font-mono relative overflow-hidden">
                  <span className="absolute top-2 right-2 text-[9px] px-1.5 py-0.5 rounded bg-[#E5252A] text-white font-bold uppercase">
                    PRO
                  </span>
                  <div className="text-[10px] uppercase tracking-wider text-[#F5353A] font-bold">Upgrade: Pro</div>
                  <div className="text-white font-bold text-sm">Unlimited Agents</div>
                  <div className="text-[11px] text-neutral-300">Dedicated MicroVM vCPU</div>
                  <div className="text-[11px] text-neutral-300">24/7 Custom Policy Triggers</div>
                </div>
              </div>

              <div className="text-[11px] text-neutral-400 bg-white/5 p-3 rounded-xl border border-white/5 leading-relaxed">
                💡 <strong>Need to stay on Free?</strong> You can delete any unused session from your workspace to free up an agent slot.
              </div>
            </div>

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setShowUpgradeModal(false)}
                className="flex-1 py-2.5 border border-white/15 hover:border-white/30 rounded-xl text-xs font-bold text-neutral-300 hover:text-white transition-colors font-mono"
              >
                Manage Existing Agents
              </button>
              <Link
                href="/settings"
                onClick={() => setShowUpgradeModal(false)}
                className="flex-1 py-2.5 bg-[#E5252A] hover:bg-[#D01E23] text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg shadow-[#E5252A]/30 border border-[#F5353A] transition-all flex items-center justify-center gap-1.5 font-mono active:scale-95"
              >
                <WorkspacePremiumRoundedIcon sx={{ fontSize: 16 }} />
                <span>Upgrade to Pro →</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

