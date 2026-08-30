"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function ShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Standalone pages (landing, login, register, docs)
  const isStandalonePage =
    pathname === "/" ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/docs");

  // Full-bleed IDE mode: /build/[agentId]
  const isIDERoute =
    pathname.startsWith("/build/") && pathname.split("/").length >= 3;

  // Dedicated Trace Detail Route: /monitor/trace/[traceId]
  const isTraceDetailRoute = pathname.startsWith("/monitor/trace/");

  if (isStandalonePage) {
    return (
      <div className="min-h-screen w-full bg-[#000000] text-white overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    );
  }

  if (isIDERoute) {
    return (
      <div className="h-screen w-screen bg-[#000000] text-white overflow-hidden">
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0A0A0A] text-white">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopNav />

        {isTraceDetailRoute ? (
          // Full-bleed Trace View — handles its own sticky header and internal scrolling
          <main className="flex-1 overflow-hidden bg-[#0A0A0E] text-white flex flex-col min-h-0">
            {children}
          </main>
        ) : (
          // Standard padded content area
          <main className="flex-1 overflow-y-auto p-6 bg-[#0E0F14] text-white">
            <div className="max-w-7xl mx-auto space-y-6">
              {children}
            </div>
          </main>
        )}
      </div>
    </div>
  );
}

