"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import CircularProgress from "@mui/material/CircularProgress";

export interface ExplorerEntry {
  type: "file" | "folder";
  /** Full relative path, e.g. "agents/research-agent.yaml" */
  path: string;
  name: string;
  lang?: "yaml" | "python" | "json" | "md" | "text" | "sh" | "mcp";
  children?: ExplorerEntry[];
}

export interface ExplorerAgent {
  id: string;
  name: string;
  status: "ready" | "running" | "error" | "idle";
}

const FILE_LANG_COLOR: Record<string, string> = {
  yaml: "#E5C07B",
  python: "#61AFEF",
  json: "#98C379",
  md: "#E06C75",
  sh: "#C678DD",
  mcp: "#56B6C2",
  text: "#8B8B98",
};

function FileDot({ lang }: { lang?: ExplorerEntry["lang"] }) {
  return (
    <span
      className="w-[7px] h-[7px] rounded-[2px] shrink-0"
      style={{ backgroundColor: FILE_LANG_COLOR[lang ?? "text"] }}
    />
  );
}

/** Map a file path to its language id for the colored dot */
export function fileLang(path: string): ExplorerEntry["lang"] {
  if (/\.ya?ml$/.test(path)) return "yaml";
  if (/\.py$/.test(path)) return "python";
  if (/\.json$/.test(path)) return "json";
  if (/\.md$/.test(path)) return "md";
  if (/\.(sh|bash)$/.test(path)) return "sh";
  if (/\.mcp\.json$/.test(path) || path === ".mcp.json") return "mcp";
  return "text";
}

interface IdExplorerProps {
  files: ExplorerEntry[];
  openFiles: string[];
  activeFile: string;
  pendingFileChanges: string[];
  onOpenFile: (path: string) => void;
  onCreateFile: (path: string) => void;
  onDeleteFile?: (path: string) => void;
  onCloseFile?: (path: string) => void;
  agentName?: string;
  loading?: boolean;
}

export function IdExplorer({
  files,
  openFiles,
  activeFile,
  pendingFileChanges,
  onOpenFile,
  onCreateFile,
  onDeleteFile,
  onCloseFile,
  agentName,
  loading,
}: IdExplorerProps) {
  const [expandedSet, setExpandedSet] = useState<Set<string>>(() => {
    const seed = new Set<string>();
    files.forEach((f) => {
      if (f.type === "folder") seed.add(f.path);
    });
    return seed;
  });

  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

  const toggleFolder = (path: string) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  useEffect(() => {
    if (!activeFile) return;
    const folder = activeFile.includes("/") ? activeFile.split("/").slice(0, -1).join("/") : null;
    if (folder) {
      setExpandedSet((prev) => {
        if (prev.has(folder)) return prev;
        const next = new Set(prev);
        next.add(folder);
        return next;
      });
    }
  }, [activeFile]);

  const isExpanded = (path: string) => expandedSet.has(path);

  const handleCreateSubmit = () => {
    const trimmed = newFileName.trim();
    if (trimmed) {
      onCreateFile(trimmed);
    }
    setNewFileName("");
    setIsCreatingFile(false);
  };

  const collapseAll = () => {
    setExpandedSet(new Set());
    setMoreMenuOpen(false);
  };

  const expandAll = () => {
    const allFolders = new Set<string>();
    const collect = (entries: ExplorerEntry[]) => {
      for (const e of entries) {
        if (e.type === "folder") {
          allFolders.add(e.path);
          if (e.children) collect(e.children);
        }
      }
    };
    collect(files);
    setExpandedSet(allFolders);
    setMoreMenuOpen(false);
  };

  const renderNode = (node: ExplorerEntry, depth = 0) => {
    const isFolder = node.type === "folder";
    const indent = depth * 12;

    if (isFolder) {
      const open = isExpanded(node.path);
      return (
        <div key={node.path}>
          <button
            onClick={() => toggleFolder(node.path)}
            className="w-full flex items-center gap-1.5 pr-2 py-[3px] text-[11px] font-medium hover:bg-[#14141B] transition-colors text-left group"
            style={{ paddingLeft: 8 + indent }}
          >
            <span
              className={cn("text-[10px] w-3 text-center transition-transform", open ? "text-[#8B8B98]" : "text-[#5C5C6C]")}
            >
              {open ? "▾" : "▸"}
            </span>
            <span className={cn(open ? "text-[#C7C7D1]" : "text-[#8B8B98]", "font-medium")}>{node.name}</span>
          </button>
          {open && node.children?.map((child) => renderNode(child, depth + 1))}
        </div>
      );
    }

    const isActive = activeFile === node.path;
    const hasPending = pendingFileChanges.includes(node.path);
    const canDelete = onDeleteFile && !["agent.yaml", "tools.py", "memory.json"].includes(node.path);

    return (
      <div
        key={node.path}
        className={cn(
          "w-full flex items-center gap-2 pr-2 py-[3px] text-[11px] font-medium transition-colors text-left border-l-[2px] group cursor-pointer",
          isActive
            ? "bg-[#181820] text-white border-l-[#E5252A]"
            : "border-l-transparent text-[#8B8B98] hover:text-white hover:bg-[#14141B]"
        )}
        style={{ paddingLeft: 8 + indent + 16 }}
        onClick={() => onOpenFile(node.path)}
      >
        <FileDot lang={node.lang} />
        <span className="truncate flex-1">{node.name}</span>
        {hasPending && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse shrink-0" title="AI changes pending" />
        )}
        {canDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDeleteFile(node.path);
            }}
            className="opacity-0 group-hover:opacity-100 p-0.5 text-[#5C5C6C] hover:text-red-400 transition-opacity"
            title="Delete file"
          >
            <CloseRoundedIcon sx={{ fontSize: 11 }} />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="w-[260px] shrink-0 h-full bg-[#0C0C10] border-r border-[#1E1E24] flex flex-col overflow-hidden select-none relative">
      {/* Explorer header */}
      <div className="h-9 shrink-0 flex items-center justify-between px-3 border-b border-[#1C1C24]">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#6E6E7E] font-mono">
          Explorer
        </span>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setIsCreatingFile(true)}
            className="p-1 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
            title="New File"
          >
            <AddRoundedIcon sx={{ fontSize: 14 }} />
          </button>
          <div className="relative">
            <button
              onClick={() => setMoreMenuOpen((v) => !v)}
              className="p-1 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
              title="More Actions"
            >
              <MoreHorizRoundedIcon sx={{ fontSize: 14 }} />
            </button>
            {moreMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-44 bg-[#14141B] border border-[#26262E] rounded-md shadow-2xl z-50 py-1 font-mono text-xs text-neutral-300">
                <button
                  onClick={() => {
                    setIsCreatingFile(true);
                    setMoreMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#1C1C26] hover:text-white transition-colors"
                >
                  + New File
                </button>
                <button
                  onClick={collapseAll}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#1C1C26] hover:text-white transition-colors"
                >
                  Collapse Folders
                </button>
                <button
                  onClick={expandAll}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#1C1C26] hover:text-white transition-colors"
                >
                  Expand Folders
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar">
        {/* Workspace Title & File Tree */}
        <div className="pt-2.5 pb-2">
          <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#8B8B98] font-mono flex items-center justify-between border-b border-[#16161F] mb-1.5">
            <span className="text-white">Workspace Files</span>
            <span className="text-[9px] text-[#5C5C6C] font-mono font-normal">
              {files.length} items
            </span>
          </div>

          {loading && (
            <div className="flex items-center gap-2 px-3 py-1.5 text-[11px] text-[#5C5C6C]">
              <CircularProgress size={10} sx={{ color: "#5C5C6C" }} /> loading…
            </div>
          )}

          {/* Inline New File Creator */}
          {isCreatingFile && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#14141B] border-y border-primary/40 my-1">
              <FileDot lang={fileLang(newFileName)} />
              <input
                autoFocus
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateSubmit();
                  else if (e.key === "Escape") {
                    setIsCreatingFile(false);
                    setNewFileName("");
                  }
                }}
                onBlur={handleCreateSubmit}
                placeholder="e.g. tools/custom.py"
                className="w-full bg-transparent text-[11px] font-mono text-white placeholder-[#5C5C6C] outline-none border-none p-0"
              />
            </div>
          )}

          {files.map((node) => renderNode(node, 0))}
        </div>
      </div>

      {/* Open files footer */}
      {openFiles.length > 0 && (
        <div className="shrink-0 border-t border-[#1C1C24] px-2 py-1.5 bg-[#090A0E]">
          <div className="px-1 pb-1 text-[9px] font-bold uppercase tracking-widest text-[#5C5C6C] font-mono">
            Open Files ({openFiles.length})
          </div>
          <div className="space-y-0.5 max-h-32 overflow-y-auto no-scrollbar">
            {openFiles.map((f) => {
              const active = f === activeFile;
              return (
                <div
                  key={f}
                  onClick={() => onOpenFile(f)}
                  className={cn(
                    "flex items-center gap-2 px-1.5 py-[2px] text-[10px] font-medium rounded cursor-pointer transition-colors group",
                    active ? "bg-[#181820] text-white" : "text-[#71717A] hover:bg-[#14141B] hover:text-white"
                  )}
                >
                  <FileDot lang={fileLang(f)} />
                  <span className="truncate flex-1">{f.split("/").pop()}</span>
                  {onCloseFile && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onCloseFile(f);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-opacity"
                    >
                      <CloseRoundedIcon sx={{ fontSize: 11 }} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}