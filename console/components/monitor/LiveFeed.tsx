"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Terminal, Play, Pause, RotateCcw, Zap, ShieldCheck, CheckCircle2, AlertTriangle } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

interface StreamLog {
  timestamp: string;
  level: "info" | "success" | "warning" | "error" | "governos";
  message: string;
  source: string;
}

const INITIAL_LOGS: StreamLog[] = [
  {
    timestamp: "22:41:02.110",
    level: "info",
    source: "MicroVM[vm-8290]",
    message: "Firecracker sandbox initialized (cold start: 18ms)",
  },
  {
    timestamp: "22:41:02.128",
    level: "info",
    source: "AgentOS",
    message: "Dispatched task to Job Tracker Pro (session: sess_a819fc72)",
  },
  {
    timestamp: "22:41:02.134",
    level: "governos",
    source: "GovernOS",
    message: "ASI02 Scope check: tool 'web_search' scope=read -> ALLOWED",
  },
  {
    timestamp: "22:41:02.420",
    level: "info",
    source: "MCPClient",
    message: "Tool response returned 5 job listings (payload: 14.2 KB)",
  },
  {
    timestamp: "22:41:02.430",
    level: "info",
    source: "LLMClient",
    message: "Generating inference on gemini-2.5-pro (3,120 prompt tokens)",
  },
  {
    timestamp: "22:41:04.080",
    level: "governos",
    source: "GovernOS",
    message: "ASI03 PII Sanitization scan: SSN=0, CC=0, Email=MASKED -> PASS",
  },
  {
    timestamp: "22:41:04.450",
    level: "success",
    source: "AgentOS",
    message: "Run complete! Cost: $0.0836 | Latency: 2,340ms | Violations: 0",
  },
];

const SIMULATED_STREAM_EVENTS = [
  { level: "info", source: "MicroVM[vm-4810]", message: "Heartbeat check OK · Memory: 84MB / 512MB" },
  { level: "governos", source: "GovernOS", message: "ASI09 A2A Escrow check for contract cnt_9981a -> ALLOWED ($0.15 limit)" },
  { level: "info", source: "LLMClient", message: "Inference stream chunk: 'Analyzed 8 candidate resumes for job #982'" },
  { level: "info", source: "MCPClient", message: "MCP server tools.nuuvixx.io/search responded in 142ms" },
  { level: "success", source: "AgentOS", message: "MicroVM snapshot state persisted to local state-plane" },
  { level: "governos", source: "GovernOS", message: "ASI01 Prompt Injection Shield: Zero malicious delimiters detected" },
];

export function LiveFeed() {
  const [logs, setLogs] = useState<StreamLog[]>(INITIAL_LOGS);
  const [isStreaming, setIsStreaming] = useState(true);
  const [speed, setSpeed] = useState<1 | 2 | 5>(1);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll when new logs arrive
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Simulate streaming events
  useEffect(() => {
    if (!isStreaming) return;

    const intervalMs = 2800 / speed;
    const timer = setInterval(() => {
      const randomEvent =
        SIMULATED_STREAM_EVENTS[Math.floor(Math.random() * SIMULATED_STREAM_EVENTS.length)];
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now
        .getMinutes()
        .toString()
        .padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}.${now
        .getMilliseconds()
        .toString()
        .padStart(3, "0")}`;

      setLogs((prev) => [
        ...prev.slice(-60), // Keep last 60 entries
        {
          timestamp: timeStr,
          level: randomEvent.level as StreamLog["level"],
          source: randomEvent.source,
          message: randomEvent.message,
        },
      ]);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isStreaming, speed]);

  const handleClear = useCallback(() => {
    setLogs([]);
  }, []);

  return (
    <div className="flex flex-col h-full rounded-xl bg-[#0B0D14] border border-surface-border overflow-hidden font-mono text-xs">
      {/* Stream Controls Bar */}
      <div className="h-9 bg-surface-200/80 border-b border-surface-border px-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-accent-cyan" />
          <span className="text-[11px] font-bold text-text-primary">
            AgentOS Live Telemetry Stream
          </span>
          <span
            className={`w-2 h-2 rounded-full ${
              isStreaming ? "bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50" : "bg-text-muted"
            }`}
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Speed selector */}
          <div className="flex items-center rounded bg-surface-100 p-0.5 border border-surface-border text-[10px]">
            {[1, 2, 5].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s as 1 | 2 | 5)}
                className={`px-1.5 py-0.5 rounded transition-colors ${
                  speed === s ? "bg-primary text-white font-bold" : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Pause / Resume */}
          <button
            onClick={() => setIsStreaming((prev) => !prev)}
            className="p-1 rounded hover:bg-surface-100 text-text-secondary hover:text-text-primary transition-colors"
            title={isStreaming ? "Pause stream" : "Resume stream"}
          >
            {isStreaming ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          </button>

          {/* Clear */}
          <button
            onClick={handleClear}
            className="p-1 rounded hover:bg-surface-100 text-text-secondary hover:text-text-primary transition-colors"
            title="Clear logs"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Log Output Stream */}
      <div className="flex-1 p-3 space-y-1.5 overflow-y-auto min-h-0 text-[11px]">
        {logs.length === 0 ? (
          <div className="text-center py-8 text-text-muted">
            Terminal buffer cleared. Waiting for new runtime telemetry events...
          </div>
        ) : (
          logs.map((log, i) => {
            const levelColor =
              log.level === "success"
                ? "text-emerald-400"
                : log.level === "governos"
                ? "text-violet-400"
                : log.level === "warning"
                ? "text-amber-400"
                : log.level === "error"
                ? "text-rose-400"
                : "text-text-secondary";

            return (
              <div key={i} className="flex items-start gap-2 leading-relaxed hover:bg-surface-100/30 px-1 rounded">
                <span className="text-[10px] text-text-muted shrink-0 pt-0.5 select-none">
                  {log.timestamp}
                </span>
                <span className="text-[10px] font-bold text-primary-light shrink-0 select-none">
                  [{log.source}]
                </span>
                <span className={`flex-1 break-all ${levelColor}`}>{log.message}</span>
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
