"use client";

import { useState, useCallback } from "react";
import { AgentListing } from "@/lib/api";

export interface InstalledAgentRecord {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_slug: string;
  api_key: string;
  installed_at: string;
  executions_used: number;
  spend_usd: number;
  status: "active" | "paused" | "rate_limited";
  max_spend_limit_usd: number;
}

export interface CreatorRevenueMetrics {
  total_revenue_usd: number;
  builder_net_usd: number;
  platform_fee_usd: number;
  total_executions_sold: number;
  active_subscribers: number;
  pending_payout_usd: number;
  next_payout_date: string;
  payout_wallet: string;
  daily_history: Array<{ date: string; executions: number; revenue_usd: number }>;
}

export interface A2AContract {
  id: string;
  contract_hash: string;
  initiator_agent: string;
  provider_agent: string;
  escrow_amount_usd: number;
  status: "active" | "settled" | "disputed" | "escrow_locked";
  handshake_protocol: string;
  created_at: string;
  settled_at?: string;
  sla_latency_ms_max: number;
  actual_latency_ms?: number;
}

export interface MultiAgentComposition {
  id: string;
  title: string;
  description: string;
  author: string;
  agents_involved: Array<{ slug: string; name: string; share_pct: number }>;
  total_executions: number;
  price_per_pipeline_run: number;
  trust_score: number;
}

const INITIAL_PURCHASES: InstalledAgentRecord[] = [];


const INITIAL_REVENUE: CreatorRevenueMetrics = {
  total_revenue_usd: 0.0,
  builder_net_usd: 0.0,
  platform_fee_usd: 0.0,
  total_executions_sold: 0,
  active_subscribers: 0,
  pending_payout_usd: 0.0,
  next_payout_date: "—",
  payout_wallet: "Not configured",
  daily_history: [],
};

const INITIAL_A2A_CONTRACTS: A2AContract[] = [];

const INITIAL_COMPOSITIONS: MultiAgentComposition[] = [];

export function useStore() {
  const [purchases, setPurchases] = useState<InstalledAgentRecord[]>(INITIAL_PURCHASES);
  const [revenue] = useState<CreatorRevenueMetrics>(INITIAL_REVENUE);
  const [contracts, setContracts] = useState<A2AContract[]>(INITIAL_A2A_CONTRACTS);
  const [compositions] = useState<MultiAgentComposition[]>(INITIAL_COMPOSITIONS);

  const rotateApiKey = useCallback((id: string) => {
    const newKey = `nvx_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
    setPurchases((prev) =>
      prev.map((p) => (p.id === id ? { ...p, api_key: newKey } : p))
    );
  }, []);

  const pauseInstallation = useCallback((id: string) => {
    setPurchases((prev) =>
      prev.map((p) =>
        p.id === id
          ? { ...p, status: p.status === "active" ? ("paused" as const) : ("active" as const) }
          : p
      )
    );
  }, []);

  const settleContract = useCallback((id: string) => {
    setContracts((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              status: "settled" as const,
              settled_at: "Just now",
              actual_latency_ms: Math.floor(800 + Math.random() * 600),
            }
          : c
      )
    );
  }, []);

  return {
    purchases,
    revenue,
    contracts,
    compositions,
    totalInstalled: purchases.length,
    activeContractsCount: contracts.filter((c) => c.status === "active" || c.status === "escrow_locked").length,
    rotateApiKey,
    pauseInstallation,
    settleContract,
  };
}
