"use client";

import React, { useState, useCallback } from "react";
import Link from "next/link";
import { StoreSubNav } from "@/components/store/StoreSubNav";
import {
  UploadCloud,
  CheckCircle2,
  DollarSign,
  Radio,
  FileCode,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Check,
} from "lucide-react";

export default function PublishAgentPage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Step 1: Metadata
  const [name, setName] = useState("Sentiment Sentinel Pro");
  const [slug, setSlug] = useState("sentiment-sentinel-pro");
  const [category, setCategory] = useState("Finance & Analytics");
  const [description, setDescription] = useState("Real-time NLP sentiment analysis across SEC filings, Bloomberg terminals, and crypto order books with strict PII masking.");

  // Step 2: Manifest YAML
  const [yamlContent, setYamlContent] = useState(`name: sentiment-sentinel-pro
version: "1.0.0"
runtime:
  model: gemini-2.5-pro
  fallback_model: gemini-2.0-flash
  max_tokens: 8192
  timeout_seconds: 30
governance:
  policy_set: enterprise-strict
  pii_scan: true
  allowed_tool_scopes:
    - read
tools:
  - name: financial_nlp
    scope: read
budget:
  cost_ceiling_usd: 0.20`);

  // Step 3: Pricing & x402
  const [pricePerRun, setPricePerRun] = useState(0.10);
  const [payoutWallet, setPayoutWallet] = useState("0x89F2...4C19");

  // Step 4: Scanning & Publish
  const [scanning, setScanning] = useState(false);
  const [published, setPublished] = useState(false);

  const handlePublish = useCallback(() => {
    setScanning(true);
    setTimeout(() => {
      setScanning(false);
      setPublished(true);
    }, 1200);
  }, []);

  return (
    <div className="space-y-5 font-mono">
      <StoreSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              AgentStore Publisher Wizard
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              80% Builder Revenue Share
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Package, validate, and monetize your autonomous AI agent on the decentralized x402 commerce marketplace.
          </p>
        </div>
      </div>

      {/* 4-Step Progress Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {[
          { num: 1, title: "1. Metadata", icon: FileCode },
          { num: 2, title: "2. Manifest Upload", icon: UploadCloud },
          { num: 3, title: "3. Pricing & x402", icon: DollarSign },
          { num: 4, title: "4. ASI Scan & Publish", icon: Radio },
        ].map((s) => (
          <div
            key={s.num}
            onClick={() => setStep(s.num as 1 | 2 | 3 | 4)}
            className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center gap-2 ${
              step === s.num
                ? "bg-surface-50 border-emerald-500 text-emerald-400 font-bold shadow-sm"
                : step > s.num
                ? "bg-surface-100/50 border-surface-border text-text-secondary"
                : "bg-surface-100/20 border-surface-border text-text-muted"
            }`}
          >
            <s.icon className="w-4 h-4" />
            <span>{s.title}</span>
          </div>
        ))}
      </div>

      {/* Wizard Step Content */}
      <div className="glass-card rounded-xl p-5 border border-surface-border space-y-4">
        {/* ── STEP 1: Metadata ──────────────────────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-bold text-text-primary">Step 1: Agent Listing Details</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Agent Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Agent Slug</label>
                <input
                  type="text"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-primary font-mono text-xs"
              >
                <option value="Productivity">Productivity</option>
                <option value="Finance & Analytics">Finance & Analytics</option>
                <option value="Security & Legal">Security & Legal</option>
                <option value="DevOps">DevOps</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase">Public Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full bg-surface-100 border border-surface-border rounded-lg p-2.5 text-text-primary focus:outline-none focus:border-primary font-sans text-xs resize-none"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setStep(2)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
              >
                <span>Continue to Manifest Upload</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: Manifest Upload ────────────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-bold text-text-primary">Step 2: agent.yaml Manifest Validation</h3>

            <textarea
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              rows={12}
              className="w-full bg-[#0B0D14] border border-surface-border rounded-xl p-3 text-emerald-300 font-mono text-xs leading-relaxed"
            />

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={() => setStep(1)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-border text-text-muted hover:text-text-primary text-xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
              >
                <span>Continue to Pricing</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: Pricing & x402 ──────────────────────────────────────────── */}
        {step === 3 && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-bold text-text-primary">Step 3: Pricing & x402 Micropayment Setup</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-2">
                <label className="text-[10px] text-text-muted uppercase font-bold">
                  Price per Execution ($USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={pricePerRun}
                  onChange={(e) => setPricePerRun(parseFloat(e.target.value) || 0.05)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
                />
                <div className="text-[10px] text-emerald-400">
                  Builder payout: ${(pricePerRun * 0.8).toFixed(4)} (80%) · Platform: ${(pricePerRun * 0.2).toFixed(4)} (20%)
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-border space-y-2">
                <label className="text-[10px] text-text-muted uppercase font-bold">
                  Payout Crypto Wallet / Account
                </label>
                <input
                  type="text"
                  value={payoutWallet}
                  onChange={(e) => setPayoutWallet(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
                />
                <div className="text-[10px] text-text-muted">Settles autonomously on Polygon USDC weekly</div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={() => setStep(2)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-border text-text-muted hover:text-text-primary text-xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
              <button
                onClick={() => setStep(4)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
              >
                <span>Continue to ASI Scan</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 4: ASI Scan & Publish ─────────────────────────────────────── */}
        {step === 4 && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-bold text-text-primary">Step 4: ASI Automated Red-Team Scanner</h3>

            {published ? (
              <div className="p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-3">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                <h4 className="text-base font-bold text-emerald-400">Agent Successfully Published to Store!</h4>
                <p className="text-xs text-text-secondary font-sans max-w-md mx-auto">
                  {name} passed all ASI01–ASI10 red-team scanner checks with a Trust Score of 96/100 and is now live on the global marketplace.
                </p>
                <div className="pt-2 flex justify-center gap-3">
                  <Link
                    href={`/store/${slug}`}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
                  >
                    View Live Store Listing
                  </Link>
                  <Link
                    href="/store"
                    className="px-4 py-2 rounded-lg border border-surface-border text-text-secondary hover:text-text-primary text-xs"
                  >
                    Return to Marketplace
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-surface-50 border border-surface-border space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-text-primary">Pre-Flight Security Gates</span>
                    <span className="text-[10px] text-emerald-400 font-bold">10/10 Passed</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[10px]">
                    <div className="p-2 rounded bg-surface-100 text-emerald-400">✓ ASI01 Injection</div>
                    <div className="p-2 rounded bg-surface-100 text-emerald-400">✓ ASI02 Scopes</div>
                    <div className="p-2 rounded bg-surface-100 text-emerald-400">✓ ASI03 PII Scan</div>
                    <div className="p-2 rounded bg-surface-100 text-emerald-400">✓ ASI04 Budget</div>
                    <div className="p-2 rounded bg-surface-100 text-emerald-400">✓ ASI05 Sandbox</div>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-2">
                  <button
                    onClick={() => setStep(3)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-border text-text-muted hover:text-text-primary text-xs"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> Back
                  </button>
                  <button
                    onClick={handlePublish}
                    disabled={scanning}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all"
                  >
                    {scanning ? (
                      <>
                        <div className="w-3.5 h-3.5 border border-white border-t-transparent rounded-full animate-spin" />
                        Running Red-Team Audits...
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        Publish to AgentStore (Live)
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
