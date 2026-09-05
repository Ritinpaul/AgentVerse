import React from "react";
import { AgentListing } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { TrustScore } from "./TrustScore";
import { formatCurrency, formatNumber } from "@/lib/utils";
import Link from "next/link";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";

// MUI Icons
import MemoryRoundedIcon from "@mui/icons-material/MemoryRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";

interface AgentCardProps {
  agent: AgentListing;
  onRun?: (slug: string) => void;
}

export function AgentCard({ agent, onRun }: AgentCardProps) {
  return (
    <div className="dark-glass-card rounded-xl p-5 relative flex flex-col justify-between group border border-red-900/30 hover:border-red-600/50 shadow-xl transition-all duration-200">
      <div>
        {/* Top bar */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-[#0e0e12] border border-red-900/40 group-hover:border-red-600/60 shadow-inner transition-colors">
              <MemoryRoundedIcon sx={{ fontSize: 20, color: "#f87171" }} />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm group-hover:text-red-400 transition-colors font-mono">
                {agent.name}
              </h4>
              <p className="text-xs font-mono text-neutral-400">{agent.slug}</p>
            </div>
          </div>
          <StatusBadge status={agent.status as any} />
        </div>

        {/* Description */}
        <p className="text-xs text-neutral-300 line-clamp-2 mb-4 leading-relaxed font-sans">
          {agent.description}
        </p>

        {/* Runtime Tags — MUI Chips */}
        <div className="flex flex-wrap items-center gap-1.5 mb-4">
          <Chip
            label={agent.runtime?.model || "gemini-1.5-flash"}
            size="small"
            sx={{
              height: 20, fontSize: "11px", fontFamily: "monospace",
              bgcolor: "rgba(127,29,29,0.25)", color: "#fca5a5",
              border: "1px solid rgba(127,29,29,0.4)", borderRadius: "4px",
              "& .MuiChip-label": { px: 1 },
            }}
          />
          <Chip
            label={agent.category || "General"}
            size="small"
            sx={{
              height: 20, fontSize: "11px", fontFamily: "monospace", fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.05em",
              bgcolor: "#14141a", color: "#cbd5e1",
              border: "1px solid #27272a", borderRadius: "4px",
              "& .MuiChip-label": { px: 1 },
            }}
          />
          <Chip
            label={`v${agent.version || (agent as any).current_version || "1.0.0"}`}
            size="small"
            sx={{
              height: 20, fontSize: "11px", fontFamily: "monospace",
              bgcolor: "#14141a", color: "#a1a1aa",
              border: "1px solid #27272a", borderRadius: "4px",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        </div>
      </div>

      {/* Metrics & Bottom Action */}
      <div className="border-t border-red-900/20 pt-3.5 mt-auto">
        <div className="flex items-center justify-between mb-3.5">
          <TrustScore score={agent.trust_score ?? 95} size="sm" showBadge={false} showLabel={false} />

          <div className="text-right font-mono">
            <div className="text-xs font-bold text-white">
              {formatCurrency(agent.price_per_execution ?? 0.05)}
              <span className="text-[10px] text-neutral-400 font-normal"> /run</span>
            </div>
            <div className="text-[10px] text-red-400 font-semibold">
              {formatNumber(agent.total_executions ?? 0)} runs
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/monitor?agent=${agent.slug}`}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg bg-[#0e0e12] hover:bg-neutral-900 border border-red-900/40 hover:border-red-600/50 text-xs font-condensed-bold tracking-wider text-slate-200 uppercase transition-colors"
          >
            <TerminalRoundedIcon sx={{ fontSize: 14, color: "#94a3b8" }} />
            Traces
          </Link>

          <Tooltip title="Execute Agent locally via AgentOS MicroVM" arrow>
            <IconButton
              onClick={() => onRun?.(agent.slug)}
              size="small"
              sx={{
                bgcolor: "#dc2626",
                color: "white",
                borderRadius: 1.5,
                p: 0.75,
                "&:hover": { bgcolor: "#b91c1c" },
                boxShadow: "0 4px 15px rgba(220,38,38,0.4)",
              }}
            >
              <PlayArrowRoundedIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
