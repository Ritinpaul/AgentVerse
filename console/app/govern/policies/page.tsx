"use client";

import React, { useState, useCallback } from "react";
import { GovernSubNav } from "@/components/govern/GovernSubNav";
import { useGovernance, PolicyRule } from "@/hooks/useGovernance";
import {
  Lock,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  Code2,
  Check,
  Trash2,
  RefreshCw,
  Save,
} from "lucide-react";

export default function PoliciesPage() {
  const { policies, togglePolicy, updatePolicyMode, addPolicy } = useGovernance();
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyRule | null>(policies[0] ?? null);
  const [isAddingRule, setIsAddingRule] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // New Rule Form State
  const [newRuleCode, setNewRuleCode] = useState("ASI11");
  const [newRuleName, setNewRuleName] = useState("");
  const [newRuleCategory, setNewRuleCategory] = useState<PolicyRule["category"]>("scope");
  const [newRuleSeverity, setNewRuleSeverity] = useState<PolicyRule["severity"]>("High");
  const [newRuleDescription, setNewRuleDescription] = useState("");

  const handleSave = useCallback(() => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  }, []);

  const handleCreateRule = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!newRuleName) return;

      addPolicy({
        code: newRuleCode,
        name: newRuleName,
        category: newRuleCategory,
        mode: "ENFORCE",
        severity: newRuleSeverity,
        description: newRuleDescription || "Custom user-defined security rule.",
        enabled: true,
        config: { custom_rule: true },
      });

      setIsAddingRule(false);
      setNewRuleName("");
      setNewRuleDescription("");
    },
    [addPolicy, newRuleCode, newRuleName, newRuleCategory, newRuleSeverity, newRuleDescription]
  );

  return (
    <div className="space-y-5">
      <GovernSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-violet-400" />
            <h1 className="text-xl font-bold font-mono text-text-primary">
              Visual Policy Rule Editor
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-mono font-semibold">
              No Raw YAML Required
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Configure in-runtime tool allowlists, rate ceilings, PII redaction rules, and prompt injection filters via visual key-value controls.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAddingRule(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-mono font-semibold shadow-sm transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Security Rule
          </button>

          <button
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold shadow-sm transition-all"
          >
            {saveSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-white" />
                Policies Deployed!
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                Deploy to MicroVM Kernel
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Split: Policies List & Visual Rule Configurator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Rule Catalog */}
        <div className="glass-card rounded-xl p-4 space-y-3 font-mono">
          <div className="flex items-center justify-between text-xs text-text-secondary font-bold uppercase tracking-wider">
            <span>Security Rules ({policies.length})</span>
            <span className="text-[10px] text-text-muted">Zero-Trust</span>
          </div>

          <div className="space-y-2">
            {policies.map((pol) => {
              const isSelected = selectedPolicy?.id === pol.id;

              return (
                <div
                  key={pol.id}
                  onClick={() => setSelectedPolicy(pol)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all space-y-1.5 ${
                    isSelected
                      ? "bg-surface-50 border-primary shadow-md shadow-primary/10"
                      : "bg-surface-100/40 border-surface-border hover:bg-surface-100"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-primary-light">{pol.code}</span>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                          pol.mode === "ENFORCE"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-amber-500/20 text-amber-400"
                        }`}
                      >
                        {pol.mode}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={pol.enabled}
                        onChange={(e) => {
                          e.stopPropagation();
                          togglePolicy(pol.id);
                        }}
                        className="rounded border-surface-border bg-surface-100 text-primary focus:ring-0 cursor-pointer"
                      />
                    </div>
                  </div>

                  <p className="text-xs font-semibold text-text-primary truncate">{pol.name}</p>

                  <div className="flex items-center justify-between text-[10px] text-text-muted border-t border-surface-border/60 pt-1">
                    <span>{pol.enforcements_today.toLocaleString()} gated today</span>
                    <span className="text-amber-400 font-bold">{pol.blocked_count} blocked</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Cols: Visual Rule Configurator */}
        <div className="lg:col-span-2 glass-card rounded-xl p-5 space-y-5 font-mono">
          {selectedPolicy ? (
            <>
              {/* Header Details */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-primary/20 text-primary-light">
                      {selectedPolicy.code}
                    </span>
                    <h2 className="text-base font-bold text-text-primary">
                      {selectedPolicy.name}
                    </h2>
                  </div>
                  <p className="text-xs text-text-muted mt-1 font-sans">
                    {selectedPolicy.description}
                  </p>
                </div>

                {/* Mode Selector */}
                <div className="flex items-center rounded-lg bg-surface-100 p-0.5 border border-surface-border text-xs shrink-0">
                  {(["ENFORCE", "AUDIT", "DISABLED"] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => updatePolicyMode(selectedPolicy.id, mode)}
                      className={`px-2.5 py-1 rounded-md transition-colors ${
                        selectedPolicy.mode === mode
                          ? mode === "ENFORCE"
                            ? "bg-emerald-600 text-white font-bold"
                            : mode === "AUDIT"
                            ? "bg-amber-600 text-white font-bold"
                            : "bg-surface-200 text-text-muted"
                          : "text-text-muted hover:text-text-secondary"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* Visual Parameter Key-Value Grid */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Visual Parameters & Thresholds
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {Object.entries(selectedPolicy.config).map(([key, val]) => (
                    <div
                      key={key}
                      className="p-3 rounded-lg bg-surface-50 border border-surface-border space-y-1"
                    >
                      <span className="text-[10px] text-text-muted uppercase font-bold">{key}</span>
                      <div className="text-xs font-bold text-text-primary">
                        {typeof val === "boolean" ? (
                          <span className={val ? "text-emerald-400" : "text-text-muted"}>
                            {val ? "ENABLED (true)" : "DISABLED (false)"}
                          </span>
                        ) : Array.isArray(val) ? (
                          <span className="text-cyan-300">[{val.join(", ")}]</span>
                        ) : (
                          String(val)
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live Preview of Generated Kernel JSON */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-text-secondary font-bold uppercase tracking-wider">
                  <span>Generated MicroVM Kernel Enforcement Ruleset</span>
                  <Code2 className="w-3.5 h-3.5 text-text-muted" />
                </div>
                <pre className="p-3.5 rounded-xl bg-[#0B0D14] border border-surface-border text-xs text-emerald-300 overflow-x-auto leading-relaxed">
                  {JSON.stringify(
                    {
                      rule_id: selectedPolicy.id,
                      code: selectedPolicy.code,
                      mode: selectedPolicy.mode,
                      severity: selectedPolicy.severity,
                      enforcement: selectedPolicy.config,
                      signed_by: "GovernOS Sentinel Root Key v2",
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-text-muted text-xs">
              Select a security policy rule to edit visual parameters.
            </div>
          )}
        </div>
      </div>

      {/* Modal / Overlay: Add New Security Rule */}
      {isAddingRule && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md glass-card rounded-xl p-5 space-y-4 font-mono border border-surface-border">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <h3 className="text-sm font-bold text-text-primary">Add New Security Rule</h3>
              <button
                onClick={() => setIsAddingRule(false)}
                className="text-text-muted hover:text-text-primary text-xs"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Rule Code (e.g. ASI11)</label>
                <input
                  type="text"
                  value={newRuleCode}
                  onChange={(e) => setNewRuleCode(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Rule Name</label>
                <input
                  type="text"
                  value={newRuleName}
                  onChange={(e) => setNewRuleName(e.target.value)}
                  placeholder="e.g. SQL Injection Query Sanitizer"
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] text-text-muted uppercase">Category</label>
                  <select
                    value={newRuleCategory}
                    onChange={(e) => setNewRuleCategory(e.target.value as PolicyRule["category"])}
                    className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs"
                  >
                    <option value="scope">Tool Scope</option>
                    <option value="injection">Prompt Injection</option>
                    <option value="pii">PII / Redaction</option>
                    <option value="cost">Cost Ceiling</option>
                    <option value="sandbox">Sandbox Isolation</option>
                    <option value="a2a">A2A Escrow</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-text-muted uppercase">Severity</label>
                  <select
                    value={newRuleSeverity}
                    onChange={(e) => setNewRuleSeverity(e.target.value as PolicyRule["severity"])}
                    className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs"
                  >
                    <option value="Critical">Critical</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Description</label>
                <textarea
                  value={newRuleDescription}
                  onChange={(e) => setNewRuleDescription(e.target.value)}
                  placeholder="Explain what this rule prevents in runtime..."
                  rows={3}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg p-2.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddingRule(false)}
                  className="px-3 py-1.5 rounded-lg border border-surface-border text-text-muted hover:text-text-primary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold"
                >
                  Create Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
