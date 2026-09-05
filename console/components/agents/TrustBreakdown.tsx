import React from "react";
import { TrustFactorBreakdown } from "@/lib/api";
import { ShieldCheck, Award, CheckCircle, Lock, Cpu } from "lucide-react";

interface TrustBreakdownProps {
  score: number;
  factors: TrustFactorBreakdown[];
}

export function TrustBreakdown({ score, factors }: TrustBreakdownProps) {
  const complianceBadges = [
    { label: "SOC 2 Type II", status: "Verified", icon: ShieldCheck, color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
    { label: "HIPAA Compliant", status: "Verified", icon: Lock, color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
    { label: "GDPR Article 28", status: "Verified", icon: CheckCircle, color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10" },
    { label: "ISO 42001 (AI)", status: "Active", icon: Award, color: "text-purple-400 border-purple-500/30 bg-purple-500/10" },
  ];

  return (
    <div className="space-y-6">
      {/* 5-Factor Weighted Dimension Progress Bars */}
      <div className="glass-card rounded-xl p-5 space-y-4">
        <div>
          <h3 className="font-semibold text-sm text-text-primary font-mono flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            GovernOS 5-Factor Trust Algorithm
          </h3>
          <p className="text-xs text-text-muted">
            Composite score computed in real-time across automated security scans, runtime compliance, and reliability telemetry.
          </p>
        </div>

        <div className="space-y-4 pt-2">
          {factors.map((factor) => {
            const pct = Math.round((factor.score / factor.max_score) * 100);

            return (
              <div key={factor.dimension} className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-medium text-text-primary">
                    {factor.dimension}{" "}
                    <span className="text-[10px] text-text-muted">({factor.weight_pct}% weight)</span>
                  </span>
                  <span className="font-bold text-emerald-400">
                    {factor.score}/{factor.max_score} pts ({pct}%)
                  </span>
                </div>

                <div className="w-full h-2 rounded-full bg-surface-50 overflow-hidden border border-surface-border">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      pct >= 90
                        ? "bg-emerald-500"
                        : pct >= 75
                        ? "bg-cyan-500"
                        : "bg-amber-500"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>

                <p className="text-[11px] text-text-muted leading-relaxed">{factor.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Official Compliance & Governance Badges */}
      <div className="glass-card rounded-xl p-5 space-y-3">
        <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider font-mono">
          Enterprise Compliance Badges
        </h4>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {complianceBadges.map((badge) => {
            const Icon = badge.icon;

            return (
              <div
                key={badge.label}
                className={`p-3 rounded-lg border flex flex-col items-center justify-center text-center gap-1.5 ${badge.color}`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-bold text-xs font-mono">{badge.label}</span>
                <span className="text-[10px] uppercase font-semibold tracking-wider opacity-80">
                  {badge.status}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
