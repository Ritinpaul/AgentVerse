"use client";

import React, { Suspense } from "react";
import AgentStudioIde from "./AgentStudioIde";

export default function BuildAgentPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0E0F14] flex items-center justify-center text-xs font-mono text-neutral-400">
          Loading Agent Studio IDE...
        </div>
      }
    >
      <AgentStudioIde />
    </Suspense>
  );
}