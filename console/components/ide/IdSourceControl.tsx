"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import UndoRoundedIcon from "@mui/icons-material/UndoRounded";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import DoneAllRoundedIcon from "@mui/icons-material/DoneAllRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import GitHubIcon from "@mui/icons-material/GitHub";
import CloudSyncRoundedIcon from "@mui/icons-material/CloudSyncRounded";
import LockRoundedIcon from "@mui/icons-material/LockRounded";
import LinkRoundedIcon from "@mui/icons-material/LinkRounded";
import LinkOffRoundedIcon from "@mui/icons-material/LinkOffRounded";

interface IdSourceControlProps {
  modifiedFiles: string[];
  pendingFileChanges: string[];
  activeFile: string;
  onOpenFile: (path: string) => void;
  onDiscardFileChange?: (path: string) => void;
  onCommit: (message: string) => void;
  branchName?: string;
  isGithubConnected?: boolean;
  githubRepo?: string | null;
  onOpenGithubModal?: () => void;
  onDisconnectGithub?: () => void;
}

export function IdSourceControl({
  modifiedFiles,
  pendingFileChanges,
  activeFile,
  onOpenFile,
  onDiscardFileChange,
  onCommit,
  branchName = "main",
  isGithubConnected = false,
  githubRepo = null,
  onOpenGithubModal,
  onDisconnectGithub,
}: IdSourceControlProps) {
  const [commitMsg, setCommitMsg] = useState("");
  const [isCommitting, setIsCommitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Combine modified files and pending AI files uniquely
  const allChangedFiles = Array.from(new Set([...modifiedFiles, ...pendingFileChanges]));
  const hasChanges = allChangedFiles.length > 0;

  const handleCommit = () => {
    const trimmed = commitMsg.trim();
    if (!trimmed || !hasChanges) return;

    setIsCommitting(true);
    onCommit(trimmed);
    setCommitMsg("");
    setStatusMessage("Committed & synced to " + (githubRepo || "github.com"));
    setTimeout(() => {
      setIsCommitting(false);
      setStatusMessage(null);
    }, 2500);
  };

  const getFileBadge = (file: string) => {
    if (pendingFileChanges.includes(file)) {
      return { label: "AI", color: "text-[#38D9A9] bg-[#38D9A9]/10 border-[#38D9A9]/20" };
    }
    return { label: "M", color: "text-[#E5C07B] bg-[#E5C07B]/10 border-[#E5C07B]/20" };
  };

  return (
    <div className="w-72 shrink-0 h-full bg-[#0B0B0E] border-r border-[#1C1C24] flex flex-col select-none text-white z-10 font-mono">
      {/* Top Panel Header */}
      <div className="h-9 shrink-0 border-b border-[#1C1C24] px-3 flex items-center justify-between bg-[#0E0E12]">
        <div className="flex items-center gap-1.5 min-w-0">
          <AccountTreeRoundedIcon sx={{ fontSize: 14, color: "#8B8B98" }} />
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#A0A0B0] font-bold truncate">
            Source Control
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px]">
          {isGithubConnected ? (
            <span className="px-1.5 py-0.5 rounded bg-[#10B981]/10 border border-[#10B981]/30 text-[#10B981] font-bold">
              {branchName}
            </span>
          ) : (
            <span className="px-1.5 py-0.5 rounded bg-[#22222E] text-[#8B8B98] border border-[#2E2E3E]">
              Unconnected
            </span>
          )}
        </div>
      </div>

      {/* Main Body */}
      {!isGithubConnected ? (
        /* State A: GitHub Setup Onboarding View */
        <div className="flex-1 overflow-y-auto p-4 flex flex-col items-center justify-between no-scrollbar space-y-4">
          <div className="w-full space-y-4 text-center my-auto">
            {/* Icon Container */}
            <div className="relative mx-auto w-12 h-12 rounded-xl bg-[#14141E] border border-[#262636] flex items-center justify-center text-white shadow-xl group">
              <GitHubIcon sx={{ fontSize: 28 }} />
              <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-red-600 border border-[#0B0B0E] flex items-center justify-center">
                <LinkOffRoundedIcon sx={{ fontSize: 10, color: "#FFF" }} />
              </div>
            </div>

            {/* Title & Explanation */}
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wide">
                Connect GitHub Repository
              </h4>
              <p className="text-[10px] text-slate-400 font-sans leading-relaxed px-1">
                Link your GitHub account to enable automated commits, version history, PR workflows, and Firecracker MicroVM CI/CD triggers.
              </p>
            </div>

            {/* Actions */}
            <div className="space-y-2 pt-1 w-full">
              <button
                onClick={onOpenGithubModal}
                className="w-full h-8 rounded-md bg-red-600 hover:bg-red-500 text-white text-[11px] font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-red-950/40"
              >
                <GitHubIcon sx={{ fontSize: 15 }} />
                <span>Connect GitHub Account</span>
              </button>

              <button
                onClick={onOpenGithubModal}
                className="w-full h-7 rounded-md bg-[#161620] hover:bg-[#1E1E2C] border border-[#252536] text-slate-300 text-[10px] font-medium flex items-center justify-center gap-1.5 transition-colors"
              >
                <LinkRoundedIcon sx={{ fontSize: 14 }} />
                <span>Publish to New Repository</span>
              </button>
            </div>

            {/* Workflow Info Cards */}
            <div className="pt-3 border-t border-[#1C1C26] text-left space-y-2 text-[10px]">
              <div className="flex items-start gap-2 text-slate-400">
                <CloudSyncRoundedIcon sx={{ fontSize: 14, color: "#38D9A9", marginTop: "1px" }} />
                <div>
                  <span className="font-bold text-slate-200 block">MicroVM Kernel Sync</span>
                  <span>Deploy code automatically on push.</span>
                </div>
              </div>
              <div className="flex items-start gap-2 text-slate-400">
                <LockRoundedIcon sx={{ fontSize: 14, color: "#E5C07B", marginTop: "1px" }} />
                <div>
                  <span className="font-bold text-slate-200 block">Governance Auditing</span>
                  <span>Every commit is cryptographically hashed.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="w-full text-center text-[9px] text-slate-500 pt-2 border-t border-[#161620]">
            AgentVerse Version Control System v2.4
          </div>
        </div>
      ) : (
        /* State B: Connected Version Control Workspace */
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3 no-scrollbar">
          {/* Linked Repo Header Bar */}
          <div className="p-2 rounded-md bg-[#12121A] border border-[#222230] flex items-center justify-between text-[10px]">
            <div className="flex items-center gap-1.5 min-w-0">
              <GitHubIcon sx={{ fontSize: 14, color: "#38D9A9" }} />
              <span className="font-bold text-slate-200 truncate" title={githubRepo || "nuuvixx/agent"}>
                {githubRepo || "nuuvixx/agent"}
              </span>
            </div>
            {onDisconnectGithub && (
              <button
                onClick={onDisconnectGithub}
                title="Disconnect GitHub repository"
                className="text-slate-500 hover:text-red-400 transition-colors p-0.5"
              >
                <LinkOffRoundedIcon sx={{ fontSize: 13 }} />
              </button>
            )}
          </div>

          {/* Commit Message Box */}
          <div className="space-y-1.5">
            <div className="relative">
              <textarea
                rows={2}
                value={commitMsg}
                onChange={(e) => setCommitMsg(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    handleCommit();
                  }
                }}
                placeholder="Commit message (Ctrl+Enter)"
                className="w-full bg-[#111116] border border-[#22222A] rounded-[4px] px-2.5 py-1.5 text-[11px] text-[#E6EDF3] placeholder-[#4D4D5E] font-mono focus:outline-none focus:border-[#3A3A46] resize-none"
              />
            </div>

            <button
              onClick={handleCommit}
              disabled={!commitMsg.trim() || !hasChanges || isCommitting}
              className={cn(
                "w-full h-7 rounded-[4px] text-[10px] font-mono font-medium flex items-center justify-center gap-1.5 transition-colors",
                commitMsg.trim() && hasChanges && !isCommitting
                  ? "bg-[#10B981] hover:bg-[#059669] text-black font-bold shadow-md shadow-emerald-950/40"
                  : "bg-[#171720] text-[#5C5C6C] border border-[#22222E] cursor-not-allowed"
              )}
            >
              <CheckRoundedIcon sx={{ fontSize: 13 }} />
              <span>{isCommitting ? "Syncing..." : `Commit & Push to ${branchName}`}</span>
            </button>

            {statusMessage && (
              <div className="text-[10px] text-[#10B981] font-mono px-1 flex items-center gap-1">
                <DoneAllRoundedIcon sx={{ fontSize: 12 }} />
                <span>{statusMessage}</span>
              </div>
            )}
          </div>

          {/* Changes list */}
          <div className="space-y-1 pt-1">
            <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase tracking-wider text-[#8B8B98] pb-1 border-b border-[#1A1A22]">
              <span>Changes</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-[#1A1A24] text-neutral-300">
                {allChangedFiles.length}
              </span>
            </div>

            {hasChanges ? (
              <div className="space-y-0.5 pt-1">
                {allChangedFiles.map((file) => {
                  const badge = getFileBadge(file);
                  const isActive = activeFile === file;

                  return (
                    <div
                      key={file}
                      onClick={() => onOpenFile(file)}
                      className={cn(
                        "flex items-center justify-between px-2 py-1.5 rounded-[4px] text-[11px] font-mono cursor-pointer transition-colors group",
                        isActive ? "bg-[#16161F] text-white" : "text-[#8B8B98] hover:bg-[#121218] hover:text-white"
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <DescriptionRoundedIcon sx={{ fontSize: 13, color: "#61AFEF" }} />
                        <span className="truncate">{file}</span>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={cn(
                            "text-[9px] font-mono px-1 py-0.2 rounded border font-bold",
                            badge.color
                          )}
                        >
                          {badge.label}
                        </span>

                        {onDiscardFileChange && (
                          <button
                            title="Discard changes"
                            onClick={(e) => {
                              e.stopPropagation();
                              onDiscardFileChange(file);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-0.5 text-[#5C5C6C] hover:text-red-400 transition-all"
                          >
                            <UndoRoundedIcon sx={{ fontSize: 12 }} />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-6 text-center space-y-1.5">
                <div className="w-8 h-8 rounded-full bg-[#14141B] border border-[#22222E] flex items-center justify-center mx-auto text-[#10B981]">
                  <CheckRoundedIcon sx={{ fontSize: 16 }} />
                </div>
                <p className="text-[11px] font-mono text-[#71717A]">Working tree clean</p>
                <p className="text-[9px] font-mono text-[#4D4D5E]">No modified or uncommitted files</p>
              </div>
            )}
          </div>

          {/* AI Suggestions Note */}
          {pendingFileChanges.length > 0 && (
            <div className="p-2 rounded-[4px] bg-[#141822] border border-[#223048] text-[10px] font-mono text-[#82AAFF] flex items-start gap-1.5">
              <AutoAwesomeRoundedIcon sx={{ fontSize: 13, color: "#38D9A9", marginTop: "1px" }} />
              <span>
                {pendingFileChanges.length} AI code change{pendingFileChanges.length > 1 ? "s" : ""} pending review.
              </span>
            </div>
          )}
        </div>
      )}

      {/* Footer Status */}
      <div className="shrink-0 h-7 border-t border-[#1C1C24] px-3 flex items-center justify-between text-[9px] font-mono text-[#5C5C6C] bg-[#090A0E]">
        <span>{isGithubConnected ? `GitHub: ${githubRepo || "linked"}` : "Git status: Unconnected"}</span>
        <span className={cn("flex items-center gap-1", isGithubConnected ? "text-[#10B981]" : "text-[#8B8B98]")}>
          <span className={cn("w-1.5 h-1.5 rounded-full", isGithubConnected ? "bg-[#10B981]" : "bg-[#5C5C6C]")} />
          {isGithubConnected ? "Synchronized" : "Disconnected"}
        </span>
      </div>
    </div>
  );
}
