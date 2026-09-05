import React from "react";
import Chip from "@mui/material/Chip";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import CancelRoundedIcon from "@mui/icons-material/CancelRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import RemoveCircleOutlineRoundedIcon from "@mui/icons-material/RemoveCircleOutlineRounded";

interface StatusBadgeProps {
  status: "running" | "active" | "stopped" | "flagged" | "blocked" | "success" | "warning" | "failed";
  showPulse?: boolean;
  className?: string;
  size?: "sm" | "md";
}

const STATUS_CONFIG: Record<string, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ElementType;
}> = {
  running:  { label: "Running",  color: "#34d399", bgColor: "rgba(52,211,153,0.08)",  borderColor: "rgba(52,211,153,0.3)",  icon: CheckCircleRoundedIcon },
  active:   { label: "Active",   color: "#34d399", bgColor: "rgba(52,211,153,0.08)",  borderColor: "rgba(52,211,153,0.3)",  icon: CheckCircleRoundedIcon },
  success:  { label: "Success",  color: "#34d399", bgColor: "rgba(52,211,153,0.08)",  borderColor: "rgba(52,211,153,0.3)",  icon: CheckCircleRoundedIcon },
  stopped:  { label: "Stopped",  color: "#94a3b8", bgColor: "rgba(148,163,184,0.08)", borderColor: "rgba(148,163,184,0.3)", icon: RemoveCircleOutlineRoundedIcon },
  warning:  { label: "Warning",  color: "#fbbf24", bgColor: "rgba(251,191,36,0.08)",  borderColor: "rgba(251,191,36,0.3)",  icon: WarningAmberRoundedIcon },
  flagged:  { label: "Flagged",  color: "#fbbf24", bgColor: "rgba(251,191,36,0.08)",  borderColor: "rgba(251,191,36,0.3)",  icon: WarningAmberRoundedIcon },
  blocked:  { label: "Blocked",  color: "#fb7185", bgColor: "rgba(251,113,133,0.08)", borderColor: "rgba(251,113,133,0.3)", icon: CancelRoundedIcon },
  failed:   { label: "Failed",   color: "#fb7185", bgColor: "rgba(251,113,133,0.08)", borderColor: "rgba(251,113,133,0.3)", icon: CancelRoundedIcon },
};

export function StatusBadge({ status, showPulse = true, className, size = "md" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.stopped;
  const isLive = status === "running" || status === "active";

  return (
    <Chip
      size="small"
      label={config.label}
      icon={
        isLive && showPulse ? (
          <FiberManualRecordIcon
            sx={{
              fontSize: "10px !important",
              color: `${config.color} !important`,
              animation: "pulse 1.5s infinite",
              "@keyframes pulse": {
                "0%, 100%": { opacity: 1 },
                "50%": { opacity: 0.4 },
              },
            }}
          />
        ) : (
          <FiberManualRecordIcon sx={{ fontSize: "10px !important", color: `${config.color} !important` }} />
        )
      }
      sx={{
        height: size === "sm" ? 20 : 24,
        fontSize: size === "sm" ? "10px" : "11px",
        fontFamily: "monospace",
        fontWeight: 600,
        letterSpacing: "0.04em",
        color: config.color,
        backgroundColor: config.bgColor,
        border: `1px solid ${config.borderColor}`,
        borderRadius: "999px",
        "& .MuiChip-label": { px: 1 },
        "& .MuiChip-icon": { ml: 0.75 },
      }}
      className={className}
    />
  );
}
