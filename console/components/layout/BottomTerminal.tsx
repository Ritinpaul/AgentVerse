"use client";

import React, { useState, useEffect, useRef } from "react";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";
import OpenInFullRoundedIcon from "@mui/icons-material/OpenInFullRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";

interface TerminalEntry {
  id: string;
  time?: string;
  prefix?: string;
  text: string;
  type?: "ok" | "sys" | "warn" | "err";
}

export function BottomTerminal() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<"terminal" | "output" | "logs">("terminal");
  const [inputVal, setInputVal] = useState("");
  const [logs, setLogs] = useState<TerminalEntry[]>([
    { id: "1", prefix: "[ OK ]", text: "Initializing neural pathways...", type: "ok" },
    { id: "2", prefix: "[ OK ]", text: "Loading protocol buffers...", type: "ok" },
    { id: "3", prefix: "[ SYS ]", text: "Connecting to global governance registry...", type: "sys" },
    { id: "4", prefix: "[ OK ]", text: "System ready. 4 MicroVMs online.", type: "ok" },
  ]);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const cmd = inputVal.trim();
    const newEntry: TerminalEntry = { id: String(Date.now()), text: `admin@agentverse:~$ ${cmd}` };

    let response: TerminalEntry | null = null;
    if (cmd === "clear") {
      setLogs([]);
      setInputVal("");
      return;
    } else if (cmd === "help") {
      response = { id: String(Date.now() + 1), prefix: "[ SYS ]", text: "Commands: status, agents, deploy, clear, help", type: "sys" };
    } else if (cmd === "status") {
      response = { id: String(Date.now() + 1), prefix: "[ OK ]", text: "Kernel v4.2.0 | Status: ONLINE | 4 Active Agents", type: "ok" };
    } else if (cmd === "agents") {
      response = { id: String(Date.now() + 1), prefix: "[ OK ]", text: "nuuvixx-job-tracker (Active), cloudscale-k8s-cost-cutter (Active), nuuvixx-settlement-broker (Active), acme-docu-verify (Active)", type: "ok" };
    } else if (cmd.startsWith("deploy") || cmd.startsWith("av run")) {
      response = { id: String(Date.now() + 1), prefix: "[ OK ]", text: "Deploying agent container to MicroVM sandbox...", type: "ok" };
    } else {
      response = { id: String(Date.now() + 1), prefix: "[ WARN ]", text: `Command executed: ${cmd}`, type: "warn" };
    }

    setLogs((prev) => [...prev, newEntry, ...(response ? [response] : [])]);
    setInputVal("");
  };

  return (
    <div
      className={`w-full bg-[#141619]/95 backdrop-blur-md border-t-2 border-[#E5252A] transition-all flex flex-col shrink-0 text-white font-mono z-30 ${
        isCollapsed ? "h-9" : "h-44"
      }`}
    >
      {/* Header bar */}
      <div className="h-9 px-4 bg-[#181A1D] flex items-center justify-between border-b border-white/10 select-none text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setActiveTab("terminal"); setIsCollapsed(false); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-t-lg transition-colors ${
              activeTab === "terminal" && !isCollapsed
                ? "bg-[#22252A] text-white font-bold border-t-2 border-[#E5252A]"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <TerminalRoundedIcon sx={{ fontSize: 13, color: "#E5252A" }} />
            <span>TERMINAL</span>
          </button>
          <button
            onClick={() => { setActiveTab("output"); setIsCollapsed(false); }}
            className={`px-3 py-1 rounded-t-lg transition-colors ${
              activeTab === "output" && !isCollapsed
                ? "bg-[#22252A] text-white font-bold border-t-2 border-[#E5252A]"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <span>OUTPUT</span>
          </button>
          <button
            onClick={() => { setActiveTab("logs"); setIsCollapsed(false); }}
            className={`px-3 py-1 rounded-t-lg transition-colors ${
              activeTab === "logs" && !isCollapsed
                ? "bg-[#22252A] text-white font-bold border-t-2 border-[#E5252A]"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <span>LOGS</span>
          </button>
        </div>

        <div className="flex items-center gap-2 text-neutral-400">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:text-white rounded-lg hover:bg-white/10"
            title={isCollapsed ? "Expand Terminal" : "Collapse Terminal"}
          >
            <OpenInFullRoundedIcon sx={{ fontSize: 12 }} />
          </button>
          <button
            onClick={() => setLogs([])}
            className="p-1 hover:text-white rounded-lg hover:bg-white/10"
            title="Clear Terminal"
          >
            <CloseRoundedIcon sx={{ fontSize: 13 }} />
          </button>
        </div>
      </div>

      {/* Terminal Body */}
      {!isCollapsed && (
        <div className="flex-1 p-3 overflow-y-auto text-xs space-y-1 bg-[#141619] leading-relaxed">
          <div className="text-neutral-400 text-[11px] pb-1 border-b border-white/5">
            AgentVerse Kernel v4.2.0 (build 8821)
          </div>

          {logs.map((log) => (
            <div key={log.id} className="flex items-start gap-2">
              {log.prefix && (
                <span
                  className={`font-bold shrink-0 ${
                    log.type === "ok"
                      ? "text-[#10B981]"
                      : log.type === "sys"
                      ? "text-[#E5252A]"
                      : log.type === "warn"
                      ? "text-[#FBBF24]"
                      : "text-white"
                  }`}
                >
                  {log.prefix}
                </span>
              )}
              <span className="text-neutral-200">{log.text}</span>
            </div>
          ))}

          <div ref={bottomRef} />

          {/* Prompt line */}
          <form onSubmit={handleCommand} className="flex items-center gap-2 pt-1">
            <span className="text-[#E5252A] font-bold shrink-0">admin@agentverse:~$</span>
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              className="flex-1 bg-transparent text-white focus:outline-none border-none p-0 font-mono text-xs"
              autoFocus
            />
          </form>
        </div>
      )}
    </div>
  );
}
