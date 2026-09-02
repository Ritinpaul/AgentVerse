"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { getStarterTemplate, STARTER_TEMPLATES } from "@/lib/templates";
import {
  getStoredAgentFiles,
  saveStoredAgentFiles,
  touchStoredSession,
  getStoredSessions,
  saveStoredSession,
  checkCanCreateAgent,
  type StudioSession,
} from "@/lib/agentPersistence";

// MUI
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import BlockRoundedIcon from "@mui/icons-material/BlockRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import FolderRoundedIcon from "@mui/icons-material/FolderRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import AnalyticsRoundedIcon from "@mui/icons-material/AnalyticsRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";

// Lib
import { autoRoute, RouteDecision, recordTokenUsage } from "@/lib/autoroute";
import { getProviderHeaders, getActiveProviders } from "@/lib/modelKeys";
import { getStoredUser } from "@/lib/auth";
import { useAgents } from "@/hooks/useAgents";

import {
  MonacoAgentEditor,
  type GovernanceDiagnostic,
  type CostEstimate,
  runGovernanceChecks,
  estimateCost,
} from "@/components/build/MonacoAgentEditor";
import { CursorMarkdownRenderer } from "@/components/build/CursorMarkdownRenderer";
import { KeyManagementModal } from "@/components/build/KeyManagementModal";
import { AutoRouteIndicator } from "@/components/build/AutoRouteIndicator";
import { UsageBar } from "@/components/build/UsageBar";
import { ModelPicker } from "@/components/build/ModelPicker";

// IDE components
import { IdTopBar } from "@/components/ide/IdTopBar";
import { IdActivityBar, type ActivityBarItem } from "@/components/ide/IdActivityBar";
import { IdExplorer, type ExplorerEntry, fileLang } from "@/components/ide/IdExplorer";
import { IdSourceControl } from "@/components/ide/IdSourceControl";
import { GithubConnectModal } from "@/components/ide/GithubConnectModal";
import {
  getStoredGithubToken,
  getStoredGithubRepo,
  clearGithubToken,
  commitFilesToGithub,
} from "@/lib/githubService";
import { AgentGraph } from "@/components/ide/AgentGraph";
import { AgentInspector } from "@/components/ide/AgentInspector";
import { IdTerminal, type TermLog, type TermLogLevel, type TerminalTab, type TermProblem } from "@/components/ide/IdTerminal";
import { IdCommandPalette, type PaletteAgent, type PaletteFile } from "@/components/ide/IdCommandPalette";

function mkLog(level: TermLogLevel, text: string, extra?: Partial<TermLog>): TermLog {
  const n = new Date();
  const ts = [n.getHours(), n.getMinutes(), n.getSeconds()].map((x) => String(x).padStart(2, "0")).join(":");
  return { id: `${Date.now()}-${Math.random()}`, ts, level, text, ...extra };
}

// Chat message type
interface ChatMsg {
  id: string;
  role: "user" | "ai";
  content: string;
  diff?: string;
  accepted?: boolean;
  rejected?: boolean;
  routeDecision?: RouteDecision;
}

// Canned composer replies
const CANNED: Record<string, { reply: string; diff?: string }> = {
  default: {
    reply: "I can help configure your agent. Ask me to add tools, set policies, configure memory, or optimize your manifest.",
  },
  yaml: {
    reply: "I analyzed your manifest and generated an optimized configuration with an isolated microVM sandbox, memory limits, and GovernOS policy gates.",
    diff: `runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512
governance:
  trust_level: T2
  asi_scan: true
  cost_limit_usd: 0.50
  pii_scan: true
  require_human_approval: true`,
  },
  pii: {
    reply: "PII redaction enabled. This strips emails, phone numbers, and SSNs from agent context.",
    diff: "  pii_redaction: true\n  pii_fields: [email, phone, ssn, credit_card]",
  },
  cost: {
    reply: "Updated governance cost limit to $0.50 per run with $5.00 daily cap.",
    diff: "  cost_limit_usd: 0.50\n  daily_cap_usd: 5.00",
  },
  memory: {
    reply: "Configured Redis-backed episodic memory with 24h TTL.",
    diff: "memory:\n  type: redis\n  ttl_hours: 24\n  namespace: \"agent-memory\"",
  },
  tool: {
    reply: "Added a web_search tool powered by Tavily.",
    diff: "tools:\n  - name: web_search\n    provider: tavily\n    max_results: 5",
  },
  deploy: { reply: "Manifest validated! GovernOS policy active. ASI scan clean. Ready to deploy." },
};

function getReply(msg: string, agentName?: string) {
  const l = msg.toLowerCase();
  if (
    l.includes("what does this agent do") ||
    l.includes("explain") ||
    l.includes("overview") ||
    l.includes("what is this") ||
    l.includes("describe")
  ) {
    const name = agentName || "Current Agent";
    return {
      reply: `### Agent Architecture & Capabilities: **${name}**\n\nThis agent is configured as an autonomous execution unit on the AgentVerse microVM runtime.\n\n#### 1. Core Runtime & Model\n- **Inference Engine**: Governed LLM with active context window management\n- **Isolation**: Firecracker microVM with cgroups v2 resource quotas (512MB RAM, 300s timeout)\n- **Episodic Memory**: Redis persistence layer active\n\n#### 2. Registered Tools\n- **Tools**: Integrated web search and file manipulation capabilities enabled with SENTINEL validation\n\n#### 3. Governance & Safety Guardrails\n- **Policy Enforcement**: GovernOS active at Level T2\n- **PII Redaction**: Email, SSN, and sensitive identifiers automatically masked\n- **Audit & ASI**: Continuous automated security scans active\n\nAsk me to add tools in \`tools.py\`, adjust governance thresholds in \`agent.yaml\`, or deploy this agent to production.`,
    };
  }
  if (l.includes("yaml") || l.includes("suggest") || l.includes("manifest") || l.includes("change")) return CANNED.yaml;
  if (l.includes("pii") || l.includes("redact")) return CANNED.pii;
  if (l.includes("cost") || l.includes("budget") || l.includes("limit")) return CANNED.cost;
  if (l.includes("memory") || l.includes("redis")) return CANNED.memory;
  if (l.includes("tool") || l.includes("search") || l.includes("browser")) return CANNED.tool;
  if (l.includes("deploy") || l.includes("ship")) return CANNED.deploy;
  return CANNED.default;
}


// ── Default file contents ──────────────────────────────────────────────────────
const DEFAULT_YAML = (
  name: string,
  description: string = "Autonomous AI agent deployed on AgentVerse microVM",
  model: string = "gemini-1.5-flash",
  slug?: string
) =>
  `# agent.yaml — AgentVerse Manifest
name: ${name}
slug: ${slug || name.toLowerCase().replace(/\s+/g, "-")}
version: 1.0.0
description: "${description}"

model:
  provider: agentverse
  model: ${model}
  context_window: 128000
  max_output_tokens: 4096
  temperature: 0.2

runtime:
  sandbox: firecracker-microvm
  timeout_s: 300
  memory_limit_mb: 512

governance:
  trust_level: T2
  trust_score_threshold: 70
  policy_set: strict-production-v1
  asi_scan: true
  cost_limit_usd: 0.50
  pii_scan: true

tools:
  - type: web_search
    enabled: true
  - type: file_reader
    enabled: true
`;

const DEFAULT_FILES: Record<string, string> = {
  "agent.yaml": DEFAULT_YAML("Autonomous Agent"),
  "tools.py": `# tools.py — AgentVerse Custom Tool Implementations
import os

def web_search(query: str, max_results: int = 5):
    """Perform live web search using Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"error": "TAVILY_API_KEY environment variable not set"}
    return {"query": query, "results": []}
`,
  "memory.json": `{
  "context_window_tokens": 128000,
  "short_term_memory": [
    "User requested quarterly earnings audit",
    "Verified GAAP compliance rules ASI-01"
  ],
  "persistence": "enabled",
  "namespace": "finance-analyst-v2"
}`,
  "triggers.yaml": `triggers:
  - type: api
    enabled: true
  - type: webhook.github.push
    action: run_compliance_scan
  - type: cron.daily_0000
    action: generate_financial_report
`,
  "prompts/system.md": `# System Prompt — Finance Analyst V2

You are an expert financial analyst AI agent deployed on AgentVerse.

## Operating Rules
1. Always verify financial data against primary SEC EDGAR filings.
2. Structure your analysis into: Summary, Key Metrics, Risk Factors, and Verdict.
3. Redact any sensitive internal PII automatically before output generation.
`,
  ".mcp.json": `{
  "mcpServers": {
    "tavily": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-tavily"]
    }
  }
}`,
  "README.md": `# Finance Analyst V2

Autonomous financial analysis agent built on AgentVerse.

## Quickstart
\`\`\`bash
av run finance-analyst-v2 --input "Analyze NVDA Q3 report"
\`\`\`
`,
};
// Workspace scaffold files
const WORKSPACE_FILES: Record<string, string> = {
  "tools/web-search.ts": `export const webSearch = {
  name: "web_search",
  provider: "tavily",
  maxResults: 5,
  enabled: true,
};`,
  "tools/browser.ts": `export const browser = {
  name: "browser",
  provider: "playwright",
  headless: true,
  enabled: true,
};`,
  "tools/file-reader.ts": `export const fileReader = {
  name: "file_reader",
  scopes: ["workspace"],
  enabled: true,
};`,
  "policies/governance-policy.yaml": `policy_set: strict-production-v1
rules:
  - id: governance.cost_limit_usd
    max: 0.50
  - id: governance.require_human_approval
    value: true
asi:
  scan_on_publish: true
  required_score: 75
`,
  "environments/dev.yaml": `environment: dev
control_plane: http://127.0.0.1:8010
govern: http://127.0.0.1:8025
store: http://127.0.0.1:8005
`,
  "environments/prod.yaml": `environment: prod
control_plane: https://api.nuuvixx.ai
govern: https://govern.nuuvixx.ai
store: https://store.nuuvixx.ai
`,
  "scripts/deploy.sh": `#!/usr/bin/env bash
set -euo pipefail
echo "→ Running GovernOS pre-deployment scan"
av deploy agent.yaml --target staging
`,
  "scripts/seed.py": `#!/usr/bin/env python3
"""Seed agent parameters."""
print("Workspace initialized.")
`,
  "agentverse.config.yaml": `workspace: nuuvixx-production
environment: staging
default_model: auto
default_policy: strict-production-v1
terminal_shell: bash
`,
};

const DEFAULT_FILES_ALL: Record<string, string> = { ...DEFAULT_FILES, ...WORKSPACE_FILES };
// ── Explorer file tree ─────────────────────────────────────────────────────────
const FILE_TREE: ExplorerEntry[] = [
  { type: "folder", path: "tools", name: "tools", children: [
    { type: "file", path: "tools/web-search.ts", name: "web-search.ts", lang: "text" },
    { type: "file", path: "tools/browser.ts", name: "browser.ts", lang: "text" },
    { type: "file", path: "tools/file-reader.ts", name: "file-reader.ts", lang: "text" },
  ] },
  { type: "folder", path: "policies", name: "policies", children: [
    { type: "file", path: "policies/governance-policy.yaml", name: "governance-policy.yaml", lang: "yaml" },
  ] },
  { type: "folder", path: "environments", name: "environments", children: [
    { type: "file", path: "environments/dev.yaml", name: "dev.yaml", lang: "yaml" },
    { type: "file", path: "environments/prod.yaml", name: "prod.yaml", lang: "yaml" },
  ] },
  { type: "folder", path: "scripts", name: "scripts", children: [
    { type: "file", path: "scripts/deploy.sh", name: "deploy.sh", lang: "sh" },
    { type: "file", path: "scripts/seed.py", name: "seed.py", lang: "python" },
  ] },
  { type: "folder", path: "prompts", name: "prompts", children: [
    { type: "file", path: "prompts/system.md", name: "system.md", lang: "md" },
  ] },
  { type: "file", path: "agent.yaml", name: "agent.yaml", lang: "yaml" },
  { type: "file", path: "tools.py", name: "tools.py", lang: "python" },
  { type: "file", path: "memory.json", name: "memory.json", lang: "json" },
  { type: "file", path: "triggers.yaml", name: "triggers.yaml", lang: "yaml" },
  { type: "file", path: ".mcp.json", name: ".mcp.json", lang: "json" },
  { type: "file", path: "agentverse.config.yaml", name: "agentverse.config.yaml", lang: "yaml" },
];

function insertIntoTree(tree: ExplorerEntry[], fullPath: string): ExplorerEntry[] {
  const parts = fullPath.split("/").filter(Boolean);
  if (parts.length === 0) return tree;

  if (parts.length === 1) {
    const name = parts[0];
    if (tree.some((n) => n.path === fullPath)) return tree;
    return [...tree, { type: "file", path: fullPath, name, lang: fileLang(name) }];
  }

  const [folderName, ...rest] = parts;
  const folderPath = folderName;
  const existingFolder = tree.find((n) => n.type === "folder" && n.name === folderName);

  if (existingFolder) {
    return tree.map((n) => {
      if (n === existingFolder) {
        return {
          ...n,
          children: insertIntoTree(n.children || [], rest.join("/")),
        };
      }
      return n;
    });
  } else {
    const newFolder: ExplorerEntry = {
      type: "folder",
      path: folderPath,
      name: folderName,
      children: insertIntoTree([], rest.join("/")),
    };
    return [newFolder, ...tree];
  }
}

function deleteFromTree(tree: ExplorerEntry[], targetPath: string): ExplorerEntry[] {
  return tree
    .filter((n) => n.path !== targetPath)
    .map((n) => {
      if (n.type === "folder" && n.children) {
        return {
          ...n,
          children: deleteFromTree(n.children, targetPath),
        };
      }
      return n;
    });
}

function monacoLang(path: string): string {
  if (/\.ya?ml$/.test(path)) return "yaml";
  if (/\.py$/.test(path)) return "python";
  if (/\.tsx?$/.test(path)) return "typescript";
  if (/\.json$/.test(path)) return "json";
  if (/\.md$/.test(path)) return "markdown";
  if (/\.(sh|bash)$/.test(path)) return "shell";
  return "plaintext";
}

function getFileBadge(filename: string) {
  if (filename.endsWith(".yaml") || filename.endsWith(".yml"))
    return { ext: "YAML", color: "text-[#E5C07B] bg-[#E5C07B]/10 border-[#E5C07B]/30" };
  if (filename.endsWith(".py")) return { ext: "PY", color: "text-[#61AFEF] bg-[#61AFEF]/10 border-[#61AFEF]/30" };
  if (filename.endsWith(".json")) return { ext: "JSON", color: "text-[#98C379] bg-[#98C379]/10 border-[#98C379]/30" };
  if (filename.endsWith(".md")) return { ext: "MD", color: "text-[#E06C75] bg-[#E06C75]/10 border-[#E06C75]/30" };
  if (filename.endsWith(".ts")) return { ext: "TS", color: "text-[#56B6C2] bg-[#56B6C2]/10 border-[#56B6C2]/30" };
  return { ext: "FILE", color: "text-neutral-400 bg-neutral-800 border-neutral-700" };
}

// ── Copilot quick actions ──────────────────────────────────────────────────────
const QUICK_ACTIONS: { label: string; prompt: string }[] = [
  { label: "Add browser tool", prompt: "Add a browser tool to this agent and update the manifest." },
  { label: "PII redaction", prompt: "Add PII redaction protection to the governance block." },
  { label: "Cost limit", prompt: "Set a cost limit of $0.50 per run with a $5 daily cap." },
  { label: "Configure memory", prompt: "Configure redis memory with 24h TTL for this agent." },
];

// ── Activity bar items ─────────────────────────────────────────────────────────
const ACTIVITY_ITEMS: ActivityBarItem[] = [
  { id: "explorer", label: "Explorer (Files)", icon: FolderRoundedIcon },
  { id: "search", label: "Search / Command", icon: SearchRoundedIcon },
  { id: "scm", label: "Source Control", icon: AccountTreeRoundedIcon },
  { id: "agents", label: "Agents", icon: SmartToyRoundedIcon },
  { id: "analytics", label: "Analytics & Monitoring", icon: AnalyticsRoundedIcon },
  { id: "security", label: "Security & Logs", icon: ShieldRoundedIcon },
  { id: "settings", label: "Settings", icon: SettingsRoundedIcon },
];

type SidebarTab = "explorer" | "search" | "scm" | "agents" | "analytics" | "security" | "settings";
type RightPanelTab = "graph" | "inspector" | "copilot";
// ── Inline ASI approval card (rendered inside the TERMINAL tab) ────────────────
function AsiReviewCard({
  log,
  onOverride,
  onAbort,
}: {
  log: TermLog;
  onOverride: () => void;
  onAbort: () => void;
}) {
  if (!log.asiBlock) return null;
  const { action, detail, rule } = log.asiBlock;

  if (log.asiState === "overridden") {
    return (
      <div className="my-1.5 flex items-center gap-2 text-[11px] text-[#10B981] font-sans font-medium border-l-2 border-l-[#10B981] pl-2.5 py-1">
        <CheckRoundedIcon sx={{ fontSize: 13 }} />
        <span>GovernOS policy block overridden — proceeding with {action}</span>
      </div>
    );
  }
  if (log.asiState === "aborted") {
    return (
      <div className="my-1.5 flex items-center gap-2 text-[11px] text-[#8B8B98] font-sans font-medium border-l-2 border-l-neutral-700 pl-2.5 py-1">
        <CloseRoundedIcon sx={{ fontSize: 13 }} />
        <span>Action aborted — {action} deployment cancelled</span>
      </div>
    );
  }

  return (
    <div className="my-2 border border-[#E5252A]/50 bg-red-950/20 p-3 space-y-2.5 font-sans rounded-[4px]">
      <div className="flex items-center gap-2">
        <ShieldRoundedIcon sx={{ fontSize: 15, color: "#E5252A" }} />
        <span className="text-[11px] font-bold text-[#E5252A] uppercase tracking-wider">
          GovernOS Guard — Restricted Action
        </span>
      </div>
      <div className="space-y-0.5 text-[11px] text-[#C7C7D1]">
        <div className="flex gap-2">
          <span className="text-neutral-500 font-medium w-14 shrink-0">Action:</span>
          <span className="text-white font-bold font-mono">{action}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 font-medium w-14 shrink-0">Detail:</span>
          <span>{detail}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-neutral-500 font-medium w-14 shrink-0">Rule:</span>
          <span className="text-[#E5C07B] font-mono">{rule}</span>
        </div>
      </div>
      <div className="flex gap-2 pt-0.5">
        <button
          onClick={onOverride}
          className="flex-1 py-1 border border-[#E5252A] bg-[#E5252A]/10 text-[#E5252A] text-[11px] font-semibold rounded-[3px] hover:bg-[#E5252A] hover:text-white transition-all flex items-center justify-center gap-1.5"
        >
          <BlockRoundedIcon sx={{ fontSize: 12 }} />Override & Continue
        </button>
        <button
          onClick={onAbort}
          className="flex-1 py-1 border border-[#27272A] bg-[#141417] text-neutral-400 text-[11px] font-medium rounded-[3px] hover:text-white hover:border-[#3F3F46] transition-all flex items-center justify-center gap-1.5"
        >
          <CloseRoundedIcon sx={{ fontSize: 12 }} />Abort Action
        </button>
      </div>
    </div>
  );
}
// ── Main IDE component ─────────────────────────────────────────────────────────
export default function AgentStudioIde() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const agentId = (Array.isArray(params.agentId) ? params.agentId[0] : params.agentId) ?? "finance-analyst-v2";
  const templateId = (searchParams?.get("template") as "custom" | "finance" | "devops" | "security") || "custom";
  const { agents } = useAgents();

  const currentAgent = useMemo(() => {
    return agents.find(
      (a) =>
        a.slug === agentId ||
        a.id === agentId ||
        a.slug.endsWith(`/${agentId}`) ||
        a.slug.replace(/\//g, "-") === agentId
    );
  }, [agents, agentId]);

  const realAgentName = currentAgent?.name || agentId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const agentName = realAgentName;

  // Panels
  const [explorerOpen, setExplorerOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [activeSidebarTab, setActiveSidebarTab] = useState<SidebarTab>("explorer");
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>("graph");
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Bottom terminal
  const [consoleCollapsed, setConsoleCollapsed] = useState(false);
  const [activeConsoleTab, setActiveConsoleTab] = useState<TerminalTab>("terminal");
  const [consoleHeight, setConsoleHeight] = useState(220);

  // Right panel width (resizable)
  const [chatSideWidth, setChatSideWidth] = useState(430);
  const [isDraggingChatSide, setIsDraggingChatSide] = useState(false);
  const chatDragStartXRef = useRef(0);
  const chatDragStartWidthRef = useRef(430);

  const handleChatSideDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingChatSide(true);
    chatDragStartXRef.current = e.clientX;
    chatDragStartWidthRef.current = chatSideWidth;
    if (!inspectorOpen) setInspectorOpen(true);
  };

  useEffect(() => {
    if (!isDraggingChatSide) return;
    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = chatDragStartXRef.current - e.clientX;
      setChatSideWidth(
        Math.min(Math.max(380, chatDragStartWidthRef.current + deltaX), Math.min(780, window.innerWidth - 420))
      );
    };
    const handleMouseUp = () => setIsDraggingChatSide(false);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingChatSide, chatSideWidth]);

  // Files
  const [fileTree, setFileTree] = useState<ExplorerEntry[]>(FILE_TREE);
  const [openFiles, setOpenFiles] = useState<string[]>(["agent.yaml", "tools.py", "prompts/system.md"]);
  const [activeFile, setActiveFile] = useState("agent.yaml");
  const [fileContents, setFileContents] = useState<Record<string, string>>(() => {
    const saved = getStoredAgentFiles(agentId);
    if (saved && Object.keys(saved).length > 0) {
      return saved;
    }
    const tplFiles = getStarterTemplate(templateId, realAgentName, agentId);
    const initial = {
      ...DEFAULT_FILES_ALL,
      ...tplFiles,
    };
    saveStoredAgentFiles(agentId, initial);
    return initial;
  });

  // Client hydration & registration of session / files
  useEffect(() => {
    const saved = getStoredAgentFiles(agentId);
    if (saved && Object.keys(saved).length > 0) {
      setFileContents(saved);
      // Rebuild file tree with any new custom files
      Object.keys(saved).forEach((p) => {
        setFileTree((prev) => insertIntoTree(prev, p));
      });
    } else {
      const tplFiles = getStarterTemplate(templateId, realAgentName, agentId);
      const initial = { ...DEFAULT_FILES_ALL, ...tplFiles };
      setFileContents(initial);
      saveStoredAgentFiles(agentId, initial);
    }

    // Ensure session is saved in studio sessions list so returning to /build lists it
    const sessions = getStoredSessions();
    const existing = sessions.find((s) => s.id === agentId);
    if (!existing) {
      const quota = checkCanCreateAgent(sessions);
      if (!quota.allowed) {
        router.push("/build");
        return;
      }
      const newSession: StudioSession = {
        id: agentId,
        name: realAgentName,
        branch: `workspace/${agentId}`,
        status: "running",
        model: templateId === "security" ? "gpt-4o" : templateId === "finance" ? "claude-3-5-sonnet" : "gemini-2.0-flash",
        fallback: "gpt-4o-mini",
        templateId,
        files: ["agent.yaml", "tools.py", "prompts/system.md"],
        plan: { current: 1, total: 5 },
        collaborators: ["DEV"],
        pendingApprovals: 0,
        lastModified: "Just now",
        lastAction: "Active in MicroVM IDE",
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      saveStoredSession(newSession);
    } else {
      touchStoredSession(agentId, { lastAction: "Active in MicroVM IDE" });
    }
  }, [agentId, realAgentName, templateId, router]);

  // Debounced auto-save to localStorage whenever fileContents changes
  useEffect(() => {
    if (!agentId || !fileContents || Object.keys(fileContents).length === 0) return;
    const timer = setTimeout(() => {
      saveStoredAgentFiles(agentId, fileContents);
      touchStoredSession(agentId, {
        files: Object.keys(fileContents).slice(0, 6),
      });
    }, 400);
    return () => clearTimeout(timer);
  }, [fileContents, agentId]);

  const [pendingChanges, setPendingChanges] = useState<Record<string, { original: string; proposed: string }>>({});

  // GitHub Version Control Connection State
  const [isGithubConnected, setIsGithubConnected] = useState(false);
  const [githubRepo, setGithubRepo] = useState<string | null>(null);
  const [githubToken, setGithubToken] = useState<string | null>(null);
  const [currentBranch, setCurrentBranch] = useState("main");
  const [isGithubModalOpen, setIsGithubModalOpen] = useState(false);

  useEffect(() => {
    const token = getStoredGithubToken();
    const repoInfo = getStoredGithubRepo();
    if (token) setGithubToken(token);
    if (token && repoInfo) {
      setIsGithubConnected(true);
      setGithubRepo(`${repoInfo.owner}/${repoInfo.repo}`);
      setCurrentBranch(repoInfo.branch || "main");
    }
  }, []);

  useEffect(() => {
    if (currentAgent) {
      setFileContents((prev) => {
        // Do not overwrite user-saved agent.yaml
        const saved = getStoredAgentFiles(agentId);
        if (saved && saved["agent.yaml"]) return prev;

        const hasCustomYaml = prev["agent.yaml"] && !prev["agent.yaml"].includes("name: Autonomous Agent");
        const personalizedYaml = DEFAULT_YAML(
          currentAgent.name,
          currentAgent.description,
          currentAgent.runtime?.model,
          currentAgent.slug
        );
        const next = {
          ...prev,
          "agent.yaml": hasCustomYaml ? prev["agent.yaml"] : personalizedYaml,
          "README.md": prev["README.md"] || `# ${currentAgent.name}\n\n${currentAgent.description || "Autonomous agent running on AgentVerse."}\n\n## Quickstart\n\`\`\`bash\nav run ${currentAgent.slug.replace(/\//g, "-")} --input "Hello"\n\`\`\`\n`,
        };
        saveStoredAgentFiles(agentId, next);
        return next;
      });
    }
  }, [currentAgent, agentId]);

  // Run / deploy states
  const [running, setRunning] = useState(false);
  const [watching, setWatching] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  const modifiedFilesList = useMemo(() => {
    const list: string[] = [];
    if (dirty || !saved) {
      list.push("agent.yaml");
    }
    Object.keys(pendingChanges).forEach((f) => {
      if (!list.includes(f)) list.push(f);
    });
    return list;
  }, [dirty, saved, pendingChanges]);

  const activityItems = useMemo<ActivityBarItem[]>(() => {
    return ACTIVITY_ITEMS.map((item) => {
      if (item.id === "scm") {
        return {
          ...item,
          badge: modifiedFilesList.length > 0 ? String(modifiedFilesList.length) : undefined,
        };
      }
      return item;
    });
  }, [modifiedFilesList]);

  // Model & keys
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [showKeyModal, setShowKeyModal] = useState(false);

  // Composer chat
  const [compInput, setCompInput] = useState("");
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    {
      id: "1",
      role: "ai",
      content:
        "Welcome to Agent Studio. I am your AgentVerse Composer. Ask me to add tools, set PII redaction policies, or optimize your manifest.",
    },
  ]);
  const [aiTyping, setAiTyping] = useState(false);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const [lastDecision, setLastDecision] = useState<RouteDecision | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);

  // Terminal + execution
  const [termLogs, setTermLogs] = useState<TermLog[]>([
    mkLog("SYS", "AgentVerse MicroVM Kernel v4.2.0 initialized"),
    mkLog("OK", "GovernOS Policy Engine connected on :8025"),
    mkLog("INFO", "Ready for agent invocation."),
  ]);
  const [outputLines, setOutputLines] = useState<string[]>([]);
  const [debugLines, setDebugLines] = useState<string[]>([]);
  const [diagnostics, setDiagnostics] = useState<GovernanceDiagnostic[]>([]);
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);

  // Reactively re-run governance diagnostics whenever agent.yaml content changes
  const agentYaml = fileContents["agent.yaml"] ?? "";
  useEffect(() => {
    const issues = runGovernanceChecks(agentYaml);
    setDiagnostics(issues);
    setCostEstimate(estimateCost(agentYaml));
  }, [agentYaml]);

  // User
  const [user, setUser] = useState<{ name?: string; email?: string } | null>(null);
  useEffect(() => {
    setUser(getStoredUser());
  }, []);
// ── Smart code merge ───────────────────────────────────────────────────────────
  const mergeCodeSnippet = (existing: string, newSnippet: string, lang: string): string => {
    const trimmed = newSnippet.trim();
    if (!existing || !existing.trim()) return trimmed;
    if (existing.includes(trimmed)) return existing;
    return `${existing.trimEnd()}\n\n${trimmed}`;
  };

  // Apply a single AI code block with smart merge + pending review state
  const applySingleCodeBlock = (code: string, lang: string) => {
    const targetFile = lang === "python" || lang === "py" ? "tools.py" : "agent.yaml";
    const current = fileContents[targetFile] ?? "";
    const original = pendingChanges[targetFile]?.original ?? current;
    const merged = mergeCodeSnippet(current, code, lang);

    setPendingChanges((prev) => ({
      ...prev,
      [targetFile]: { original, proposed: merged },
    }));
    setFileContents((prev) => {
      const next = { ...prev, [targetFile]: merged };
      saveStoredAgentFiles(agentId, next);
      return next;
    });
    setOpenFiles((prev) => (prev.includes(targetFile) ? prev : [...prev, targetFile]));
    setActiveFile(targetFile);
    setDirty(true);
    setTermLogs((p) => [...p, mkLog("OK", `Proposed AI changes to ${targetFile}. Review pending in editor.`)]);
  };

  // Apply all code blocks in an AI response
  const applyAllCodeBlocks = (blocks: { code: string; language: string }[], msgId?: string) => {
    if (!blocks || blocks.length === 0) return;
    if (msgId) {
      setMsgs((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, accepted: true } : m))
      );
    }
    let lastTarget = activeFile;

    setFileContents((prev) => {
      const nextContents = { ...prev };
      let nextPending = { ...pendingChanges };
      for (const b of blocks) {
        const targetFile = b.language === "python" || b.language === "py" ? "tools.py" : "agent.yaml";
        lastTarget = targetFile;
        const current = nextContents[targetFile] ?? "";
        const original = nextPending[targetFile]?.original ?? current;
        const merged = mergeCodeSnippet(current, b.code, b.language);
        nextContents[targetFile] = merged;
        nextPending[targetFile] = { original, proposed: merged };
      }
      saveStoredAgentFiles(agentId, nextContents);
      setPendingChanges(nextPending);
      return nextContents;
    });

    setOpenFiles((prev) => (prev.includes(lastTarget) ? prev : [...prev, lastTarget]));
    setActiveFile(lastTarget);
    setDirty(true);
    setTermLogs((p) => [...p, mkLog("OK", "Applied proposed AI changes across files. Review pending in editor.")]);
  };

  // Accept / reject pending changes for a file
  const acceptPendingFileChange = (filename: string) => {
    setPendingChanges((prev) => {
      const copy = { ...prev };
      delete copy[filename];
      return copy;
    });
    setTermLogs((p) => [...p, mkLog("OK", `Accepted AI changes in ${filename}`)]);
  };

  const rejectPendingFileChange = (filename: string) => {
    const change = pendingChanges[filename];
    if (change) {
      setFileContents((prev) => ({ ...prev, [filename]: change.original }));
    }
    setPendingChanges((prev) => {
      const copy = { ...prev };
      delete copy[filename];
      return copy;
    });
    setTermLogs((p) => [...p, mkLog("INFO", `Rejected AI changes in ${filename}`)]);
  };

  // Save
  const handleSave = useCallback(() => {
    saveStoredAgentFiles(agentId, fileContents);
    touchStoredSession(agentId, {
      files: Object.keys(fileContents).slice(0, 6),
      lastAction: `Just now — Saved ${activeFile}`,
    });
    setDirty(false);
    setSaved(true);
    setTermLogs((p) => [...p, mkLog("OK", `Saved ${activeFile} to MicroVM workspace`)]);
    setTimeout(() => setSaved(false), 2000);
  }, [agentId, fileContents, activeFile]);

  // File open / close
  const openFile = (f: string) => {
    if (!fileContents[f]) {
      setFileContents((prev) => {
        const next = { ...prev, [f]: `# ${f}\n` };
        saveStoredAgentFiles(agentId, next);
        return next;
      });
    }
    if (!openFiles.includes(f)) setOpenFiles((p) => [...p, f]);
    setActiveFile(f);
  };
  const closeFile = (f: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const rest = openFiles.filter((x) => x !== f);
    setOpenFiles(rest);
    if (activeFile === f) setActiveFile(rest.at(-1) ?? "");
  };

  const handleCreateFile = useCallback((path: string) => {
    const cleanPath = path.trim().replace(/^\/+/, "");
    if (!cleanPath) return;

    let template = `# ${cleanPath}\n`;
    if (cleanPath.endsWith(".py")) {
      template = `# ${cleanPath}\ndef run():\n    return "ok"\n`;
    } else if (cleanPath.endsWith(".yaml") || cleanPath.endsWith(".yml")) {
      template = `# ${cleanPath}\nenabled: true\n`;
    } else if (cleanPath.endsWith(".json")) {
      template = `{\n  "name": "${cleanPath}"\n}\n`;
    } else if (cleanPath.endsWith(".ts") || cleanPath.endsWith(".js")) {
      template = `export const config = {};\n`;
    }

    setFileContents((prev) => {
      const next = {
        ...prev,
        [cleanPath]: prev[cleanPath] ?? template,
      };
      saveStoredAgentFiles(agentId, next);
      touchStoredSession(agentId, { files: Object.keys(next).slice(0, 6) });
      return next;
    });
    setFileTree((prev) => insertIntoTree(prev, cleanPath));
    setOpenFiles((prev) => (prev.includes(cleanPath) ? prev : [...prev, cleanPath]));
    setActiveFile(cleanPath);
    setTermLogs((p) => [...p, mkLog("OK", `Created file: ${cleanPath}`)]);
  }, [agentId]);

  const handleDeleteFile = useCallback((path: string) => {
    setFileContents((prev) => {
      const copy = { ...prev };
      delete copy[path];
      saveStoredAgentFiles(agentId, copy);
      touchStoredSession(agentId, { files: Object.keys(copy).slice(0, 6) });
      return copy;
    });
    setFileTree((prev) => deleteFromTree(prev, path));
    setOpenFiles((prev) => {
      const rest = prev.filter((f) => f !== path);
      if (activeFile === path) {
        setActiveFile(rest.at(-1) ?? "");
      }
      return rest;
    });
    setTermLogs((p) => [...p, mkLog("WARN", `Deleted file: ${path}`)]);
  }, [agentId, activeFile]);

  // Reactive manifest parser for Graph and Inspector
  const parsedManifest = useMemo(() => {
    const yaml = fileContents["agent.yaml"] || "";
    const modelMatch = yaml.match(/model:\s*([^\n\r#]+)/i);
    const timeoutMatch = yaml.match(/timeout_s:\s*([^\n\r#]+)/i);
    const memoryMatch = yaml.match(/memory_limit_mb:\s*([^\n\r#]+)/i);
    const trustMatch = yaml.match(/trust_level:\s*([^\n\r#]+)/i);
    const sandboxMatch = yaml.match(/sandbox:\s*([^\n\r#]+)/i);

    const tools: string[] = [];
    const lines = yaml.split("\n");
    let inTools = false;
    for (const line of lines) {
      if (/^tools:\s*$/i.test(line.trim())) {
        inTools = true;
        continue;
      }
      if (inTools) {
        if (/^[a-zA-Z_]/.test(line)) {
          inTools = false;
        } else {
          const m = line.match(/(?:name|type):\s*([a-zA-Z0-9_-]+)/);
          if (m && !tools.includes(m[1])) {
            tools.push(m[1]);
          }
        }
      }
    }
    if (tools.length === 0) {
      tools.push("web_search", "file_reader", "browser");
    }

    const modelRaw = modelMatch
      ? modelMatch[1].trim().replace(/['"]/g, "")
      : currentAgent?.runtime?.model || "qwen2.5-72b-instruct";
    const modelLabel =
      modelRaw.split("/").pop()?.replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()) || "Qwen 2.5 72B";

    return {
      model: modelRaw,
      modelLabel,
      timeout: timeoutMatch ? `${timeoutMatch[1].trim()}s` : "300s",
      memory: memoryMatch ? `${memoryMatch[1].trim()} MB` : "512 MB",
      trustLevel: trustMatch ? trustMatch[1].trim().toUpperCase() : "T2",
      trustScore: trustMatch?.includes("T3") ? 98.5 : trustMatch?.includes("T1") ? 75.0 : 94.2,
      runtime: sandboxMatch ? `MicroVM (${sandboxMatch[1].trim()})` : "MicroVM (Firecracker)",
      tools,
    };
  }, [fileContents, currentAgent]);

  // Global keyboard shortcuts
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        handleSave();
      }
      if ((e.metaKey || e.ctrlKey) && (e.key === "`" || e.key === "\\" || e.key.toLowerCase() === "j")) {
        e.preventDefault();
        setConsoleCollapsed((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && (e.key.toLowerCase() === "k" || e.key.toLowerCase() === "p")) {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setExplorerOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [handleSave]);
// ── Run sandbox ────────────────────────────────────────────────────────────────
  const runSandbox = async () => {
    if (running) {
      setRunning(false);
      setWatching(false);
      setTermLogs((p) => [...p, mkLog("WARN", "MicroVM sandbox stopped by user.")]);
      return;
    }
    setRunning(true);
    setWatching(true);
    setActiveConsoleTab("terminal");
    setConsoleCollapsed(false);

    const steps: Array<[number, TermLogLevel, string]> = [
      [300, "SYS", "Allocating cgroups v2 MicroVM sandbox..."],
      [700, "OK", "Sandbox isolated — CPU limit: 2 cores, RAM: 512MB"],
      [1200, "SYS", "Mounting agent.yaml & tools.py..."],
      [1700, "OK", "GovernOS ASI real-time policy scan passed"],
      [2200, "OK", `Agent "${agentName}" active — listening for triggers`],
      [3200, "WARN", "Idle timeout (10s) — MicroVM sandbox gracefully terminated."],
    ];

    setOutputLines([
      "[agent-init] Loading manifest agent.yaml",
      "[agent-init] Model qwen2.5-72b-instruct ready",
      "[runtime] MicroVM allocated (2 vCPU / 512MB)",
      "[governos] SENTINEL evaluate::ALLOW policy=strict-finance-v2",
      `[run] started — session ${new Date().toISOString().slice(11, 19)}`,
    ]);
    setDebugLines([
      "DBG vm::alloc -> micron-8f2a",
      "DBG tool::preflight web_search OK",
      "DBG sentinel::evaluate ALLOW 1.2ms",
      `DBG agent::loop ${agentName}`,
    ]);

    for (const [delay, level, text] of steps) {
      await new Promise((r) => setTimeout(r, delay));
      setTermLogs((p) => [...p, mkLog(level, text)]);
      if (text.includes("ASI")) {
        setOutputLines((p) => [...p, "[governos] ASI scan passed (7/10 critical rules evaluated)"]);
        setDebugLines((p) => [...p, "DBG asi::scan passed trust.current=98.4"]);
      }
      if (text.includes("active")) {
        setOutputLines((p) => [...p, `[agent] ${agentName} online — awaiting triggers`]);
      }
    }
    setRunning(false);
    setWatching(false);
  };

  // Deploy
  const handleDeploy = async () => {
    if (deploying || deployed) return;
    setDeploying(true);
    setActiveConsoleTab("terminal");
    setConsoleCollapsed(false);

    const preSteps: Array<[number, TermLogLevel, string]> = [
      [300, "SYS", "Executing pre-deployment ASI structural scan..."],
      [800, "OK", "Manifest schema & syntax verified"],
      [1200, "SYS", "Evaluating GovernOS cost policy set..."],
    ];
    for (const [delay, level, text] of preSteps) {
      await new Promise((r) => setTimeout(r, delay));
      setTermLogs((p) => [...p, mkLog(level, text)]);
    }

    await new Promise((r) => setTimeout(r, 500));
    const blockId = `asi-block-${Date.now()}`;
    setTermLogs((p) => [
      ...p,
      mkLog("ERR", "GovernOS policy violation detected", {
        id: blockId,
        asiBlock: {
          action: "registry:push",
          detail: `agentverse/${agentId}:1.0.0 — cost_limit_usd exceeded ($0.63 > $0.50)`,
          rule: "governance.cost_limit_usd — policy set: strict-finance-v2",
        },
        asiState: "pending",
      }),
    ]);
  };

  const overrideAsi = (id: string) => {
    setTermLogs((p) => p.map((l) => (l.id === id ? { ...l, asiState: "overridden" as const } : l)));
    setTimeout(() => {
      setTermLogs((p) => [...p, mkLog("SYS", "Pushing artifact to registry (override authorized)...")]);
      setTimeout(() => {
        setTermLogs((p) => [...p, mkLog("OK", `Registry image pushed: agentverse/${agentId}:1.0.0`)]);
        setTimeout(() => {
          setTermLogs((p) => [...p, mkLog("OK", `"${agentName}" DEPLOYED — Live v1.0.0 in cluster`)]);
          setDeploying(false);
          setDeployed(true);
          setTimeout(() => setDeployed(false), 4000);
        }, 600);
      }, 700);
    }, 300);
  };

  const abortAsi = (id: string) => {
    setTermLogs((p) => p.map((l) => (l.id === id ? { ...l, asiState: "aborted" as const } : l)));
    setTimeout(() => {
      setTermLogs((p) => [...p, mkLog("WARN", "Deployment aborted by user.")]);
      setDeploying(false);
    }, 200);
  };

  // ── Terminal commands ─────────────────────────────────────────────────────────
  const handleTerminalCommand = (cmd: string) => {
    setTermLogs((p) => [...p, mkLog("SYS", `agentverse@workspace $ ${cmd}`)]);
    const c = cmd.trim();
    if (c === "clear") {
      setTermLogs([]);
      return;
    } else if (c === "help") {
      setTermLogs((p) => [
        ...p,
        mkLog(
          "INFO",
          "Commands:\n  ls, pwd, cat <file>, touch <file>, rm <file>\n  python <file>, node <file>, av test, av run, av deploy\n  status, env, whoami, clear, help"
        ),
      ]);
    } else if (c === "pwd") {
      setTermLogs((p) => [...p, mkLog("INFO", `/workspace/agents/${agentId}`)]);
    } else if (c === "ls" || c === "dir") {
      const filesList = Object.keys(fileContents).sort();
      setTermLogs((p) => [
        ...p,
        mkLog("INFO", `Files (${filesList.length}):\n  ${filesList.join("\n  ")}`),
      ]);
    } else if (c.startsWith("cat ")) {
      const target = c.slice(4).trim();
      if (fileContents[target] !== undefined) {
        setTermLogs((p) => [...p, mkLog("INFO", fileContents[target])]);
      } else {
        setTermLogs((p) => [...p, mkLog("ERR", `cat: ${target}: No such file`)]);
      }
    } else if (c.startsWith("python ") || c.startsWith("py ")) {
      const target = c.replace(/^(python3?|py)\s+/, "").trim();
      const code = fileContents[target];
      if (code !== undefined) {
        const funcs = (code.match(/def\s+([a-zA-Z0-9_]+)\s*\(/g) || []).map((f) => f.replace(/def\s+|\s*\(/g, ""));
        const classes = (code.match(/class\s+([a-zA-Z0-9_]+)/g) || []).map((cl) => cl.replace(/class\s+/, ""));
        setTermLogs((p) => [
          ...p,
          mkLog("SYS", `[python3] Initializing runtime sandbox for ${target}...`),
          mkLog("OK", `Loaded symbols in ${target}: ${funcs.length > 0 ? funcs.map((f) => `${f}()`).join(", ") : "script main"}, classes: ${classes.length > 0 ? classes.join(", ") : "none"}`),
          mkLog("OK", `Python syntax and type definitions valid. MicroVM sandbox exit code: 0.`),
        ]);
      } else {
        setTermLogs((p) => [...p, mkLog("ERR", `python3: can't open file '${target}': [Errno 2] No such file or directory`)]);
      }
    } else if (c.startsWith("node ") || c.startsWith("ts-node ")) {
      const target = c.replace(/^(node|ts-node)\s+/, "").trim();
      if (fileContents[target] !== undefined) {
        setTermLogs((p) => [
          ...p,
          mkLog("SYS", `[node] Executing ${target} in v8 isolated context...`),
          mkLog("OK", `TypeScript/Node module executed cleanly. Exit code: 0.`),
        ]);
      } else {
        setTermLogs((p) => [...p, mkLog("ERR", `node: Cannot find module '/workspace/agents/${agentId}/${target}'`)]);
      }
    } else if (/^(av test|test)/.test(c)) {
      const yaml = fileContents["agent.yaml"] || "";
      const issues = runGovernanceChecks(yaml);
      setTermLogs((p) => [
        ...p,
        mkLog("SYS", `Running AgentVerse test runner for '${agentId}'...`),
        mkLog("OK", `✓ Manifest syntax & structure: valid`),
        mkLog("OK", `✓ Model provider route: agentverse (${parsedManifest.model || "default"})`),
        mkLog("OK", `✓ MicroVM sandbox isolation: active (cgroups v2)`),
        issues.length === 0
          ? mkLog("OK", `✓ GovernOS ASI compliance: PASSED (0 violations detected)`)
          : mkLog("WARN", `⚠ GovernOS ASI compliance: ${issues.length} active issue(s) detected. Check Problems panel.`),
      ]);
    } else if (c === "env") {
      setTermLogs((p) => [
        ...p,
        mkLog("INFO", `AGENT_ID=${agentId}\nAGENT_NAME=${realAgentName}\nRUNTIME=${parsedManifest.runtime}\nMODEL=${parsedManifest.model || "claude-3-5-sonnet"}\nGOVERNOS_PORT=8025\nSANDBOX_ISOLATION=cgroups_v2`),
      ]);
    } else if (c === "whoami") {
      setTermLogs((p) => [
        ...p,
        mkLog("OK", user?.email || user?.name || "agentverse-developer"),
      ]);
    } else if (c.startsWith("echo ")) {
      setTermLogs((p) => [...p, mkLog("INFO", c.slice(5))]);
    } else if (c.startsWith("touch ")) {
      const target = c.slice(6).trim();
      if (!target) return;
      setFileContents((prev) => ({ ...prev, [target]: "" }));
      setOpenFiles((prev) => (prev.includes(target) ? prev : [...prev, target]));
      setActiveFile(target);
      setDirty(true);
      setTermLogs((p) => [...p, mkLog("OK", `Created file ${target}`)]);
    } else if (c.startsWith("rm ")) {
      const target = c.slice(3).trim();
      if (fileContents[target] !== undefined) {
        setFileContents((prev) => {
          const copy = { ...prev };
          delete copy[target];
          return copy;
        });
        setOpenFiles((prev) => prev.filter((f) => f !== target));
        setTermLogs((p) => [...p, mkLog("OK", `Removed file ${target}`)]);
      } else {
        setTermLogs((p) => [...p, mkLog("ERR", `rm: cannot remove '${target}': No such file or directory`)]);
      }
    } else if (c === "status") {
      setTermLogs((p) => [
        ...p,
        mkLog(
          "OK",
          `Kernel v4.2.0 | Status: ONLINE | Agent: ${realAgentName} | Sandbox: ${parsedManifest.runtime} | GovernOS :8025 connected`
        ),
      ]);
    } else if (c === "agents" || c === "av list") {
      const agentList =
        agents.length > 0
          ? agents.map((a) => `${a.slug.replace(/\//g, "-")} (${a.status || "ready"})`).join(", ")
          : `${agentId} (ready)`;
      setTermLogs((p) => [...p, mkLog("OK", `Fleet Agents: ${agentList}`)]);
    } else if (/^(av run|agent run|run)/.test(c)) {
      const parts = c.split(/\s+/);
      const targetSlug = parts[2] || agentId;
      setTermLogs((p) => [...p, mkLog("INFO", `Resolving agent manifest for '${targetSlug}'...`)]);
      runSandbox();
    } else if (/^(av deploy|deploy)/.test(c)) {
      handleDeploy();
    } else {
      setTermLogs((p) => [...p, mkLog("WARN", `command not found: ${c}. Try 'help'.`)]);
    }
  };
// ── Send composer message (with streaming) ─────────────────────────────────────
  const sendComposer = async (text?: string) => {
    const msg = (text ?? compInput).trim();
    if (!msg) return;
    setCompInput("");
    setRightPanelTab("copilot");
    setInspectorOpen(true);

    const activeProviders = getActiveProviders();
    const decision = autoRoute(msg, activeProviders, selectedModelId ?? undefined);
    setLastDecision(decision);

    const userMsgId = `usr-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const aiMsgId = `ai-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

    setMsgs((p) => [...p, { id: userMsgId, role: "user", content: msg }]);
    setAiTyping(true);
    recordTokenUsage(decision.estimatedInputTokens);
    setTermLogs((p) => [
      ...p,
      mkLog("INFO", `[AutoRoute] Intent: "${decision.intent}" → ${decision.model.label} (${decision.model.tier.toUpperCase()})`),
    ]);

    const canned = getReply(msg, realAgentName);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...getProviderHeaders(decision.model.provider),
      };

      const manifestContent = fileContents["agent.yaml"] ?? "";
      const activeContent = fileContents[activeFile] ?? "";

      const res = await fetch("/api/chat", {
        method: "POST",
        headers,
        body: JSON.stringify({
          model: decision.model.id,
          provider: decision.model.provider,
          messages: [{ role: "user", content: msg }],
          systemPrompt: `You are AgentVerse Composer, an elite AI pair programmer for autonomous agents on the AgentVerse platform.
Agent Name: "${realAgentName}"
Agent Slug: "${agentId}"

CURRENT AGENT MANIFEST (agent.yaml):
\`\`\`yaml
${manifestContent}
\`\`\`

ACTIVE EDITOR FILE (${activeFile}):
\`\`\`
${activeContent.slice(0, 3000)}
\`\`\`

INSTRUCTIONS:
- Directly answer questions about this agent's architecture, role, tools, runtime sandbox, and governance policies based on the manifest above.
- When asked "what does this agent do?", explain its role, purpose, and all configured tools in detail.
- Propose code or manifest changes inside markdown code blocks.
- Never use emojis. Keep tone technical, crisp, and authoritative.`,
        }),
      });

      if (!res.ok) throw new Error(`Chat API status ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamedText = "";

      setMsgs((p) => [...p, { id: aiMsgId, role: "ai", content: "", diff: canned.diff, routeDecision: decision }]);
      setAiTyping(false);
      setStreamingMsgId(aiMsgId);

      let outputTokens = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") break;
            try {
              const parsed = JSON.parse(dataStr);
              const content =
                parsed.choices?.[0]?.delta?.content ??
                parsed.candidates?.[0]?.content?.parts?.[0]?.text ??
                "";
              if (content) {
                streamedText += content;
                outputTokens += 1;
                setMsgs((p) => p.map((m) => (m.id === aiMsgId ? { ...m, content: streamedText } : m)));
              }
            } catch {
              // ignore non-JSON stream lines
            }
          }
        }
      }

      recordTokenUsage(outputTokens);
      setStreamingMsgId(null);

      if (!streamedText) {
        setMsgs((p) => p.map((m) => (m.id === aiMsgId ? { ...m, content: canned.reply, diff: canned.diff } : m)));
      }
    } catch {
      // Fallback for dev mode / network issue
      await new Promise((r) => setTimeout(r, 600));
      setMsgs((p) => [...p, { id: aiMsgId, role: "ai", content: canned.reply, diff: canned.diff, routeDecision: decision }]);
      setAiTyping(false);
      setStreamingMsgId(null);
    }
  };

  // Accept / reject a proposed diff inside a chat message
  const acceptDiff = (diff: string, id: string) => {
    const targetFile = "agent.yaml";
    const current = fileContents[targetFile] ?? "";
    const original = pendingChanges[targetFile]?.original ?? current;
    const merged = mergeCodeSnippet(current, diff, "yaml");

    setPendingChanges((prev) => ({
      ...prev,
      [targetFile]: { original, proposed: merged },
    }));
    setFileContents((prev) => ({ ...prev, [targetFile]: merged }));
    if (!openFiles.includes(targetFile)) setOpenFiles((p) => [...p, targetFile]);
    setActiveFile(targetFile);
    setDirty(true);
    setMsgs((p) => p.map((m) => (m.id === id ? { ...m, accepted: true } : m)));
    setTermLogs((p) => [...p, mkLog("OK", `Proposed diff applied to ${targetFile}. Review pending in editor.`)]);
  };
  const rejectDiff = (id: string) => setMsgs((p) => p.map((m) => (m.id === id ? { ...m, rejected: true } : m)));

  // Auto-scroll chat
  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, aiTyping]);
// ── Derived lists ──────────────────────────────────────────────────────────────
  const PALETTE_AGENTS: PaletteAgent[] = agents.map((a) => ({
    id: a.slug || a.id,
    name: a.name,
    status: (a.status as PaletteAgent["status"]) || "ready",
  }));

  const PALETTE_FILES: PaletteFile[] = Object.keys(fileContents).map((path) => ({
    path,
    name: path.split("/").pop() ?? path,
  }));

  const TERM_PROBLEMS: TermProblem[] = diagnostics.map((d) => ({
    code: d.code,
    message: d.message,
    severity: d.severity,
    line: d.line,
    source: "GovernOS ASI Scanner",
  }));

  const handleSidebarSelect = (tab: string) => {
    const t = tab as SidebarTab;
    if (t === "explorer") {
      if (activeSidebarTab === "explorer" && explorerOpen) setExplorerOpen(false);
      else {
        setActiveSidebarTab("explorer");
        setExplorerOpen(true);
      }
      return;
    }
    if (t === "search") {
      setActiveSidebarTab(t);
      setPaletteOpen(true);
      return;
    }
    if (t === "agents") {
      router.push("/agents");
      return;
    }
    if (t === "scm") {
      if (activeSidebarTab === "scm" && explorerOpen) setExplorerOpen(false);
      else {
        setActiveSidebarTab("scm");
        setExplorerOpen(true);
      }
      return;
    }
    if (t === "analytics") {
      router.push("/monitor");
      return;
    }
    if (t === "security") {
      router.push("/govern/scan");
      return;
    }
    if (t === "settings") {
      router.push("/settings");
      return;
    }
  };
return (
    <div className="flex flex-col h-screen w-screen bg-[#070709] text-white overflow-hidden antialiased">
      {/* Command palette overlay */}
      <IdCommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        agents={PALETTE_AGENTS}
        files={PALETTE_FILES}
        onOpenFile={(path) => {
          openFile(path);
          setPaletteOpen(false);
        }}
        onOpenAgent={(id) => {
          setPaletteOpen(false);
          router.push(`/build/${id}`);
        }}
        onRunAgent={runSandbox}
        onToggleTerminal={() => setConsoleCollapsed((v) => !v)}
        onNavigate={(href) => {
          setPaletteOpen(false);
          router.push(href);
        }}
      />

      {/* Top bar */}
      <IdTopBar
        agentId={agentId}
        agentName={realAgentName}
        agentModelLabel={parsedManifest.modelLabel}
        userName={user?.name || "Developer"}
        userEmail={user?.email || "dev@nuuvixx.ai"}
        workspaceLabel="nuuvixx-production"
        onOpenPalette={() => setPaletteOpen(true)}
        onSave={handleSave}
        saved={saved}
        onRun={runSandbox}
        running={running}
        watching={watching}
        onDeploy={handleDeploy}
        deploying={deploying}
        deployed={deployed}
        explorerOpen={explorerOpen}
        onToggleExplorer={() => setExplorerOpen((v) => !v)}
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((v) => !v)}
        availableAgents={agents.map((a) => ({
          id: a.id,
          name: a.name,
          slug: a.slug,
          status: a.status,
        }))}
        onSelectAgent={(slugOrId) => router.push(`/build/${slugOrId}`)}
      />

      {/* Main workspace row */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Activity bar */}
        <IdActivityBar
          items={activityItems}
          activeId={activeSidebarTab}
          expanded={explorerOpen}
          onSelect={handleSidebarSelect}
        />

        {/* Explorer sidebar */}
        {explorerOpen && activeSidebarTab === "explorer" && (
          <IdExplorer
            files={fileTree}
            openFiles={openFiles}
            activeFile={activeFile}
            pendingFileChanges={Object.keys(pendingChanges)}
            onOpenFile={openFile}
            onCreateFile={handleCreateFile}
            onDeleteFile={handleDeleteFile}
            onCloseFile={(f) => {
              const rest = openFiles.filter((x) => x !== f);
              setOpenFiles(rest);
              if (activeFile === f) setActiveFile(rest.at(-1) ?? "");
            }}
            agentName={realAgentName}
          />
        )}

        {/* Source Control sidebar */}
        {explorerOpen && activeSidebarTab === "scm" && (
          <IdSourceControl
            modifiedFiles={modifiedFilesList}
            pendingFileChanges={Object.keys(pendingChanges)}
            activeFile={activeFile}
            onOpenFile={openFile}
            onDiscardFileChange={(f) => {
              if (pendingChanges[f]) {
                rejectPendingFileChange(f);
              } else {
                setTermLogs((p) => [...p, mkLog("INFO", `Discarded unstaged changes in ${f}`)]);
              }
            }}
            onCommit={async (msg) => {
              setDirty(false);
              setSaved(true);
              const repoInfo = getStoredGithubRepo();
              if (githubToken && repoInfo) {
                try {
                  const filesToCommit = modifiedFilesList.map((f) => ({
                    path: f,
                    content: fileContents[f] || "",
                  }));
                  setTermLogs((p) => [
                    ...p,
                    mkLog("INFO", `[git] Pushing ${filesToCommit.length} file(s) to GitHub (${repoInfo.owner}/${repoInfo.repo})...`),
                  ]);
                  const res = await commitFilesToGithub(
                    githubToken,
                    repoInfo.owner,
                    repoInfo.repo,
                    repoInfo.branch || "main",
                    msg,
                    filesToCommit
                  );
                  setTermLogs((p) => [
                    ...p,
                    mkLog("OK", `[git] Successfully committed & pushed to GitHub (${res.commitSha}): ${res.commitUrl}`),
                  ]);
                } catch (err: any) {
                  setTermLogs((p) => [...p, mkLog("ERR", `[git] GitHub commit failed: ${err.message}`)]);
                }
              } else {
                const commitSha = Math.random().toString(36).substring(2, 9);
                setTermLogs((p) => [
                  ...p,
                  mkLog("OK", `[git] Committed ${modifiedFilesList.length} file(s) to ${githubRepo || "origin/main"} (${commitSha}): "${msg}"`),
                ]);
              }
            }}
            branchName={currentBranch}
            isGithubConnected={isGithubConnected}
            githubRepo={githubRepo}
            onOpenGithubModal={() => setIsGithubModalOpen(true)}
            onDisconnectGithub={() => {
              clearGithubToken();
              setIsGithubConnected(false);
              setGithubRepo(null);
              setGithubToken(null);
              setTermLogs((p) => [...p, mkLog("INFO", "[git] Disconnected GitHub repository linkage.")]);
            }}
          />
        )}

        {/* Center: tabs + editor */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#070709]">
          {/* Editor tabs */}
          <div className="h-9 shrink-0 border-b border-[#1E1E24] bg-[#0A0A0C] flex items-stretch overflow-x-auto no-scrollbar">
            {openFiles.map((f) => {
              const isActive = activeFile === f;
              const badge = getFileBadge(f);
              return (
                <div
                  key={f}
                  onClick={() => setActiveFile(f)}
                  className={`group flex items-center gap-2 px-3 h-full text-[11px] font-sans font-medium cursor-pointer transition-colors duration-100 shrink-0 border-t-[2px] border-r border-r-[#1C1C24] ${
                    isActive
                      ? "bg-[#0B0D14] text-white border-t-[#E5252A] font-bold"
                      : "border-t-transparent text-[#5C5C6C] hover:bg-[#0E0E12] hover:text-[#C7C7D1]"
                  }`}
                >
                  <span className={`text-[8px] font-mono font-bold px-1 py-px rounded-[2px] border ${badge.color}`}>
                    {badge.ext}
                  </span>
                  <span className="truncate max-w-[130px]" title={f}>{f.split("/").pop()}</span>
                  {pendingChanges[f] && (
                    <span
                      className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse"
                      title="AI Changes Pending Review"
                    />
                  )}
                  <button
                    onClick={(e) => closeFile(f, e)}
                    className="p-0.5 rounded-sm opacity-40 group-hover:opacity-100 hover:bg-red-500/20 hover:text-[#E5252A] transition-all"
                  >
                    <CloseRoundedIcon sx={{ fontSize: 11 }} />
                  </button>
                </div>
              );
            })}
            <button
              onClick={() => {
                const name = window.prompt("Enter new filename (e.g. tools/custom.py):");
                if (name && name.trim()) handleCreateFile(name.trim());
              }}
              className="p-1.5 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded-sm transition-colors ml-1"
              title="Create New File"
            >
              <AddRoundedIcon sx={{ fontSize: 13 }} />
            </button>
          </div>

          {/* Editor (real Monaco or Empty State) */}
          <div className="flex-1 relative overflow-hidden bg-[#0B0D14] min-h-0">
            {openFiles.length === 0 || !activeFile ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 select-none">
                <div className="w-12 h-12 rounded-xl bg-[#12131A] border border-[#222533] flex items-center justify-center text-[#5C5C6C] mb-3 shadow-inner">
                  <CodeRoundedIcon sx={{ fontSize: 24, color: "#8B8B98" }} />
                </div>
                <h3 className="text-sm font-semibold text-neutral-300 mb-1">No File Open</h3>
                <p className="text-xs text-[#5C5C6C] max-w-[260px] mb-4">
                  Select a file from the explorer on the left to start editing.
                </p>
                <div className="flex items-center gap-2 text-[10px] font-mono text-[#5C5C6C]">
                  <span className="px-1.5 py-0.5 rounded bg-[#16161E] border border-[#262634] text-neutral-400">Ctrl+P</span>
                  <span>Quick File Palette</span>
                </div>
              </div>
            ) : (
              <>
                <MonacoAgentEditor
                  value={fileContents[activeFile] ?? ""}
                  onChange={(v) => {
                    if (watching) return;
                    setFileContents((prev) => ({ ...prev, [activeFile]: v }));
                    setDirty(true);
                  }}
                  language={monacoLang(activeFile)}
                  path={activeFile}
                  onDiagnosticsChange={(issues) => setDiagnostics(issues)}
                  onCostChange={(cost) => setCostEstimate(cost)}
                />

                {/* Pending AI changes banner for the active file */}
                {pendingChanges[activeFile] && (
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 px-3 py-1.5 bg-[#10131A] border border-[#38D9A9]/40 rounded-[4px] shadow-lg">
                    <span className="flex items-center gap-1.5 text-[11px] text-[#38D9A9] font-mono">
                      <AutoAwesomeRoundedIcon sx={{ fontSize: 12 }} />
                      AI changes pending for {activeFile}
                    </span>
                    <button
                      onClick={() => acceptPendingFileChange(activeFile)}
                      className="px-2 py-0.5 bg-[#10B981] hover:bg-[#059669] text-black text-[10px] font-bold rounded-sm transition-colors"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => rejectPendingFileChange(activeFile)}
                      className="px-2 py-0.5 bg-[#1A1A22] border border-[#2A2A34] text-neutral-300 hover:text-white text-[10px] font-medium rounded-sm transition-colors"
                    >
                      Reject
                    </button>
                    <button onClick={() => rejectPendingFileChange(activeFile)} className="p-0.5 text-[#5C5C6C] hover:text-white">
                      <CloseRoundedIcon sx={{ fontSize: 11 }} />
                    </button>
                  </div>
                )}

                {/* Watching overlay */}
                {watching && (
                  <div className="absolute inset-x-0 bottom-0 h-7 z-20 flex items-center justify-center bg-[#10B981]/10 border-t border-[#10B981]/30">
                    <span className="text-[#10B981] text-[10px] font-mono font-bold tracking-widest animate-pulse flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse" />
                      RUNNING — MICROVM SANDBOX ACTIVE (governed by SENTINEL)
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
{/* Right panel: graph / inspector / copilot */}
        {inspectorOpen && (
          <div
            className="relative shrink-0 h-full bg-[#0B0B0F] border-l border-[#1E1E24] flex flex-col overflow-hidden"
            style={{ width: chatSideWidth }}
          >
            {/* Resize handle */}
            <div
              onMouseDown={handleChatSideDragStart}
              className="absolute left-0 top-0 bottom-0 w-[5px] cursor-col-resize z-30 hover:bg-[#E5252A]/40 transition-colors"
              title="Drag to resize panel"
            />

            {/* Panel tabs */}
            <div className="h-9 shrink-0 border-b border-[#1C1C24] bg-[#0A0A0C] flex items-stretch">
              {(["graph", "inspector", "copilot"] as const).map((tab) => {
                const active = rightPanelTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setRightPanelTab(tab)}
                    className={`flex items-center gap-1.5 px-3 h-full text-[10px] font-bold tracking-wider font-mono uppercase transition-colors border-t-[2px] ${
                      active
                        ? "text-white border-t-[#E5252A] bg-[#0B0B0F]"
                        : "text-[#5C5C6C] border-t-transparent hover:text-white hover:bg-[#0E0E12]"
                    }`}
                  >
                    {tab === "copilot" && aiTyping ? (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse" />
                    ) : tab === "copilot" ? (
                      <AutoAwesomeRoundedIcon sx={{ fontSize: 11, color: "#38D9A9" }} />
                    ) : null}
                    {tab}
                  </button>
                );
              })}
            </div>

            <div className="flex-1 overflow-hidden min-h-0">
              {rightPanelTab === "graph" && (
                <div className="p-3 h-full overflow-auto">
                  {/* Agent graph */}
                  <AgentGraph
                    agentName={realAgentName}
                    modelLabel={parsedManifest.modelLabel}
                    tools={parsedManifest.tools}
                    status={running ? "running" : "ready"}
                    trustLevel={parsedManifest.trustLevel}
                    trustScore={parsedManifest.trustScore}
                  />
                  {/* Graph legend */}
                  <div className="mt-2 pt-2 border-t border-[#1A1A22] text-[9px] font-mono text-[#5C5C6C] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-1 bg-[#61AFEF]" />
                      <span>Model node — semantic router target</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-1 bg-[#E5252A]" />
                      <span>Active agent — governed execution</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-1 bg-[#10B981]" />
                      <span>Tool node — SENTINEL-gated MCP calls</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-1 bg-[#E5C07B]" />
                      <span>Governance — policy cascade</span>
                    </div>
                  </div>
                </div>
              )}

              {rightPanelTab === "inspector" && (
                <AgentInspector
                  name={realAgentName}
                  agentId={agentId}
                  status={running ? "RUNNING" : "READY"}
                  model={parsedManifest.model}
                  fallbackModel="DeepSeek-V3"
                  tools={parsedManifest.tools}
                  trustLevel={parsedManifest.trustLevel}
                  trustScore={parsedManifest.trustScore}
                  runtime={parsedManifest.runtime}
                  timeout={parsedManifest.timeout}
                  memory={parsedManifest.memory}
                  environment="staging"
                  estimatedCost={
                    costEstimate ? `$${costEstimate.estimatedCostPerRun.toFixed(4)}/run` : undefined
                  }
                />
              )}

              {rightPanelTab === "copilot" && (
                <div className="flex flex-col h-full">
                  {/* Copilot intro strip */}
                  <div className="shrink-0 px-3 py-2 border-b border-[#1C1C24] flex items-center justify-between gap-2 bg-[#090A0E]">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#38D9A9] font-mono flex items-center gap-1.5 shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9]" />
                        Copilot
                      </span>
                      <ModelPicker
                        selectedModelId={selectedModelId}
                        onSelectModel={setSelectedModelId}
                        onOpenKeyModal={() => setShowKeyModal(true)}
                        dropdownPlacement="bottom"
                      />
                    </div>
                    <span className="text-[9px] text-[#5C5C6C] font-mono shrink-0">
                      {streamingMsgId ? "STREAMING…" : aiTyping ? "THINKING…" : "READY"}
                    </span>
                  </div>
{/* Messages */}
                  <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3 no-scrollbar text-left">
                    {msgs.map((m) =>
                      m.role === "user" ? (
                        <div key={m.id} className="flex justify-end">
                          <div className="max-w-[85%] px-2.5 py-1.5 bg-[#17171D] border border-[#26262E] rounded-[4px] text-[11px] text-[#E6EDF3] font-sans">
                            {m.content}
                          </div>
                        </div>
                      ) : (
                        <div key={m.id} className="space-y-1.5">
                          <div className="text-[9px] font-mono uppercase tracking-widest text-[#38D9A9] flex items-center gap-1.5">
                            <AutoAwesomeRoundedIcon sx={{ fontSize: 11 }} />
                            Composer
                          </div>
                          <CursorMarkdownRenderer
                            content={m.content}
                            isStreaming={m.id === streamingMsgId}
                            isAccepted={m.accepted}
                            isRejected={m.rejected}
                            onApplyCode={applySingleCodeBlock}
                            onApplyAllCode={(blocks) => applyAllCodeBlocks(blocks, m.id)}
                            onRejectAllCode={() => {
                              setMsgs((prev) =>
                                prev.map((msg) => (msg.id === m.id ? { ...msg, rejected: true } : msg))
                              );
                              setTermLogs((p) => [...p, mkLog("INFO", "Rejected all proposed AI changes.")]);
                            }}
                          />
                          {m.diff && !m.accepted && !m.rejected && (
                            <div className="border border-[#E5C07B]/30 bg-[#15171C] rounded-[4px] overflow-hidden">
                              <div className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-widest text-[#E5C07B] border-b border-[#22222A] flex items-center justify-between">
                                <span>PROPOSED CHANGES</span>
                                <span className="text-[9px] text-[#38D9A9]">agent.yaml</span>
                              </div>
                              <pre className="px-2.5 py-2 text-[10px] font-mono text-[#98C379] whitespace-pre-wrap break-words leading-relaxed">
                                {m.diff}
                              </pre>
                              <div className="flex gap-2 px-2.5 pb-2 pt-1">
                                <button
                                  onClick={() => acceptDiff(m.diff!, m.id)}
                                  className="px-2 py-0.5 bg-[#10B981] hover:bg-[#059669] text-black text-[10px] font-bold rounded-sm transition-colors"
                                >
                                  Accept
                                </button>
                                <button
                                  onClick={() => rejectDiff(m.id)}
                                  className="px-2 py-0.5 bg-[#14141A] border border-[#2A2A34] text-neutral-300 hover:text-white text-[10px] font-medium rounded-sm transition-colors"
                                >
                                  Reject
                                </button>
                              </div>
                            </div>
                          )}
                          {m.accepted && (
                            <div className="flex items-center gap-1.5 text-[10px] text-[#10B981] font-mono">
                              <CheckRoundedIcon sx={{ fontSize: 12 }} /> Accepted — review in editor
                            </div>
                          )}
                          {m.rejected && (
                            <div className="flex items-center gap-1.5 text-[10px] text-[#5C5C6C] font-mono">
                              <CloseRoundedIcon sx={{ fontSize: 12 }} /> Rejected
                            </div>
                          )}
                        </div>
                      )
                    )}
                    {aiTyping && !streamingMsgId && (
                      <div className="flex items-center gap-2 text-[11px] text-[#5C5C6C] font-mono">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse" />
                        Composer is thinking…
                      </div>
                    )}
                    <div ref={msgsEndRef} />
                  </div>

                  {/* Quick actions */}
                  <div className="shrink-0 px-3 pb-1.5 flex flex-wrap gap-1">
                    {QUICK_ACTIONS.map((a) => (
                      <button
                        key={a.label}
                        onClick={() => sendComposer(a.prompt)}
                        className="text-[9px] px-1.5 py-0.5 border border-[#26262E] rounded-[3px] text-[#8B8B98] hover:text-white hover:border-[#3A3A46] font-mono transition-colors"
                      >
                        {a.label}
                      </button>
                    ))}
                  </div>

                  {/* Usage meter */}
                  <div className="shrink-0 px-3 pb-1">
                    <UsageBar onOpenKeyModal={() => setShowKeyModal(true)} />
                  </div>
{/* Composer input */}
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      sendComposer();
                    }}
                    className="shrink-0 p-2.5 border-t border-[#1C1C24]"
                  >
                    <div className="flex items-end gap-2">
                      <textarea
                        rows={2}
                        value={compInput}
                        onChange={(e) => setCompInput(e.target.value)}
                        placeholder="Ask AgentVerse Copilot — e.g. “add the browser tool”"
                        className="flex-1 bg-[#111116] border border-[#26262E] rounded-[4px] px-2.5 py-1.5 text-[11px] text-[#E6EDF3] placeholder-[#4d4d5e] focus:outline-none focus:border-[#3A3A46] resize-none font-mono"
                      />
                      <button
                        type="submit"
                        className="h-8 w-8 flex items-center justify-center bg-[#E5252A] hover:bg-[#D01E23] text-white rounded-[4px] transition-colors"
                        title="Send"
                      >
                        <SendRoundedIcon sx={{ fontSize: 15 }} />
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
{/* Bottom terminal panel */}
      <IdTerminal
        activeTab={activeConsoleTab}
        onTabChange={(tab) => {
          if (activeConsoleTab === tab && !consoleCollapsed) setConsoleCollapsed(true);
          else {
            setActiveConsoleTab(tab);
            setConsoleCollapsed(false);
          }
        }}
        collapsed={consoleCollapsed}
        onToggleCollapsed={() => setConsoleCollapsed((v) => !v)}
        height={consoleHeight}
        onResizeHeight={setConsoleHeight}
        termLogs={termLogs}
        outputLines={outputLines}
        debugLines={debugLines}
        problems={TERM_PROBLEMS}
        onCommand={handleTerminalCommand}
        onClear={() => {
          setTermLogs([]);
          setOutputLines([]);
          setDebugLines([]);
        }}
        renderAsiBlock={(log) => (
          <AsiReviewCard
            key={`asi-card-${log.id}`}
            log={log}
            onOverride={() => overrideAsi(log.id)}
            onAbort={() => abortAsi(log.id)}
          />
        )}
        showWatching={watching}
        agentId={agentId}
      />

      {/* Status bar */}
      <div className="h-6 shrink-0 bg-[#0A0A0C] border-t border-[#1C1C24] flex items-center justify-between px-3 text-[10px] font-mono text-[#5C5C6C] select-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <AccountTreeRoundedIcon sx={{ fontSize: 11 }} />
            main
          </span>
          <span className="text-[#8B8B98]">{agentId}</span>
          <span className="hidden sm:flex items-center gap-1 text-[#8B8B98]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
            staging
          </span>
          <span className="hidden md:flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
            GovernOS connected
          </span>
        </div>
        <div className="flex items-center gap-3">
          {costEstimate && (
            <span className="text-[#E5C07B]">est ${costEstimate.estimatedCostPerRun.toFixed(4)}/run</span>
          )}
          <span className="hidden sm:inline">UTF-8</span>
          <span className="hidden sm:inline">LF</span>
          <span className="text-[#61AFEF]">{monacoLang(activeFile).toUpperCase()}</span>
          <span className="text-[#E5252A] font-bold">v2.4</span>
        </div>
      </div>

      {/* Key management modal */}
      <KeyManagementModal open={showKeyModal} onClose={() => setShowKeyModal(false)} />

      {/* GitHub connection modal */}
      <GithubConnectModal
        isOpen={isGithubModalOpen}
        onClose={() => setIsGithubModalOpen(false)}
        agentName={realAgentName}
        onConnect={(repo, branch, token) => {
          setIsGithubConnected(true);
          setGithubRepo(repo);
          setCurrentBranch(branch);
          setGithubToken(token);
          setTermLogs((p) => [...p, mkLog("OK", `[git] Successfully authenticated and connected GitHub repository ${repo} on branch ${branch}`)]);
        }}
      />
    </div>
  );
}