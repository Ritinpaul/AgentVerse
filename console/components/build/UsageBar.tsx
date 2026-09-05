"use client";

import React, { useState, useEffect } from "react";
import { getDailyUsage, DailyUsage } from "@/lib/autoroute";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";

interface UsageBarProps {
  onOpenKeyModal?: () => void;
}

export function UsageBar({ onOpenKeyModal }: UsageBarProps = {}) {
  const [usage, setUsage] = useState<DailyUsage>(() => getDailyUsage());

  useEffect(() => {
    // Refresh usage state periodically
    const interval = setInterval(() => {
      setUsage(getDailyUsage());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const pct = Math.min(100, Math.max(0, usage.pct));
  const usedFormatted = (usage.tokensUsed / 1000).toFixed(1);
  const limitFormatted = (usage.limit / 1000).toFixed(0);

  const barColor =
    pct > 90
      ? "bg-gradient-to-r from-red-500 to-rose-600"
      : pct > 70
      ? "bg-gradient-to-r from-amber-500 to-yellow-400"
      : "bg-gradient-to-r from-[#10B981] to-[#38D9A9]";

  return (
    <div className="flex items-center gap-2.5 font-sans">
      {/* Sleek Energy Token Meter */}
      <div className="flex flex-col gap-1 min-w-[160px]">
        <div className="flex items-center justify-between gap-3 text-[10px] leading-none">
          <span className="flex items-center gap-1 font-semibold text-neutral-300">
            <BoltRoundedIcon sx={{ fontSize: 13, color: "#10B981" }} />
            <span>Free Daily Credits</span>
          </span>
          <span className="font-mono text-neutral-300 font-bold tracking-tight">
            {usedFormatted}k / {limitFormatted}k tok
          </span>
        </div>

        {/* Progress Bar Container */}
        <div className="h-1.5 w-full bg-[#16161D] rounded-full overflow-hidden border border-[#272734] p-0.5 shadow-inner">
          <div
            className={`h-full ${barColor} transition-all duration-500 ease-out rounded-full`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Exhausted Alert Pill (Only shown when limit reached) */}
      {usage.exhausted && (
        <span className="px-2 py-0.5 bg-[#E5252A]/20 border border-[#E5252A]/50 text-[#E5252A] text-[9px] font-bold rounded-md uppercase tracking-wider animate-pulse">
          Limit Reached
        </span>
      )}
    </div>
  );
}
