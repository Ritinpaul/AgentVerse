import React, { useState } from "react";
import { AgentListing } from "@/lib/api";
import { Copy, Check, Cpu, Lock, Coins, Clock } from "lucide-react";

interface RuntimeConfigViewerProps {
  agent: AgentListing;
}

export function RuntimeConfigViewer({ agent }: RuntimeConfigViewerProps) {
  const [copied, setCopied] = useState(false);

  const model = agent.runtime?.model || "gemini-1.5-flash";
  const fallbackModel = agent.runtime?.fallback_model || "gpt-4o-mini";
  const maxTokens = agent.runtime?.max_tokens ?? 4096;
  const timeoutSeconds = agent.runtime?.timeout_seconds ?? 30;
  const version = agent.version || (agent as any).current_version || "1.0.0";
  const price = agent.price_per_execution ?? 0.05;
  const policySet = agent.governance?.policy_set || "enterprise-strict-v1";
  const asiScanStatus = agent.governance?.asi_scan_status || "passed";
  const criticalFindings = agent.governance?.critical_findings ?? 0;

  const formattedYaml = `name: ${agent.slug}
version: "${version}"
description: "${agent.description || ""}"

runtime:
  model: ${model}
  fallback_model: ${fallbackModel}
  max_tokens: ${maxTokens}
  timeout_seconds: ${timeoutSeconds}

budget:
  price_per_execution_usd: ${price}
  alert_threshold: 0.80

governance:
  policy_set: ${policySet}
  asi_scan_status: ${asiScanStatus}
  critical_findings: ${criticalFindings}`;

  const handleCopy = () => {
    navigator.clipboard?.writeText(formattedYaml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Parameter Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-3.5 rounded-xl bg-surface-100 border border-surface-border text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-text-muted">
            <Cpu className="w-3.5 h-3.5 text-primary-light" />
            <span>Primary Model</span>
          </div>
          <div className="font-mono font-bold text-text-primary text-sm">
            {model}
          </div>
          <div className="text-[10px] text-text-muted font-mono">
            Fallback: {fallbackModel}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-100 border border-surface-border text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-text-muted">
            <Coins className="w-3.5 h-3.5 text-emerald-400" />
            <span>Hard Token Ceiling</span>
          </div>
          <div className="font-mono font-bold text-emerald-400 text-sm">
            {maxTokens.toLocaleString()}
          </div>
          <div className="text-[10px] text-text-muted font-mono">
            Enforced by MicroVM
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-100 border border-surface-border text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-text-muted">
            <Clock className="w-3.5 h-3.5 text-accent-cyan" />
            <span>Execution Timeout</span>
          </div>
          <div className="font-mono font-bold text-text-primary text-sm">
            {timeoutSeconds}s
          </div>
          <div className="text-[10px] text-text-muted font-mono">
            Scale-to-zero idle
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-100 border border-surface-border text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-text-muted">
            <Lock className="w-3.5 h-3.5 text-accent-purple" />
            <span>Policy Set</span>
          </div>
          <div className="font-mono font-bold text-accent-purple text-sm truncate">
            {policySet}
          </div>
          <div className="text-[10px] text-emerald-400 font-mono">
            ASI Scan: {asiScanStatus.toUpperCase()}
          </div>
        </div>
      </div>

      {/* YAML Manifest Container */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="h-10 bg-surface-200/80 border-b border-surface-border px-4 flex items-center justify-between text-xs text-text-secondary font-mono">
          <span>agent.yaml (Active Manifest)</span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-100 hover:bg-surface-hover border border-surface-border text-[11px] text-text-primary transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Copy YAML"}</span>
          </button>
        </div>

        <pre className="p-4 bg-[#0B0D14] text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed">
          {formattedYaml}
        </pre>
      </div>
    </div>
  );
}
