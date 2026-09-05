"use client";

import React from "react";
import { useAgents } from "@/hooks/useAgents";
import { AgentCard } from "@/components/shared/AgentCard";
import { Bot, Search, Filter, Plus } from "lucide-react";
import Link from "next/link";

export default function AgentsPage() {
  const { agents, searchQuery, setSearchQuery, selectedCategory, setSelectedCategory, categories } = useAgents();


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono text-text-primary">
              Agents Fleet & MicroVMs
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary-light font-mono font-medium">
              {agents.length} Registered
            </span>
          </div>
          <p className="text-xs text-text-secondary">
            Manage your stateful autonomous agents, configure runtime limits, and inspect microVM snapshots.
          </p>
        </div>

        <Link
          href="/build"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Deploy New Agent
        </Link>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by agent name, slug, or model..."
            className="w-full bg-surface-100 border border-surface-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary/60 font-mono"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                selectedCategory === cat
                  ? "bg-surface-50 text-text-primary border border-surface-border"
                  : "text-text-muted hover:text-text-secondary hover:bg-surface-100"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Agents Grid */}
      {agents.length === 0 ? (
        <div className="py-16 px-6 rounded-2xl bg-surface-100 border border-surface-border flex flex-col items-center justify-center gap-3 text-center">
          <Bot className="w-10 h-10 text-text-muted" />
          <div>
            <p className="text-sm font-bold text-text-primary font-mono">No registered agents in fleet</p>
            <p className="text-xs text-text-secondary mt-1">You have removed all agents from your workspace registry.</p>
          </div>
          <Link
            href="/build"
            className="mt-3 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            Deploy New Agent
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onRun={(slug) => {
                alert(`Executing ${slug} via AgentOS local control plane...`);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
