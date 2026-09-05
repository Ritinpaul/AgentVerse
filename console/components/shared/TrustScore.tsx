import React from "react";
import { cn, getTrustScoreColor } from "@/lib/utils";
import { ShieldCheck, ShieldAlert } from "lucide-react";

interface TrustScoreProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  showBadge?: boolean;
  className?: string;
}

export function TrustScore({
  score,
  size = "md",
  showLabel = false,
  showBadge = true,
  className,
}: TrustScoreProps) {
  const theme = getTrustScoreColor(score);

  const radius = size === "sm" ? 14 : size === "md" ? 20 : 28;
  const strokeWidth = size === "sm" ? 3 : size === "md" ? 4 : 5;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const svgSize = (radius + strokeWidth) * 2;

  return (
    <div className={cn("inline-flex items-center gap-2.5", className)}>
      <div className="relative flex items-center justify-center">
        <svg width={svgSize} height={svgSize} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            className="text-surface-border opacity-40"
          />
          {/* Progress circle */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className={cn("transition-all duration-1000 ease-out", theme.color)}
          />
        </svg>

        <span
          className={cn(
            "absolute font-bold font-mono",
            theme.color,
            size === "sm" ? "text-[10px]" : size === "md" ? "text-xs" : "text-sm"
          )}
        >
          {score}
        </span>
      </div>

      {(showLabel || showBadge) && (
        <div className="flex flex-col">
          {showLabel && (
            <span className="text-[10px] uppercase font-semibold text-text-muted tracking-wider">
              Trust Score
            </span>
          )}
          {showBadge && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded border",
                theme.bg,
                theme.color,
                theme.border
              )}
            >
              {score >= 75 ? (
                <ShieldCheck className="w-3 h-3" />
              ) : (
                <ShieldAlert className="w-3 h-3" />
              )}
              {theme.badge}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
