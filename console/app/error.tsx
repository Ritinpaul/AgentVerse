"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global App Router Error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#070709] text-white flex flex-col items-center justify-center p-6 text-center">
      <div className="p-4 rounded-2xl bg-red-950/40 border border-red-800/40 mb-6 text-red-400">
        <ErrorOutlineRoundedIcon sx={{ fontSize: 48 }} />
      </div>
      <h1 className="text-3xl font-bold tracking-tight mb-2">SYSTEM ERROR DETECTED</h1>
      <p className="text-sm text-slate-400 max-w-md mb-8 font-mono">
        {error.message || "An unexpected error occurred within the AgentVerse Console execution runtime."}
      </p>
      <div className="flex items-center gap-4">
        <button
          onClick={() => reset()}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs tracking-wider uppercase transition-all"
        >
          <RefreshRoundedIcon sx={{ fontSize: 16 }} />
          <span>RETRY SYSTEM</span>
        </button>
        <Link
          href="/"
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs tracking-wider uppercase transition-all"
        >
          <DashboardRoundedIcon sx={{ fontSize: 16 }} />
          <span>RETURN TO HOME</span>
        </Link>
      </div>
    </div>
  );
}
