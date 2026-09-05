import React from "react";
import { cn } from "@/lib/utils";
import LinearProgress from "@mui/material/LinearProgress";
import TrendingUpRoundedIcon from "@mui/icons-material/TrendingUpRounded";
import TrendingDownRoundedIcon from "@mui/icons-material/TrendingDownRounded";

// Accept MUI SvgIcon components (React.ElementType covers both Lucide and MUI icons)
interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  icon: React.ElementType;
  iconColor?: string;
  className?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  iconColor = "text-red-400",
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "dark-glass-card p-4 rounded-xl relative overflow-hidden transition-all duration-200 group border border-red-900/30 hover:border-red-600/50 shadow-lg",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-condensed-bold text-neutral-400 uppercase tracking-widest mb-1">
            {title}
          </p>
          <h3 className="text-3xl font-display-huge text-white tracking-tight leading-none text-shadow">
            {value}
          </h3>
        </div>
        <div className={cn("p-2 rounded-lg bg-[#0e0e12] border border-red-900/40 transition-colors group-hover:border-red-600/60 shadow-inner", iconColor)}>
          {/* Renders both Lucide icons (className w-5 h-5) and MUI icons (sx fontSize) */}
          <Icon className="w-5 h-5" sx={{ fontSize: 20 }} />
        </div>
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 flex items-center justify-between text-xs text-neutral-400 font-mono">
          {subtitle && <span className="text-[11px] truncate">{subtitle}</span>}
          {trend && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 font-bold text-[11px] px-1.5 py-0.5 rounded bg-neutral-900 border",
                trend.isPositive ? "text-emerald-400 border-emerald-900/40" : "text-rose-400 border-rose-900/40"
              )}
            >
              {trend.isPositive
                ? <TrendingUpRoundedIcon sx={{ fontSize: 12 }} />
                : <TrendingDownRoundedIcon sx={{ fontSize: 12 }} />
              }
              {trend.value}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
