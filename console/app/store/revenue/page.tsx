"use client";

import React, { useState } from "react";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import { useStore } from "@/hooks/useStore";
import {
  DollarSign,
  TrendingUp,
  CreditCard,
  CheckCircle2,
  Calendar,
  Wallet,
  ArrowUpRight,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

export default function StoreRevenuePage() {
  const { revenue } = useStore();
  const [walletAddress, setWalletAddress] = useState(revenue.payout_wallet);
  const [walletSaved, setWalletSaved] = useState(false);

  const handleSaveWallet = () => {
    setWalletSaved(true);
    setTimeout(() => setWalletSaved(false), 2000);
  };

  return (
    <div className="space-y-5 font-mono">
      <StoreSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              Creator Revenue & x402 Payouts
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              80% Creator Revenue Split
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Real-time analytics for your published agents: gross sales, net builder payouts, active subscribers, and decentralized x402 settlement.
          </p>
        </div>
      </div>

      {/* Revenue Metrics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-[10px] uppercase font-bold tracking-wider">Builder Net (80%)</span>
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {formatCurrency(revenue.builder_net_usd)}
          </div>
          <div className="text-[10px] text-text-muted">Gross: {formatCurrency(revenue.total_revenue_usd)}</div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-[10px] uppercase font-bold tracking-wider">Pending Payout</span>
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400">
            {formatCurrency(revenue.pending_payout_usd)}
          </div>
          <div className="text-[10px] text-text-muted">Next batch: {revenue.next_payout_date}</div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-[10px] uppercase font-bold tracking-wider">Executions Sold</span>
            <TrendingUp className="w-3.5 h-3.5 text-accent-purple" />
          </div>
          <div className="text-2xl font-bold text-text-primary">
            {revenue.total_executions_sold.toLocaleString()}
          </div>
          <div className="text-[10px] text-text-muted">Across {revenue.active_subscribers} active subscribers</div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-1">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-[10px] uppercase font-bold tracking-wider">Platform Share (20%)</span>
            <CreditCard className="w-3.5 h-3.5 text-text-muted" />
          </div>
          <div className="text-2xl font-bold text-text-muted">
            {formatCurrency(revenue.platform_fee_usd)}
          </div>
          <div className="text-[10px] text-text-muted">Covers microVM & hosting</div>
        </div>
      </div>

      {/* Main Split: Daily Earnings History vs Payout Wallet Config */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-xs">
        {/* Left 2 Cols: Daily History */}
        <div className="lg:col-span-2 glass-card rounded-xl p-5 border border-surface-border space-y-4">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Daily Execution & Earnings History
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-surface-200/80 text-[10px] text-text-muted uppercase border-b border-surface-border">
                <tr>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Executions Sold</th>
                  <th className="py-2.5 px-3">Gross Revenue</th>
                  <th className="py-2.5 px-3">Builder Net (80%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {revenue.daily_history.map((row, i) => (
                  <tr key={i} className="hover:bg-surface-100/50 transition-colors">
                    <td className="py-3 px-3 font-bold text-text-primary">{row.date}</td>
                    <td className="py-3 px-3 text-text-secondary">{row.executions.toLocaleString()} runs</td>
                    <td className="py-3 px-3 text-text-muted">{formatCurrency(row.revenue_usd)}</td>
                    <td className="py-3 px-3 text-emerald-400 font-bold">
                      {formatCurrency(row.revenue_usd * 0.8)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Col: Payout Wallet Configuration */}
        <div className="glass-card rounded-xl p-5 border border-surface-border space-y-4">
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
              Settlement Wallet
            </h3>
          </div>

          <p className="text-xs text-text-muted font-sans leading-relaxed">
            Revenue settlements are dispatched every Monday directly to your cryptographic wallet via the Polygon USDC contract.
          </p>

          <div className="space-y-2">
            <label className="text-[10px] text-text-muted uppercase font-bold">Payout Destination</label>
            <input
              type="text"
              value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
              className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary text-xs font-mono"
            />

            <button
              onClick={handleSaveWallet}
              className="w-full py-2 px-3 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1"
            >
              {walletSaved ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  Wallet Saved!
                </>
              ) : (
                <>
                  <span>Save Payout Address</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
