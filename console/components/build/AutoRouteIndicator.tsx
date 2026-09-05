"use client";

import React from "react";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import KeyRoundedIcon from "@mui/icons-material/KeyRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { RouteDecision } from "@/lib/autoroute";

interface AutoRouteIndicatorProps {
  decision: RouteDecision;
}

export function AutoRouteIndicator({ decision }: AutoRouteIndicatorProps) {
  const isByok = decision.model.tier === "byok";

  return (
    <div
      className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-[#141418] border border-[#272732] rounded text-[10px] font-mono max-w-full overflow-hidden"
      title={decision.reason}
    >
      <AutoAwesomeRoundedIcon sx={{ fontSize: 11, color: isByok ? "#10B981" : "#38D9A9" }} />
      <span className="font-semibold text-white truncate">{decision.model.label}</span>
      <span className="text-neutral-600">•</span>
      <span className="text-neutral-400 capitalize shrink-0">{decision.intent}</span>
      {isByok ? (
        <span className="text-[9px] px-1 bg-[#10B981]/15 text-[#10B981] rounded border border-[#10B981]/30 font-bold flex items-center gap-0.5 shrink-0">
          <KeyRoundedIcon sx={{ fontSize: 9 }} /> BYOK
        </span>
      ) : (
        <span className="text-[9px] px-1 bg-[#38D9A9]/15 text-[#38D9A9] rounded border border-[#38D9A9]/30 font-bold shrink-0">
          FREE
        </span>
      )}
      <InfoOutlinedIcon sx={{ fontSize: 11, color: "#5C5C6C" }} className="shrink-0 ml-0.5" />
    </div>
  );
}
