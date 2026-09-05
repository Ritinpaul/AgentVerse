"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import { useStore } from "@/hooks/useStore";
import {
  Key,
  Copy,
  Check,
  RefreshCw,
  Play,
  Pause,
  ArrowRight,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

export default function StorePurchasesPage() {
  const { purchases, rotateApiKey, pauseInstallation } = useStore();
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  const handleCopy = (id: string, key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  return (
    <div className="space-y-5 font-mono">
      <StoreSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              My Agent Installs & API Keys
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              {purchases.length} Active Subscriptions
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Manage your provisioned API credentials, rotate keys with zero downtime, track execution quotas, and enforce monthly spend limits.
          </p>
        </div>
      </div>

      {/* Purchases List */}
      <div className="space-y-4">
        {purchases.map((item) => (
          <div
            key={item.id}
            className="glass-card rounded-xl p-5 border border-surface-border space-y-3"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-text-primary">{item.agent_name}</h3>
                  <span className="text-[10px] text-text-muted">({item.agent_slug})</span>
                  <span
                    className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                      item.status === "active"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-amber-500/20 text-amber-400"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <span className="text-[10px] text-text-muted">Installed on {item.installed_at}</span>
              </div>

              {/* Action Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => pauseInstallation(item.id)}
                  className="px-3 py-1.5 rounded-lg border border-surface-border text-text-secondary hover:text-text-primary text-xs flex items-center gap-1"
                >
                  {item.status === "active" ? (
                    <>
                      <Pause className="w-3 h-3" />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3" />
                      Resume
                    </>
                  )}
                </button>

                <Link
                  href={`/monitor?agent=${item.agent_slug}`}
                  className="px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-200 border border-surface-border text-text-primary text-xs font-semibold flex items-center gap-1"
                >
                  <span>Traces</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* API Key Box */}
            <div className="p-3 rounded-lg bg-[#0B0D14] border border-surface-border flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 truncate">
                <Key className="w-3.5 h-3.5 text-violet-400 shrink-0" />
                <span className="text-text-muted text-[10px] shrink-0 uppercase font-bold">API Key:</span>
                <span className="text-emerald-300 truncate font-bold text-[11px]">{item.api_key}</span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleCopy(item.id, item.api_key)}
                  className="p-1 rounded text-text-muted hover:text-emerald-400 transition-colors"
                  title="Copy API key"
                >
                  {copiedKeyId === item.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>

                <button
                  onClick={() => rotateApiKey(item.id)}
                  className="p-1 rounded text-text-muted hover:text-primary-light transition-colors"
                  title="Rotate API Key"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Quota & Spend Progress */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
              <div className="p-2.5 rounded-lg bg-surface-50 border border-surface-border space-y-1">
                <div className="flex justify-between text-[10px] text-text-muted">
                  <span>Executions Consumed</span>
                  <span className="text-text-primary font-bold">{item.executions_used.toLocaleString()} runs</span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-400 rounded-full w-[45%]" />
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-surface-50 border border-surface-border space-y-1">
                <div className="flex justify-between text-[10px] text-text-muted">
                  <span>Spend vs Monthly Ceiling</span>
                  <span className="text-emerald-400 font-bold">
                    {formatCurrency(item.spend_usd)} / {formatCurrency(item.max_spend_limit_usd)}
                  </span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${(item.spend_usd / item.max_spend_limit_usd) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
