/**
 * agentPersistence.ts
 * User-scoped persistence & cross-device cloud sync for AgentVerse Studio.
 * Enforces Free plan quota limit of 5 agents maximum.
 */

import { getStoredUser, UserProfile } from "./auth";

export interface StudioSession {
  id: string; // slug, e.g. "finance-analyst-v2"
  name: string;
  branch: string;
  status: "running" | "paused" | "needs-approval" | "idle";
  model: string;
  fallback?: string;
  templateId?: string;
  files: string[];
  plan: { current: number; total: number };
  collaborators: string[];
  pendingApprovals: number;
  lastModified: string;
  lastAction: string;
  createdAt: number;
  updatedAt: number;
}

export const MAX_FREE_AGENTS = 5;

const BASE_SESSIONS_KEY = "agentverse_studio_sessions_v1";
const BASE_FILES_PREFIX = "agentverse_files_v1_";

/** Resolve active user ID for storage scoping */
export function getActiveUserId(): string {
  if (typeof window === "undefined") return "default_user";
  try {
    const user = getStoredUser();
    if (user && (user.id || user.email)) {
      return (user.id || user.email).toLowerCase().replace(/[^a-z0-9_-]/g, "_");
    }
  } catch {}
  return "default_user";
}

/** Get active user tier ("Free" | "Pro" | "Enterprise") */
export function getActiveUserTier(): "Free" | "Pro" | "Enterprise" {
  if (typeof window === "undefined") return "Free";
  try {
    const user = getStoredUser();
    if (user?.org_tier === "Pro" || user?.org_tier === "Enterprise") {
      return user.org_tier;
    }
    const wsTier = user?.workspaces?.[0]?.tier;
    if (wsTier === "Pro" || wsTier === "Enterprise") {
      return wsTier;
    }
  } catch {}
  return "Free";
}

/** Scoped storage key for sessions */
function getSessionsKey(): string {
  const uid = getActiveUserId();
  return `${BASE_SESSIONS_KEY}_${uid}`;
}

/** Scoped storage key for agent files */
function getFilesKey(agentId: string): string {
  const uid = getActiveUserId();
  return `${BASE_FILES_PREFIX}${uid}_${agentId}`;
}

const DEFAULT_SESSIONS: StudioSession[] = [
  {
    id: "finance-analyst-v2",
    name: "Finance Analyst Pro",
    branch: "workspace/finance-analyst-v2",
    status: "running",
    model: "claude-3-5-sonnet",
    fallback: "gpt-4o-mini",
    templateId: "finance",
    files: ["agent.yaml", "tools.py", "prompts/system.md"],
    plan: { current: 3, total: 3 },
    collaborators: ["NV", "AI"],
    pendingApprovals: 0,
    lastModified: "Synchronized",
    lastAction: "Ready in MicroVM Sandbox",
    createdAt: Date.now() - 3600000 * 24,
    updatedAt: Date.now() - 3600000 * 2,
  },
  {
    id: "devops-sre-sentinel",
    name: "DevOps SRE Sentinel",
    branch: "workspace/devops-sre-sentinel",
    status: "running",
    model: "gemini-2.0-flash",
    fallback: "gpt-4o-mini",
    templateId: "devops",
    files: ["agent.yaml", "tools.py", "prompts/system.md"],
    plan: { current: 2, total: 4 },
    collaborators: ["SRE"],
    pendingApprovals: 0,
    lastModified: "Synchronized",
    lastAction: "Monitoring k8s pod metrics",
    createdAt: Date.now() - 3600000 * 48,
    updatedAt: Date.now() - 3600000 * 5,
  },
  {
    id: "secops-guardian",
    name: "SecOps Threat Hunter",
    branch: "workspace/secops-guardian",
    status: "needs-approval",
    model: "gpt-4o",
    fallback: "claude-3-5-haiku",
    templateId: "security",
    files: ["agent.yaml", "tools.py", "prompts/system.md"],
    plan: { current: 1, total: 5 },
    collaborators: ["SEC"],
    pendingApprovals: 1,
    lastModified: "Synchronized",
    lastAction: "GovernOS policy gate flagged admin escalation",
    createdAt: Date.now() - 3600000 * 72,
    updatedAt: Date.now() - 3600000 * 12,
  },
];

/** Check if current user is allowed to create another agent based on plan tier */
export function checkCanCreateAgent(customSessions?: { length: number } | any[]): {
  allowed: boolean;
  count: number;
  max: number;
  tier: "Free" | "Pro" | "Enterprise";
  remaining: number;
} {
  const tier = getActiveUserTier();
  const sessions = customSessions || getStoredSessions();
  const count = sessions.length;

  if (tier !== "Free") {
    return { allowed: true, count, max: Infinity, tier, remaining: Infinity };
  }

  const remaining = Math.max(0, MAX_FREE_AGENTS - count);
  const allowed = count < MAX_FREE_AGENTS;

  return { allowed, count, max: MAX_FREE_AGENTS, tier, remaining };
}

/** Read all sessions stored in browser localStorage for the active user */
export function getStoredSessions(): StudioSession[] {
  if (typeof window === "undefined") return [];
  try {
    const key = getSessionsKey();
    const raw = localStorage.getItem(key);
    if (!raw) {
      // Also check legacy un-scoped key for seamless upgrade migration
      const legacyRaw = localStorage.getItem(BASE_SESSIONS_KEY);
      if (legacyRaw) {
        const legacyParsed = JSON.parse(legacyRaw);
        if (Array.isArray(legacyParsed) && legacyParsed.length > 0) {
          localStorage.setItem(key, JSON.stringify(legacyParsed));
          return legacyParsed;
        }
      }
      localStorage.setItem(key, JSON.stringify(DEFAULT_SESSIONS));
      return DEFAULT_SESSIONS;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed;
    }
    return DEFAULT_SESSIONS;
  } catch {
    return DEFAULT_SESSIONS;
  }
}

/** Save or update a session in localStorage and sync to cloud */
export function saveStoredSession(session: StudioSession, syncToCloud: boolean = true): void {
  if (typeof window === "undefined") return;
  try {
    const key = getSessionsKey();
    const current = getStoredSessions();
    const idx = current.findIndex((s) => s.id === session.id);
    let updated: StudioSession[];
    const isNew = idx < 0;

    if (idx >= 0) {
      updated = [...current];
      updated[idx] = { ...updated[idx], ...session, updatedAt: Date.now() };
    } else {
      updated = [{ ...session, createdAt: Date.now(), updatedAt: Date.now() }, ...current];
    }
    localStorage.setItem(key, JSON.stringify(updated));

    if (syncToCloud) {
      const files = getStoredAgentFiles(session.id) || {};
      syncSessionToCloud(session, files, isNew);
    }
  } catch (err) {
    console.warn("Failed to persist session to localStorage", err);
  }
}

/** Delete a session from localStorage and cloud */
export function deleteStoredSession(sessionId: string): void {
  if (typeof window === "undefined") return;
  try {
    const key = getSessionsKey();
    const current = getStoredSessions();
    const updated = current.filter((s) => s.id !== sessionId);
    localStorage.setItem(key, JSON.stringify(updated));
    localStorage.removeItem(getFilesKey(sessionId));

    // Async cloud delete
    deleteSessionFromCloud(sessionId);
  } catch (err) {
    console.warn("Failed to delete session from localStorage", err);
  }
}

/** Touch session to update lastModified / lastAction timestamp */
export function touchStoredSession(sessionId: string, patch?: Partial<StudioSession>): void {
  if (typeof window === "undefined") return;
  try {
    const key = getSessionsKey();
    const current = getStoredSessions();
    const idx = current.findIndex((s) => s.id === sessionId);
    if (idx >= 0) {
      const updated = [...current];
      updated[idx] = {
        ...updated[idx],
        ...patch,
        lastModified: "Just now",
        updatedAt: Date.now(),
      };
      localStorage.setItem(key, JSON.stringify(updated));
    }
  } catch {}
}

/** Get saved files for a specific agent/session */
export function getStoredAgentFiles(agentId: string): Record<string, string> | null {
  if (typeof window === "undefined") return null;
  try {
    const key = getFilesKey(agentId);
    let raw = localStorage.getItem(key);
    if (!raw) {
      // Legacy migration check
      raw = localStorage.getItem(`${BASE_FILES_PREFIX}${agentId}`);
      if (raw) {
        localStorage.setItem(key, raw);
      }
    }
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && Object.keys(parsed).length > 0) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

/** Save files dictionary for a specific agent/session and sync to cloud */
export function saveStoredAgentFiles(agentId: string, files: Record<string, string>, syncCloud: boolean = true): void {
  if (typeof window === "undefined") return;
  try {
    const key = getFilesKey(agentId);
    localStorage.setItem(key, JSON.stringify(files));

    if (syncCloud) {
      const sessions = getStoredSessions();
      const sess = sessions.find((s) => s.id === agentId);
      if (sess) {
        syncSessionToCloud(sess, files, false);
      }
    }
  } catch (err) {
    console.warn(`Failed to save files for agent ${agentId} to localStorage`, err);
  }
}

// ── Cloud API Sync Layer ───────────────────────────────────────────────────────

/** Sync session and workspace files to cloud backend */
export async function syncSessionToCloud(session: StudioSession, files: Record<string, string>, isNew: boolean = false): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    const userId = getActiveUserId();
    const tier = getActiveUserTier();

    await fetch("/api/studio/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-id": userId,
        "x-user-tier": tier,
      },
      body: JSON.stringify({
        userId,
        tier,
        session,
        files,
        isNew,
      }),
    });
  } catch (err) {
    console.warn("Background cloud sync error:", err);
  }
}

/** Delete session from cloud backend */
export async function deleteSessionFromCloud(sessionId: string): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    const userId = getActiveUserId();
    await fetch(`/api/studio/sessions?id=${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
      headers: {
        "x-user-id": userId,
      },
    });
  } catch (err) {
    console.warn("Background cloud delete error:", err);
  }
}

/**
 * Syncs user sessions from cloud API on page load / device change.
 * Merges cloud data into local storage.
 */
export async function syncSessionsFromCloud(): Promise<StudioSession[]> {
  if (typeof window === "undefined") return [];
  try {
    const userId = getActiveUserId();
    const tier = getActiveUserTier();

    const res = await fetch(`/api/studio/sessions?userId=${encodeURIComponent(userId)}&tier=${encodeURIComponent(tier)}`, {
      headers: {
        "x-user-id": userId,
        "x-user-tier": tier,
      },
      signal: AbortSignal.timeout(3000),
    });

    if (!res.ok) return getStoredSessions();

    const data = await res.json();
    const cloudSessions: StudioSession[] = data.sessions || [];
    const cloudFiles: Record<string, Record<string, string>> = data.files || {};

    const localSessions = getStoredSessions();
    const mergedMap = new Map<string, StudioSession>();

    // 1. Add cloud sessions
    for (const s of cloudSessions) {
      mergedMap.set(s.id, s);
    }
    // 2. Preserve any local sessions not yet synced or newer
    for (const s of localSessions) {
      const existing = mergedMap.get(s.id);
      if (!existing || (s.updatedAt && s.updatedAt > (existing.updatedAt || 0))) {
        mergedMap.set(s.id, s);
      }
    }

    const merged = Array.from(mergedMap.values());
    const key = getSessionsKey();
    localStorage.setItem(key, JSON.stringify(merged));

    // Sync down cloud files if missing locally
    for (const [agentId, files] of Object.entries(cloudFiles)) {
      const localFiles = getStoredAgentFiles(agentId);
      if (!localFiles || Object.keys(localFiles).length === 0) {
        saveStoredAgentFiles(agentId, files, false);
      }
    }

    return merged;
  } catch {
    return getStoredSessions();
  }
}
