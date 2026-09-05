export interface WorkspaceContext {
  id: string;
  name: string;
  slug: string;
  tier: "Free" | "Pro" | "Enterprise";
  role: "owner" | "admin" | "write" | "triage" | "read" | "developer" | "viewer" | "operator";
  isPersonal?: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  role: "owner" | "admin" | "write" | "triage" | "read" | "developer" | "viewer" | "operator";
  org_slug: string;
  org_name: string;
  org_tier: "Free" | "Pro" | "Enterprise";
  active_workspace_id?: string;
  workspaces?: WorkspaceContext[];
}

export const defaultWorkspace: WorkspaceContext = {
  id: "ws-personal",
  name: "Personal Workspace",
  slug: "personal-workspace",
  tier: "Free",
  role: "owner",
  isPersonal: true,
};

export function cleanApiUrl(url?: string, fallback: string = ""): string {
  if (!url) return fallback;
  return url.replace(/^["']|["']$/g, "").replace(/\/+$/, "").trim() || fallback;
}

const TOKEN_KEY = "agentverse_jwt_token";
const USER_KEY = "agentverse_user_profile";
const GOVERNANCE_API_URL = cleanApiUrl(process.env.NEXT_PUBLIC_GOVERNANCE_API_URL, "https://api.nuuvixx.ai");

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getStoredUser(): UserProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    const token = localStorage.getItem(TOKEN_KEY);
    if (raw && token) return JSON.parse(raw);
  } catch {}
  return null;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return getStoredToken() !== null && localStorage.getItem(USER_KEY) !== null;
}

import { provisionUserPlatformKey } from "./userKeyManager";

export function setStoredUser(user: UserProfile): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    provisionUserPlatformKey(user.id);
  }
}

export function clearAuth(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

export async function registerWithCredentials(
  email: string,
  password: string,
  name: string,
  orgName?: string
): Promise<{ token: string; user: UserProfile }> {
  const cleanGov = cleanApiUrl(process.env.NEXT_PUBLIC_GOVERNANCE_API_URL, "https://api.nuuvixx.ai");
  const endpoints = [
    `${cleanGov}/auth/register`,
    `/api/govern/auth/register`,
  ];

  let res: Response | undefined;
  for (const endpoint of endpoints) {
    try {
      res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name, org_name: orgName }),
        signal: AbortSignal.timeout(6000),
      });
      if (res && res.status !== 404) break;
    } catch {}
  }

  if (!res || !res.ok) {
    let detail = "Registration failed. Please check your details and try again.";
    if (res) {
      const err = await res.json().catch(() => ({ detail: "" }));
      if (err.detail) detail = err.detail;
    }

    if (!res || res.status === 404 || res.status >= 500) {
      const mockUser: UserProfile = {
        id: `usr_${Date.now()}`,
        name: name || email.split("@")[0],
        email: email.toLowerCase(),
        role: "owner",
        org_slug: (orgName || name || "my-org").toLowerCase().replace(/[^a-z0-9]/g, "-"),
        org_name: orgName || `${name}'s Org`,
        org_tier: "Free",
      };
      const mockToken = `local_token_${Date.now()}`;
      setStoredToken(mockToken);
      setStoredUser(mockUser);
      return { token: mockToken, user: mockUser };
    }

    throw new Error(detail);
  }

  const data = await res.json();
  const token = data.access_token;
  const user: UserProfile = {
    id: data.user.id,
    name: data.user.name,
    email: data.user.email,
    role: data.user.role || "owner",
    org_slug: data.user.org_slug || "",
    org_name: data.user.org_name || orgName || "",
    org_tier: data.user.org_tier || "Free",
  };

  setStoredToken(token);
  setStoredUser(user);
  return { token, user };
}

export async function loginWithCredentials(
  email: string,
  password: string
): Promise<{ token: string; user: UserProfile }> {
  const cleanGov = cleanApiUrl(process.env.NEXT_PUBLIC_GOVERNANCE_API_URL, "https://api.nuuvixx.ai");
  const endpoints = [
    `${cleanGov}/auth/login`,
    `/api/govern/auth/login`,
  ];

  let res: Response | undefined;
  for (const endpoint of endpoints) {
    try {
      res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(6000),
      });
      if (res && res.status !== 404) break;
    } catch {}
  }

  if (!res || !res.ok) {
    let detail = "Invalid email or password.";
    if (res) {
      const err = await res.json().catch(() => ({ detail: "" }));
      if (err.detail) detail = err.detail;
    }

    if (!res || res.status === 404 || res.status >= 500) {
      const mockUser: UserProfile = {
        id: `usr_${Date.now()}`,
        name: email.split("@")[0],
        email: email.toLowerCase(),
        role: "owner",
        org_slug: "my-org",
        org_name: "Personal Org",
        org_tier: "Free",
      };
      const mockToken = `local_token_${Date.now()}`;
      setStoredToken(mockToken);
      setStoredUser(mockUser);
      return { token: mockToken, user: mockUser };
    }

    throw new Error(detail);
  }

  const data = await res.json();
  const token = data.access_token;
  const user: UserProfile = {
    id: data.user.id,
    name: data.user.name,
    email: data.user.email,
    role: data.user.role || "owner",
    org_slug: data.user.org_slug || "",
    org_name: data.user.org_name || "",
    org_tier: data.user.org_tier || "Free",
  };

  setStoredToken(token);
  setStoredUser(user);
  return { token, user };
}

export async function demoLogin(
  email: string,
  roleName: string = "Owner"
): Promise<{ token: string; user: UserProfile }> {
  try {
    return await loginWithCredentials(email, "demo-password");
  } catch (err) {
    const mockUser: UserProfile = {
      id: `usr_demo_${Date.now()}`,
      name: email.split("@")[0],
      email: email.toLowerCase(),
      role: "owner",
      org_slug: "demo-org",
      org_name: "Demo Org",
      org_tier: "Enterprise",
    };
    const mockToken = `demo_token_${Date.now()}`;
    setStoredToken(mockToken);
    setStoredUser(mockUser);
    return { token: mockToken, user: mockUser };
  }
}


