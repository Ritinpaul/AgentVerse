"use client";

import React from "react";
import Link from "next/link";
import CompassIcon from "@mui/icons-material/ExploreRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#070709] text-white flex flex-col items-center justify-center p-6 text-center">
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 mb-6 text-red-500">
        <CompassIcon sx={{ fontSize: 48 }} />
      </div>
      <h1 className="text-4xl font-bold tracking-tight mb-2">404 — ROUTE NOT FOUND</h1>
      <p className="text-sm text-slate-400 max-w-md mb-8 font-mono">
        The requested endpoint or console resource does not exist in the AgentVerse node cluster.
      </p>
      <Link
        href="/"
        className="flex items-center gap-2 px-6 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs tracking-wider uppercase transition-all"
      >
        <DashboardRoundedIcon sx={{ fontSize: 16 }} />
        <span>BACK TO CONSOLE</span>
      </Link>
    </div>
  );
}
