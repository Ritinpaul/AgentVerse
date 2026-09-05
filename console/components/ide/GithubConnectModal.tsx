"use client";

import React, { useState, useEffect } from "react";
import GitHubIcon from "@mui/icons-material/GitHub";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import LockRoundedIcon from "@mui/icons-material/LockRounded";
import PublicRoundedIcon from "@mui/icons-material/PublicRounded";
import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import KeyRoundedIcon from "@mui/icons-material/KeyRounded";
import FolderRoundedIcon from "@mui/icons-material/FolderRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import {
  GithubUser,
  GithubOrg,
  GithubRepo,
  validateGithubToken,
  fetchUserRepos,
  createGithubRepo,
  setStoredGithubToken,
  getStoredGithubToken,
  setStoredGithubRepo,
} from "@/lib/githubService";

interface GithubConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  onConnect: (fullRepoName: string, branchName: string, token: string) => void;
}

export function GithubConnectModal({
  isOpen,
  onClose,
  agentName,
  onConnect,
}: GithubConnectModalProps) {
  // Authentication state
  const [tokenInput, setTokenInput] = useState("");
  const [activeToken, setActiveToken] = useState<string | null>(null);
  const [githubUser, setGithubUser] = useState<GithubUser | null>(null);
  const [githubOrgs, setGithubOrgs] = useState<GithubOrg[]>([]);

  // Setup mode state
  const [step, setStep] = useState<"auth" | "repo">("auth");
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [ownerSelect, setOwnerSelect] = useState<string>("");

  // Existing Repo Selection
  const [userRepos, setUserRepos] = useState<GithubRepo[]>([]);
  const [selectedRepoFullName, setSelectedRepoFullName] = useState("");

  // New Repo Creation
  const defaultNewRepoName = agentName.toLowerCase().replace(/[^a-z0-9]/g, "-") || "autonomous-agent";
  const [newRepoName, setNewRepoName] = useState(defaultNewRepoName);
  const [isPrivate, setIsPrivate] = useState(true);
  const [branchName, setBranchName] = useState("main");

  // Loading & Error states
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isFetchingRepos, setIsFetchingRepos] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Initialize from stored token if present
  useEffect(() => {
    if (isOpen) {
      const storedToken = getStoredGithubToken();
      if (storedToken) {
        setTokenInput(storedToken);
        validateGithubToken(storedToken)
          .then(({ user, orgs }) => {
            setGithubUser(user);
            setGithubOrgs(orgs);
            setActiveToken(storedToken);
            setOwnerSelect(user.login);
            setStep("repo");
            return fetchUserRepos(storedToken);
          })
          .then((repos) => {
            setUserRepos(repos);
            if (repos.length > 0) setSelectedRepoFullName(repos[0].full_name);
          })
          .catch(() => {
            setStep("auth");
          });
      } else {
        setStep("auth");
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  async function handleAuthenticateToken(tokenToVerify: string) {
    if (!tokenToVerify.trim()) return;
    setIsAuthenticating(true);
    setErrorMsg(null);

    try {
      const { user, orgs } = await validateGithubToken(tokenToVerify.trim());
      setGithubUser(user);
      setGithubOrgs(orgs);
      setActiveToken(tokenToVerify.trim());
      setStoredGithubToken(tokenToVerify.trim());
      setOwnerSelect(user.login);
      setStep("repo");

      // Load repositories for current user
      loadRepos(tokenToVerify.trim(), user.login);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to authenticate token");
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function loadRepos(token: string, owner: string) {
    setIsFetchingRepos(true);
    setErrorMsg(null);
    try {
      const isOrg = githubOrgs.some((o) => o.login === owner);
      const repos = await fetchUserRepos(token, isOrg ? owner : undefined);
      setUserRepos(repos);
      if (repos.length > 0) {
        setSelectedRepoFullName(repos[0].full_name);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to fetch repositories");
    } finally {
      setIsFetchingRepos(false);
    }
  }

  function handleOwnerChange(newOwner: string) {
    setOwnerSelect(newOwner);
    if (activeToken) {
      loadRepos(activeToken, newOwner);
    }
  }

  async function handleSubmitRepo(e: React.FormEvent) {
    e.preventDefault();
    if (!activeToken || !githubUser) return;
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      let finalRepoFullName = "";

      if (mode === "existing") {
        if (!selectedRepoFullName) {
          throw new Error("Please select a repository from the list.");
        }
        finalRepoFullName = selectedRepoFullName;
      } else {
        if (!newRepoName.trim()) {
          throw new Error("Please enter a valid repository name.");
        }
        const isOrg = ownerSelect !== githubUser.login;
        const created = await createGithubRepo(
          activeToken,
          newRepoName.trim(),
          isPrivate,
          isOrg ? ownerSelect : undefined
        );
        finalRepoFullName = created.full_name;
      }

      const [owner, repo] = finalRepoFullName.split("/");
      setStoredGithubRepo(owner, repo, branchName || "main");

      onConnect(finalRepoFullName, branchName || "main", activeToken);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to link repository");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-[#0F0F14] border border-[#22222E] rounded-xl shadow-2xl overflow-hidden font-mono text-white">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#1C1C26] flex items-center justify-between bg-[#13131A]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#181824] border border-[#2A2A3A] flex items-center justify-center text-white">
              <GitHubIcon sx={{ fontSize: 20 }} />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                Live GitHub Connection
              </h3>
              <p className="text-[10px] text-slate-400">AgentVerse Version Control Link</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-[#222230] transition-colors"
          >
            <CloseRoundedIcon sx={{ fontSize: 18 }} />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 space-y-4 text-xs">
          {errorMsg && (
            <div className="p-2.5 rounded-md bg-red-950/40 border border-red-800/40 text-red-300 text-[11px] leading-relaxed">
              {errorMsg}
            </div>
          )}

          {/* STEP 1: Authentication */}
          {step === "auth" ? (
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-300 font-medium flex items-center justify-between">
                  <span>GitHub Personal Access Token (PAT)</span>
                  <a
                    href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=AgentVerse+Studio"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-sky-400 hover:underline flex items-center gap-0.5"
                  >
                    <span>Generate PAT</span>
                    <OpenInNewRoundedIcon sx={{ fontSize: 11 }} />
                  </a>
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx or github_pat_xxxx"
                    className="w-full bg-[#161620] border border-[#2A2A38] rounded-md pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500/50"
                  />
                  <KeyRoundedIcon sx={{ fontSize: 14, color: "#8B8B98" }} className="absolute left-2.5 top-2.5" />
                </div>
                <p className="text-[10px] text-slate-400 leading-normal pt-1">
                  Requires <code className="text-amber-300 bg-[#1A1A26] px-1 py-0.5 rounded">repo</code> scope to create commits & push code directly to GitHub.
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-md bg-[#161620] hover:bg-[#20202E] text-slate-300 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isAuthenticating || !tokenInput.trim()}
                  onClick={() => handleAuthenticateToken(tokenInput)}
                  className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-lg shadow-red-950/40"
                >
                  {isAuthenticating ? "Authenticating..." : "Authenticate GitHub Account"}
                </button>
              </div>
            </div>
          ) : (
            /* STEP 2: Repository Link or Create */
            <form onSubmit={handleSubmitRepo} className="space-y-4">
              {/* Connected User Badge */}
              {githubUser && (
                <div className="p-2.5 rounded-lg bg-[#14141E] border border-[#222230] flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <img
                      src={githubUser.avatar_url}
                      alt={githubUser.login}
                      className="w-6 h-6 rounded-full border border-slate-700"
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-slate-100 truncate">
                        {githubUser.name || githubUser.login}
                      </div>
                      <div className="text-[10px] text-slate-400">@{githubUser.login}</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setStep("auth");
                      setTokenInput("");
                    }}
                    className="text-[10px] text-slate-400 hover:text-amber-300 underline"
                  >
                    Switch Account
                  </button>
                </div>
              )}

              {/* Owner / Org Selector */}
              <div className="space-y-1.5">
                <label className="block text-[11px] text-slate-300 font-medium">Owner</label>
                <select
                  value={ownerSelect}
                  onChange={(e) => handleOwnerChange(e.target.value)}
                  className="w-full bg-[#161620] border border-[#2A2A38] rounded-md px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/50"
                >
                  {githubUser && <option value={githubUser.login}>{githubUser.login} (User)</option>}
                  {githubOrgs.map((org) => (
                    <option key={org.id} value={org.login}>
                      {org.login} (Organization)
                    </option>
                  ))}
                </select>
              </div>

              {/* Mode Toggle: Existing vs New */}
              <div className="flex items-center p-0.5 bg-[#14141E] rounded-lg border border-[#222230] text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setMode("existing")}
                  className={`flex-1 py-1.5 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                    mode === "existing"
                      ? "bg-[#20202E] text-white font-bold border border-[#333346]"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <FolderRoundedIcon sx={{ fontSize: 14 }} />
                  <span>Select Existing Repo</span>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("new")}
                  className={`flex-1 py-1.5 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                    mode === "new"
                      ? "bg-[#20202E] text-white font-bold border border-[#333346]"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <AddRoundedIcon sx={{ fontSize: 14 }} />
                  <span>Create New Repo</span>
                </button>
              </div>

              {/* Existing Repo Selector */}
              {mode === "existing" ? (
                <div className="space-y-1.5">
                  <label className="block text-[11px] text-slate-300 font-medium">
                    Target Repository
                  </label>
                  {isFetchingRepos ? (
                    <div className="text-[11px] text-slate-400 py-2 text-center">Loading repositories...</div>
                  ) : userRepos.length > 0 ? (
                    <select
                      value={selectedRepoFullName}
                      onChange={(e) => setSelectedRepoFullName(e.target.value)}
                      className="w-full bg-[#161620] border border-[#2A2A38] rounded-md px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500/50"
                    >
                      {userRepos.map((r) => (
                        <option key={r.id} value={r.full_name}>
                          {r.full_name} {r.private ? "(Private)" : "(Public)"}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-[11px] text-amber-400 py-1">No repositories found for {ownerSelect}.</div>
                  )}
                </div>
              ) : (
                /* New Repo Inputs */
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-slate-300 font-medium">
                      New Repository Name
                    </label>
                    <input
                      type="text"
                      value={newRepoName}
                      onChange={(e) => setNewRepoName(e.target.value)}
                      placeholder="repo-name"
                      className="w-full bg-[#161620] border border-[#2A2A38] rounded-md px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500/50"
                      required
                    />
                  </div>

                  <div className="flex items-center justify-between bg-[#161620] border border-[#2A2A38] rounded-md p-2 text-xs">
                    <div className="flex items-center gap-1.5">
                      {isPrivate ? (
                        <LockRoundedIcon sx={{ fontSize: 14, color: "#E5C07B" }} />
                      ) : (
                        <PublicRoundedIcon sx={{ fontSize: 14, color: "#38D9A9" }} />
                      )}
                      <span>{isPrivate ? "Private Repository" : "Public Repository"}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsPrivate(!isPrivate)}
                      className="text-[10px] text-slate-400 hover:text-white underline"
                    >
                      Toggle
                    </button>
                  </div>
                </div>
              )}

              {/* Target Branch */}
              <div className="space-y-1.5">
                <label className="block text-[11px] text-slate-300 font-medium">Target Branch</label>
                <div className="flex items-center gap-1.5 bg-[#161620] border border-[#2A2A38] rounded-md px-3 py-1.5 text-xs">
                  <AccountTreeRoundedIcon sx={{ fontSize: 14, color: "#8B8B98" }} />
                  <input
                    type="text"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    className="w-full bg-transparent text-white focus:outline-none"
                    placeholder="main"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-[#1C1C26]">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-md bg-[#161620] hover:bg-[#20202E] text-slate-300 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || (mode === "existing" && !selectedRepoFullName)}
                  className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-lg shadow-red-950/40"
                >
                  {isSubmitting ? (
                    <span>Linking GitHub...</span>
                  ) : (
                    <>
                      <CheckCircleRoundedIcon sx={{ fontSize: 15 }} />
                      <span>Link & Enable Live Version Control</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
