"use client";

import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { EXECUTION_WS_URL } from "@/lib/api";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";
import UnfoldMoreRoundedIcon from "@mui/icons-material/UnfoldMoreRounded";
import UnfoldLessRoundedIcon from "@mui/icons-material/UnfoldLessRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import InfoRoundedIcon from "@mui/icons-material/InfoRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";

export type TermLogLevel = "OK" | "SYS" | "WARN" | "ERR" | "INFO";

export interface TermLog {
  id: string;
  ts: string;
  level: TermLogLevel;
  text: string;
  asiBlock?: { action: string; detail: string; rule: string };
  asiState?: "pending" | "overridden" | "aborted";
}

export interface TermProblem {
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  line?: number;
  source?: string;
}

const LEVEL_COLOR: Record<TermLogLevel, string> = {
  OK: "text-[#10B981]",
  SYS: "text-[#61AFEF]",
  WARN: "text-[#E5C07B]",
  ERR: "text-[#E5252A]",
  INFO: "text-[#8B8B98]",
};

const TABS = ["terminal", "output", "debug", "problems"] as const;
export type TerminalTab = (typeof TABS)[number];

interface IdTerminalProps {
  activeTab: TerminalTab;
  onTabChange: (tab: TerminalTab) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  height: number;
  onResizeHeight: (h: number) => void;
  termLogs: TermLog[];
  outputLines: string[];
  debugLines: string[];
  problems: TermProblem[];
  onCommand: (cmd: string) => void;
  onClear: () => void;
  renderAsiBlock?: (log: TermLog) => React.ReactNode;
  showWatching?: boolean;
  agentId?: string;
}

export function IdTerminal({
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapsed,
  height,
  onResizeHeight,
  termLogs,
  outputLines,
  debugLines,
  problems,
  onCommand,
  onClear,
  renderAsiBlock,
  showWatching,
  agentId,
}: IdTerminalProps) {
  const [inputVal, setInputVal] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number | null>(null);
  const [ptyConnected, setPtyConnected] = useState(false);
  const [useLivePty, setUseLivePty] = useState(true);
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const xtermContainerRef = useRef<HTMLDivElement>(null);
  const xtermInstanceRef = useRef<any>(null);
  const fitAddonRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const dragStartYRef = useRef(0);
  const dragStartHeightRef = useRef(height);

  // Auto-scroll to bottom on new output while the panel is open (for non-PTY tabs)
  useEffect(() => {
    if (collapsed || !bodyRef.current) return;
    bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [termLogs, outputLines, debugLines, problems, collapsed, activeTab]);

  // ── Initialize & Mount xterm.js with WebSocket PTY Bridge ────────────────────
  useEffect(() => {
    if (collapsed || activeTab !== "terminal" || !useLivePty) {
      return;
    }

    let disposed = false;

    async function setupXterm() {
      if (!xtermContainerRef.current) return;

      try {
        const { Terminal } = await import("xterm");
        const { FitAddon } = await import("@xterm/addon-fit");

        if (disposed || !xtermContainerRef.current) return;

        // Clean up previous instance if any
        if (xtermInstanceRef.current) {
          xtermInstanceRef.current.dispose();
          xtermInstanceRef.current = null;
        }

        xtermContainerRef.current.innerHTML = "";

        const term = new Terminal({
          cursorBlink: true,
          theme: {
            background: "#0A0A0C",
            foreground: "#C7C7D1",
            cursor: "#E5252A",
            cursorAccent: "#0A0A0C",
            selectionBackground: "rgba(229, 37, 42, 0.3)",
            black: "#1E1E24",
            red: "#E5252A",
            green: "#10B981",
            yellow: "#E5C07B",
            blue: "#61AFEF",
            magenta: "#C678DD",
            cyan: "#56B6C2",
            white: "#ABB2BF",
            brightBlack: "#5C5C6C",
            brightRed: "#EF4444",
            brightGreen: "#34D399",
            brightYellow: "#FBBF24",
            brightBlue: "#60A5FA",
            brightMagenta: "#E879F9",
            brightCyan: "#38BDF8",
            brightWhite: "#FFFFFF",
          },
          fontFamily: "JetBrains Mono, Menlo, Monaco, Consolas, monospace",
          fontSize: 12,
          lineHeight: 1.25,
          convertEol: true,
          scrollback: 2000,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        term.open(xtermContainerRef.current);
        fitAddon.fit();

        xtermInstanceRef.current = term;
        fitAddonRef.current = fitAddon;

        // Establish WebSocket connection to AgentOS execution plane
        const baseWs = EXECUTION_WS_URL.replace(/^http:\/\//, "ws://").replace(/^https:\/\//, "wss://");
        const targetAgent = agentId || "agent-studio";
        const wsUrl = `${baseWs}/ws/terminal/${targetAgent}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (disposed) {
            ws.close();
            return;
          }
          setPtyConnected(true);
          try {
            fitAddon.fit();
            ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
          } catch {
            // ignore
          }
        };

        ws.onmessage = (event) => {
          if (!disposed && term) {
            term.write(event.data);
          }
        };

        ws.onclose = () => {
          if (!disposed) {
            setPtyConnected(false);
          }
        };

        ws.onerror = () => {
          if (!disposed) {
            setPtyConnected(false);
            term.write("\r\n\x1b[31m[PTY Bridge Offline: Unable to connect to " + wsUrl + "]\x1b[0m\r\n");
            term.write("\x1b[90mEnsure AgentOS Execution Plane (:8012) is active or switch to Simulated Log mode.\x1b[0m\r\n");
          }
        };

        term.onData((data) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "stdin", data }));
          }
        });

      } catch (err) {
        console.error("Failed to initialize xterm.js PTY bridge:", err);
      }
    }

    setupXterm();

    return () => {
      disposed = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (xtermInstanceRef.current) {
        xtermInstanceRef.current.dispose();
        xtermInstanceRef.current = null;
      }
    };
  }, [collapsed, activeTab, useLivePty, agentId, connectionAttempts]);

  // Handle resize for xterm
  useEffect(() => {
    if (activeTab === "terminal" && useLivePty && fitAddonRef.current && xtermInstanceRef.current) {
      try {
        fitAddonRef.current.fit();
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "resize",
              cols: xtermInstanceRef.current.cols,
              rows: xtermInstanceRef.current.rows,
            })
          );
        }
      } catch {
        // ignore
      }
    }
  }, [height, collapsed, activeTab, useLivePty]);

  const reconnectPty = () => {
    setConnectionAttempts((prev) => prev + 1);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = inputVal.trim();
    if (!cmd) return;
    setHistory((prev) => [...prev, cmd]);
    setHistoryIndex(null);
    onCommand(cmd);
    setInputVal("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length === 0) return;
      const nextIdx = historyIndex === null ? history.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIdx);
      setInputVal(history[nextIdx] ?? "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex === null) return;
      const nextIdx = historyIndex + 1;
      if (nextIdx >= history.length) {
        setHistoryIndex(null);
        setInputVal("");
      } else {
        setHistoryIndex(nextIdx);
        setInputVal(history[nextIdx] ?? "");
      }
    } else if (e.key === "Escape") {
      setHistoryIndex(null);
      setInputVal("");
    }
  };

  const severityIcon = (severity: TermProblem["severity"]) => {
    if (severity === "error") return <ErrorOutlineRoundedIcon sx={{ fontSize: 12, color: "#E5252A" }} />;
    if (severity === "warning") return <WarningAmberRoundedIcon sx={{ fontSize: 12, color: "#E5C07B" }} />;
    return <InfoRoundedIcon sx={{ fontSize: 12, color: "#61AFEF" }} />;
  };

  const handleDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    dragStartYRef.current = e.clientY;
    dragStartHeightRef.current = height;
    if (collapsed) onToggleCollapsed();
    const onMove = (ev: MouseEvent) => {
      const deltaY = dragStartYRef.current - ev.clientY;
      onResizeHeight(Math.min(Math.max(120, dragStartHeightRef.current + deltaY), 560));
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const handleClearTerminal = () => {
    if (xtermInstanceRef.current) {
      xtermInstanceRef.current.clear();
    }
    onClear();
  };

  return (
    <div
      className={cn(
        "w-full shrink-0 bg-[#0A0A0C] border-t border-[#1E1E24] flex flex-col overflow-hidden font-mono",
        collapsed ? "h-9" : ""
      )}
      style={collapsed ? undefined : { height }}
    >
      {/* Drag handle */}
      {!collapsed && (
        <div
          onMouseDown={handleDragStart}
          className="h-[5px] -mb-[5px] z-20 cursor-row-resize group relative"
          style={{ background: "transparent" }}
        >
          <div className="absolute inset-x-0 top-1/2 w-full h-px bg-transparent group-hover:bg-[#E5252A]/40 transition-colors" />
        </div>
      )}

      {/* Tab bar */}
      <div className="h-9 shrink-0 flex items-center justify-between px-2 border-b border-[#1C1C24] select-none">
        <div className="flex items-center gap-0.5 h-full">
          {TABS.map((tab) => {
            const active = activeTab === tab && !collapsed;
            const label =
              tab === "terminal"
                ? "TERMINAL"
                : tab === "output"
                ? "OUTPUT"
                : tab === "debug"
                ? "DEBUG CONSOLE"
                : "PROBLEMS";
            const count =
              tab === "problems"
                ? problems.length > 0
                  ? problems.length
                  : ""
                : "";
            return (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                className={cn(
                  "h-full px-3 text-[10px] font-bold tracking-wider transition-colors flex items-center gap-1.5",
                  active
                    ? "text-white border-t-[2px] border-t-[#E5252A] bg-[#111115]"
                    : "text-[#5C5C6C] hover:text-white hover:bg-[#101014] border-t-[2px] border-t-transparent"
                )}
              >
                {tab === "terminal" && <TerminalRoundedIcon sx={{ fontSize: 12 }} />}
                {label}
                {count !== "" && (
                  <span
                    className={cn(
                      "text-[9px] px-1 rounded font-bold",
                      tab === "problems"
                        ? problems.some((p) => p.severity === "error")
                          ? "bg-[#E5252A]/20 text-[#E5252A]"
                          : "bg-[#E5C07B]/20 text-[#E5C07B]"
                        : "bg-[#1C1C26] text-[#8B8B98]"
                    )}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          {activeTab === "terminal" && (
            <div className="flex items-center gap-1.5 mr-2">
              <button
                onClick={() => setUseLivePty((p) => !p)}
                className={cn(
                  "px-2 py-0.5 rounded text-[9px] font-semibold border transition-colors",
                  useLivePty
                    ? "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30 hover:bg-[#10B981]/20"
                    : "bg-[#1E1E24] text-[#8B8B98] border-white/10 hover:text-white"
                )}
                title={useLivePty ? "Switch to simulated command logs" : "Switch to live xterm.js PTY bridge"}
              >
                {useLivePty ? "LIVE PTY" : "LOG MODE"}
              </button>

              {useLivePty && (
                <div className="flex items-center gap-1">
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      ptyConnected ? "bg-[#10B981] shadow-[0_0_6px_#10B981]" : "bg-[#8B8B98]"
                    )}
                  />
                  <span className="text-[9px] text-[#8B8B98]">
                    {ptyConnected ? "CONNECTED" : "OFFLINE"}
                  </span>
                  {!ptyConnected && (
                    <button
                      onClick={reconnectPty}
                      title="Reconnect PTY bridge"
                      className="p-0.5 text-[#8B8B98] hover:text-white rounded"
                    >
                      <RefreshRoundedIcon sx={{ fontSize: 11 }} />
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {showWatching && (
            <span className="text-[10px] text-[#38D9A9] animate-pulse flex items-center gap-1 mr-1">
              ● watching
            </span>
          )}
          <button
            onClick={handleClearTerminal}
            title="Clear"
            className="p-1 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
          >
            <CloseRoundedIcon sx={{ fontSize: 13 }} />
          </button>
          <button
            onClick={onToggleCollapsed}
            title={collapsed ? "Expand Panel" : "Collapse Panel"}
            className="p-1 text-[#5C5C6C] hover:text-white hover:bg-[#16161D] rounded transition-colors"
          >
            {collapsed ? (
              <UnfoldMoreRoundedIcon sx={{ fontSize: 13 }} />
            ) : (
              <UnfoldLessRoundedIcon sx={{ fontSize: 13 }} />
            )}
          </button>
        </div>
      </div>

      {/* Terminal body */}
      {!collapsed && (
        <div
          ref={bodyRef}
          onClick={() => {
            if (activeTab === "terminal") {
              if (useLivePty && xtermInstanceRef.current) {
                xtermInstanceRef.current.focus();
              } else {
                inputRef.current?.focus();
              }
            }
          }}
          className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2 text-[11px] leading-relaxed no-scrollbar cursor-text relative"
        >
          {activeTab === "terminal" && (
            <>
              {useLivePty ? (
                <div
                  ref={xtermContainerRef}
                  className="w-full h-full min-h-[140px] xterm-container"
                  style={{ minHeight: `${Math.max(100, height - 50)}px` }}
                />
              ) : (
                <div className="space-y-0.5">
                  <div className="text-[10px] text-[#4d4d5e] pb-1 border-b border-[#16161D] mb-1">
                    agentverse@workspace ~ bash (Simulated Log Mode) — 80×24
                  </div>
                  {termLogs.map((log) => (
                    <div key={log.id} className="flex items-start gap-2">
                      <span className="text-[#3d3d4a] shrink-0">{log.ts}</span>
                      <span className={`font-bold shrink-0 ${LEVEL_COLOR[log.level]}`}>
                        [{log.level}]
                      </span>
                      <span className="text-[#C7C7D1]">{log.text}</span>
                    </div>
                  ))}
                  {renderAsiBlock &&
                    termLogs
                      .filter((l) => l.asiBlock)
                      .map((l) => <div key={l.id}>{renderAsiBlock(l)}</div>)}

                  <form onSubmit={handleSubmit} className="flex items-center gap-2 pt-1">
                    <span className="text-[#E5252A] font-bold shrink-0">❯</span>
                    <span className="text-[#10B981] shrink-0">agentverse@workspace</span>
                    <span className="text-white shrink-0">$</span>
                    <input
                      ref={inputRef}
                      type="text"
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      onKeyDown={handleKeyDown}
                      className="flex-1 bg-transparent text-[#E6EDF3] focus:outline-none border-none p-0 font-mono text-[11px]"
                      placeholder="type `agent run <slug>`, `python tools.py`, or `help`"
                      autoComplete="off"
                      spellCheck={false}
                    />
                  </form>
                </div>
              )}
            </>
          )}

          {activeTab === "output" && (
            <div className="space-y-0.5">
              {outputLines.length === 0 && (
                <div className="text-[#4d4d5e] text-[11px]">
                  [No output recorded. Run the agent to capture execution output.]
                </div>
              )}
              {outputLines.map((line, i) => (
                <div key={i} className="text-[#C7C7D1] whitespace-pre-wrap break-words">
                  {line}
                </div>
              ))}
            </div>
          )}

          {activeTab === "debug" && (
            <div className="space-y-0.5">
              {debugLines.length === 0 && (
                <div className="text-[#4d4d5e] text-[11px]">
                  [Debug console — execution traces will appear while the agent runs.]
                </div>
              )}
              {debugLines.map((line, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-[#3d3d4a] shrink-0">
                    {line.startsWith("DBG") ? "DBG" : "TRC"}
                  </span>
                  <span className="text-[#E6EDF3]">{line}</span>
                </div>
              ))}
            </div>
          )}

          {activeTab === "problems" && (
            <div>
              {problems.length === 0 ? (
                <div className="text-[#4d4d5e] text-[11px] flex items-center gap-1.5">
                  <CheckCircleRoundedIcon sx={{ fontSize: 12, color: "#10B981" }} />
                  No governance problems detected in the current manifest.
                </div>
              ) : (
                <div className="space-y-1">
                  {problems.map((p, i) => (
                    <div key={i} className="flex items-start gap-2 text-[11px]">
                      {severityIcon(p.severity)}
                      <span className="text-[#E6EDF3]">{p.message}</span>
                      <span className="ml-auto shrink-0 text-[#3d3d4a]">
                        [{p.source ?? "GovernOS"}] · line {p.line ?? "?"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 pt-2 border-t border-[#1C1C24] flex items-center gap-3 text-[10px] text-[#888899]">
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#E5252A]" />{" "}
                  {problems.filter((p) => p.severity === "error").length} errors
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#E5C07B]" />{" "}
                  {problems.filter((p) => p.severity === "warning").length} warnings
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#61AFEF]" />{" "}
                  {problems.filter((p) => p.severity === "info").length} infos
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}