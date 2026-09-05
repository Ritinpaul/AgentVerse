export interface GithubUser {
  login: string;
  id: number;
  avatar_url: string;
  name: string;
  html_url: string;
}

export interface GithubOrg {
  login: string;
  id: number;
  avatar_url: string;
  description: string;
}

export interface GithubRepo {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  html_url: string;
  default_branch: string;
}

const GITHUB_TOKEN_KEY = "agentverse_github_token";
const GITHUB_LINKED_REPO_KEY = "agentverse_github_linked_repo";

export function getStoredGithubToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(GITHUB_TOKEN_KEY);
}

export function setStoredGithubToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(GITHUB_TOKEN_KEY, token);
  }
}

export function clearGithubToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(GITHUB_TOKEN_KEY);
    localStorage.removeItem(GITHUB_LINKED_REPO_KEY);
  }
}

export function getStoredGithubRepo(): { owner: string; repo: string; branch: string } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(GITHUB_LINKED_REPO_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

export function setStoredGithubRepo(owner: string, repo: string, branch: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(GITHUB_LINKED_REPO_KEY, JSON.stringify({ owner, repo, branch }));
  }
}

function getHeaders(token: string) {
  return {
    Authorization: `Bearer ${token.trim()}`,
    Accept: "application/vnd.github.v3+json",
    "Content-Type": "application/json",
  };
}

export async function validateGithubToken(token: string): Promise<{ user: GithubUser; orgs: GithubOrg[] }> {
  const userRes = await fetch("https://api.github.com/user", {
    headers: getHeaders(token),
  });

  if (!userRes.ok) {
    throw new Error("Invalid GitHub token. Please verify your Personal Access Token and scopes.");
  }

  const user: GithubUser = await userRes.json();

  let orgs: GithubOrg[] = [];
  try {
    const orgsRes = await fetch("https://api.github.com/user/orgs", {
      headers: getHeaders(token),
    });
    if (orgsRes.ok) {
      orgs = await orgsRes.json();
    }
  } catch {}

  return { user, orgs };
}

export async function fetchUserRepos(token: string, org?: string): Promise<GithubRepo[]> {
  const url = org
    ? `https://api.github.com/orgs/${org}/repos?per_page=100&sort=updated`
    : `https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator`;

  const res = await fetch(url, { headers: getHeaders(token) });
  if (!res.ok) {
    throw new Error(`Failed to fetch repositories from GitHub (${res.status})`);
  }
  return await res.json();
}

export async function fetchRepoBranches(token: string, owner: string, repo: string): Promise<string[]> {
  try {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/branches`, {
      headers: getHeaders(token),
    });
    if (res.ok) {
      const branches = await res.json();
      return branches.map((b: { name: string }) => b.name);
    }
  } catch {}
  return ["main"];
}

export async function createGithubRepo(
  token: string,
  repoName: string,
  isPrivate: boolean,
  org?: string
): Promise<GithubRepo> {
  const url = org
    ? `https://api.github.com/orgs/${org}/repos`
    : `https://api.github.com/user/repos`;

  const res = await fetch(url, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({
      name: repoName,
      private: isPrivate,
      auto_init: true,
      description: "Autonomous AI Agent repository created via AgentVerse Studio",
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "Failed to create repository" }));
    throw new Error(err.message || `Failed to create repository on GitHub (${res.status})`);
  }

  return await res.json();
}

function utf8ToBase64(str: string): string {
  try {
    return btoa(unescape(encodeURIComponent(str)));
  } catch {
    return btoa(str);
  }
}

export async function commitFilesToGithub(
  token: string,
  owner: string,
  repo: string,
  branch: string,
  commitMessage: string,
  files: { path: string; content: string }[]
): Promise<{ commitSha: string; commitUrl: string; committedFiles: string[] }> {
  const committedFiles: string[] = [];
  let lastSha = "";

  for (const file of files) {
    const path = file.path.replace(/^\//, "");
    const contentBase64 = utf8ToBase64(file.content);

    // Fetch existing file SHA if updating
    let existingSha: string | undefined;
    try {
      const existingRes = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}?ref=${encodeURIComponent(branch)}`,
        { headers: getHeaders(token) }
      );
      if (existingRes.ok) {
        const existingData = await existingRes.json();
        existingSha = existingData.sha;
      }
    } catch {}

    const putBody: Record<string, unknown> = {
      message: `${commitMessage} [${path}]`,
      content: contentBase64,
      branch,
    };
    if (existingSha) putBody.sha = existingSha;

    const putRes = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`,
      {
        method: "PUT",
        headers: getHeaders(token),
        body: JSON.stringify(putBody),
      }
    );

    if (!putRes.ok) {
      const err = await putRes.json().catch(() => ({ message: `Failed to update ${path}` }));
      throw new Error(err.message || `Failed to commit ${path} to GitHub (${putRes.status})`);
    }

    const resData = await putRes.json();
    if (resData.commit && resData.commit.sha) {
      lastSha = resData.commit.sha.substring(0, 7);
    }
    committedFiles.push(path);
  }

  const commitUrl = `https://github.com/${owner}/${repo}/commit/${lastSha}`;
  return { commitSha: lastSha || "HEAD", commitUrl, committedFiles };
}
