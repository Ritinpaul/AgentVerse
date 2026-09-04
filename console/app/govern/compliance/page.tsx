"use client";

import React, { useState, useCallback } from "react";
import { GovernSubNav } from "@/components/govern/GovernSubNav";
import { useGovernance } from "@/hooks/useGovernance";
import {
  Award,
  CheckCircle2,
  ShieldCheck,
  Download,
  Copy,
  Check,
  FileCheck,
  Lock,
} from "lucide-react";

export default function CompliancePage() {
  const { complianceFrameworks, complianceScore } = useGovernance();
  const [copiedBadge, setCopiedBadge] = useState<string | null>(null);

  const handleCopyBadge = (id: string) => {
    const badgeMarkdown = `[![AgentVerse Certified](https://agentverse.io/badges/${id}-certified.svg)](https://agentverse.io/compliance/${id})`;
    navigator.clipboard.writeText(badgeMarkdown);
    setCopiedBadge(id);
    setTimeout(() => setCopiedBadge(null), 2000);
  };

  return (
    <div className="space-y-5 font-mono">
      <GovernSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              Enterprise Regulatory Compliance Badges
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              Score: {complianceScore}%
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Continuous cryptographic verification matrix covering SOC2 Type II, HIPAA HITECH, GDPR, and the EU AI Act.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => alert("Downloading continuous compliance report (PDF / Audit Pack)...")}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white font-semibold shadow-sm transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Export Audit Pack (PDF)
          </button>
        </div>
      </div>

      {/* Framework Badges Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {complianceFrameworks.map((fw) => (
          <div
            key={fw.id}
            className="glass-card rounded-xl p-5 border border-surface-border space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <div>
                  <h3 className="font-bold text-sm text-text-primary">{fw.name}</h3>
                  <span className="text-[10px] text-text-muted">Standard: {fw.version}</span>
                </div>
              </div>

              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                  fw.status === "Certified"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-cyan-500/20 text-cyan-400"
                }`}
              >
                {fw.status}
              </span>
            </div>

            <p className="text-xs text-text-muted font-sans leading-relaxed">{fw.description}</p>

            {/* Controls Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-text-muted">Continuous Controls Passed</span>
                <span className="text-emerald-400 font-bold">
                  {fw.controls_passed} / {fw.controls_total} ({fw.score}%)
                </span>
              </div>
              <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{ width: `${(fw.controls_passed / fw.controls_total) * 100}%` }}
                />
              </div>
            </div>

            {/* Embed Badge Copy Button */}
            <div className="pt-2 border-t border-surface-border/60 flex items-center justify-between text-[10px]">
              <span className="text-text-muted">Last verified: {fw.last_audit_date}</span>
              <button
                onClick={() => handleCopyBadge(fw.id)}
                className="flex items-center gap-1 text-primary-light hover:underline font-bold"
              >
                {copiedBadge === fw.id ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    Copied Markdown!
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy Embed Badge
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
