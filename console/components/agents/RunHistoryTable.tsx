import React from "react";
import { AgentRunRecord } from "@/lib/api";
import { formatCurrency, formatLatency } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Terminal, ShieldCheck, ShieldAlert, ArrowRight } from "lucide-react";
import Link from "next/link";

interface RunHistoryTableProps {
  runs: AgentRunRecord[];
  agentSlug: string;
}

export function RunHistoryTable({ runs, agentSlug }: RunHistoryTableProps) {
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="p-4 border-b border-surface-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm text-text-primary font-mono">
            Execution Run History
          </h3>
          <p className="text-xs text-text-muted">
            Last {runs.length} runs with token spend, duration, and in-runtime Sentinel decisions.
          </p>
        </div>
        <Link
          href={`/monitor?agent=${agentSlug}`}
          className="text-xs font-mono text-primary-light hover:underline flex items-center gap-1"
        >
          Full Trace Explorer <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-surface-200/60 border-b border-surface-border text-text-muted uppercase text-[10px] tracking-wider">
            <tr>
              <th className="p-3.5 pl-4">Run ID</th>
              <th className="p-3.5">Trigger</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5">Duration</th>
              <th className="p-3.5">Tokens</th>
              <th className="p-3.5">Cost</th>
              <th className="p-3.5">GovernOS Policy</th>
              <th className="p-3.5 pr-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {runs.map((run) => (
              <tr key={run.id} className="hover:bg-surface-100/50 transition-colors">
                <td className="p-3.5 pl-4 font-bold text-text-primary">
                  {run.id}
                  <div className="text-[10px] text-text-muted font-normal">{run.timestamp}</div>
                </td>
                <td className="p-3.5">
                  <span className="px-2 py-0.5 rounded bg-surface-50 border border-surface-border text-text-secondary capitalize">
                    {run.trigger}
                  </span>
                </td>
                <td className="p-3.5">
                  <StatusBadge status={run.status as any} size="sm" />
                </td>
                <td className="p-3.5 text-text-secondary">{formatLatency(run.duration_ms)}</td>
                <td className="p-3.5 text-text-secondary">{run.tokens.toLocaleString()}</td>
                <td className="p-3.5 font-bold text-emerald-400">{formatCurrency(run.cost_usd)}</td>
                <td className="p-3.5">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold ${
                      run.policy_decision === "ALLOW"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {run.policy_decision === "ALLOW" ? (
                      <ShieldCheck className="w-3 h-3" />
                    ) : (
                      <ShieldAlert className="w-3 h-3" />
                    )}
                    {run.policy_decision}
                  </span>
                </td>
                <td className="p-3.5 pr-4 text-right">
                  <Link
                    href={`/monitor?trace=${run.id}`}
                    className="p-1.5 rounded-lg bg-surface-50 hover:bg-surface-hover border border-surface-border text-text-muted hover:text-text-primary inline-flex items-center justify-center transition-colors"
                    title="View causal waterfall trace"
                  >
                    <Terminal className="w-3.5 h-3.5" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
