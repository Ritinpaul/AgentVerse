import React from "react";
import { useSystemHealth } from "@/hooks/useGovernance";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";

const SERVICE_PILLS = [
  { key: "store", label: "Store", title: "AgentStore Marketplace Service" },
  { key: "os", label: "OS", title: "AgentOS Control Plane Kernel" },
  { key: "govern", label: "Govern", title: "AgentGovernOS Governance Sentinel" },
];

export function ServerStatusPill() {
  const health = useSystemHealth();

  return (
    <div className="hidden lg:flex items-center gap-2 px-2 py-1 rounded-full bg-black/40 border border-white/10 backdrop-blur-md">
      {SERVICE_PILLS.map((svc, i) => (
        <React.Fragment key={svc.key}>
          {i > 0 && <span className="text-white/10 text-xs select-none">|</span>}
          <Tooltip title={svc.title} arrow placement="bottom">
            <Chip
              size="small"
              icon={
                <FiberManualRecordIcon
                  sx={{
                    fontSize: "8px !important",
                    color: "#10b981 !important",
                    animation: "pulse 1.5s infinite",
                    "@keyframes pulse": {
                      "0%, 100%": { opacity: 1 },
                      "50%": { opacity: 0.35 },
                    },
                    filter: "drop-shadow(0 0 4px rgba(16,185,129,0.8))",
                  }}
                />
              }
              label={svc.label}
              sx={{
                height: 20,
                bgcolor: "transparent",
                color: "#e2e8f0",
                fontSize: "11px",
                fontFamily: "monospace",
                fontWeight: 500,
                "& .MuiChip-label": { px: 0.5, pr: 0.75 },
                "& .MuiChip-icon": { ml: 0.5 },
              }}
            />
          </Tooltip>
        </React.Fragment>
      ))}
    </div>
  );
}
