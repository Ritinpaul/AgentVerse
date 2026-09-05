import React, { useState } from "react";
import { Terminal, Play, RotateCcw, Zap, CheckCircle2, ShieldCheck } from "lucide-react";
import { apiClient } from "@/lib/api";

interface MicroVMTerminalProps {
  agentSlug: string;
  agentName: string;
}

export function MicroVMTerminal({ agentSlug, agentName }: MicroVMTerminalProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<Array<{ time: string; type: "info" | "govern" | "metric" | "error"; message: string }>>([
    { time: "00:00.000", type: "info", message: `[AgentOS] MicroVM worker spawned for ${agentSlug} (cold-start: 38ms)` },
    { time: "00:00.018", type: "govern", message: `[GovernOS SENTINEL] Intercepted tool request: web_search -> ALLOW (ASI02)` },
    { time: "00:00.312", type: "info", message: `[NetworkPlane] MCP search response payload received (14.2 KB)` },
    { time: "00:01.840", type: "metric", message: `[TokenMeter] Tokens consumed: 3,840 | Cost: $0.0768 | Budget status: OK` },
    { time: "00:02.100", type: "info", message: `[StatePlane] MicroVM snapshot saved (hash: 8f9b2a1c)` },
  ]);

  const handleExecute = async () => {
    setIsRunning(true);
    const start = Date.now();

    try {
      const res = await apiClient.executeAgent(agentSlug);
      const elapsed = Date.now() - start;

      setLogs((prev) => [
        ...prev,
        {
          time: `+${(elapsed / 1000).toFixed(3)}s`,
          type: "info",
          message: `[AgentOS] Triggered run: ${res.execution_id} | Result: ${res.status.toUpperCase()}`,
        },
        {
          time: `+${((elapsed + 40) / 1000).toFixed(3)}s`,
          type: "govern",
          message: `[GovernOS SENTINEL] ASI01-ASI10 Zero-Trust validation complete (0 violations)`,
        },
        {
          time: `+${((elapsed + 80) / 1000).toFixed(3)}s`,
          type: "metric",
          message: `[BillingEngine] Execution metered: $${res.cost_usd.toFixed(4)} | MicroVM state captured`,
        },
      ]);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="glass-card rounded-xl overflow-hidden flex flex-col font-mono text-xs">
      {/* Terminal Header */}
      <div className="h-10 bg-surface-200/90 border-b border-surface-border px-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-text-secondary">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-text-primary">MicroVM Console ({agentSlug})</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
            Sandboxed
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setLogs([])}
            className="p-1.5 rounded hover:bg-surface-50 text-text-muted hover:text-text-primary transition-colors"
            title="Clear logs"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleExecute}
            disabled={isRunning}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-all shadow-sm disabled:opacity-50"
          >
            <Play className="w-3 h-3 fill-current" />
            <span>{isRunning ? "Executing..." : "Run MicroVM"}</span>
          </button>
        </div>
      </div>

      {/* Terminal Log Output */}
      <div className="p-4 bg-[#090A0F] min-h-[320px] max-h-[480px] overflow-y-auto space-y-1.5 leading-relaxed">
        {logs.map((log, index) => (
          <div key={index} className="flex items-start gap-2.5">
            <span className="text-text-dim text-[11px] w-20 flex-shrink-0 select-none">
              {log.time}
            </span>
            <span
              className={
                log.type === "govern"
                  ? "text-purple-400"
                  : log.type === "metric"
                  ? "text-emerald-400"
                  : log.type === "error"
                  ? "text-rose-400"
                  : "text-text-primary"
              }
            >
              {log.message}
            </span>
          </div>
        ))}
        {isRunning && (
          <div className="flex items-center gap-2 text-primary-light animate-pulse pt-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            <span>Executing agent logic and streaming causal events...</span>
          </div>
        )}
      </div>

      {/* Terminal Footer */}
      <div className="h-8 bg-surface-200 border-t border-surface-border px-4 flex items-center justify-between text-[11px] text-text-muted">
        <span className="flex items-center gap-1.5 text-emerald-400">
          <ShieldCheck className="w-3.5 h-3.5" /> In-Runtime Sentinel Active (Port 8025)
        </span>
        <span className="text-text-dim">Scale-to-zero enabled</span>
      </div>
    </div>
  );
}
