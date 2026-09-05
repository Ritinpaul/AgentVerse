"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser, clearAuth } from "@/lib/auth";
import {
  Settings,
  Key,
  Server,
  Shield,
  Cpu,
  Save,
  CheckCircle2,
  Lock,
  Eye,
  EyeOff,
  Globe,
  Radio,
  LogOut,
  User,
} from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [orgName, setOrgName] = useState("Nuuvixx Core Org");
  const [clusterRegion, setClusterRegion] = useState("prod-ap-south");
  const [geminiKey, setGeminiKey] = useState("AIzaSyB9...84920a11");
  const [claudeKey, setClaudeKey] = useState("sk-ant-api03-918...4490");
  const [openAiKey, setOpenAiKey] = useState("sk-proj-49182...bb90");

  const [showSecrets, setShowSecrets] = useState(false);
  const [saved, setSaved] = useState(false);

  const [storePort, setStorePort] = useState("8005");
  const [osPort, setOsPort] = useState("8010");
  const [governPort, setGovernPort] = useState("8025");

  useEffect(() => {
    const u = getStoredUser();
    setUser(u);
    if (u?.org_name) setOrgName(u.org_name);
  }, []);

  const handleSignOut = () => {
    clearAuth();
    router.push("/login");
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4 text-emerald-400" />
            <h1 className="text-xl font-bold text-text-primary">
              Organization Settings & API Keys
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              Admin Access
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            Configure global ecosystem ports, manage foundation model provider keys, and tune MicroVM execution policies.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-sm transition-all"
        >
          {saved ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              Settings Saved!
            </>
          ) : (
            <>
              <Save className="w-3.5 h-3.5" />
              Save Configuration
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs">
        {/* Left Column: Organization & Ecosystem Ports & Session */}
        <div className="space-y-6">
          {/* Org Profile */}
          <div className="glass-card rounded-xl p-5 border border-surface-border space-y-3">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <Globe className="w-3.5 h-3.5 text-primary-light" />
              Organization & Cluster
            </h3>

            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Organization Name</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-text-muted uppercase">Deployment Cluster Region</label>
                <select
                  value={clusterRegion}
                  onChange={(e) => setClusterRegion(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
                >
                  <option value="prod-ap-south">prod-ap-south (Mumbai/AWS)</option>
                  <option value="prod-us-east">prod-us-east (N. Virginia/AWS)</option>
                  <option value="prod-eu-central">prod-eu-central (Frankfurt/AWS)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Account & Active Session */}
          <div className="glass-card rounded-xl p-5 border border-surface-border space-y-4">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <User className="w-3.5 h-3.5 text-red-400" />
              Active User Session
            </h3>
            <div className="p-3 rounded-lg bg-[#0B0D14] border border-surface-border space-y-2.5 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Account Email:</span>
                <span className="text-text-primary font-bold">{user?.email || "admin@nuuvixx.ai"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Organization:</span>
                <span className="text-text-secondary">{user?.org_name || "Nuuvixx AI Systems"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Role Permission:</span>
                <span className="text-emerald-400 uppercase font-bold">{user?.role || "owner"}</span>
              </div>
              <div className="pt-3 border-t border-surface-border">
                <button
                  onClick={handleSignOut}
                  className="w-full py-2 px-3 rounded-lg bg-red-950/50 hover:bg-red-900/60 border border-red-800/50 text-red-400 hover:text-red-200 text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-sm active:scale-[0.99]"
                >
                  <LogOut className="w-4 h-4 text-red-500" />
                  <span>Sign Out of AgentVerse</span>
                </button>
              </div>
            </div>
          </div>

          {/* Ecosystem Backend Ports */}
          <div className="glass-card rounded-xl p-5 border border-surface-border space-y-3">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              Backend Ecosystem Ports
            </h3>

            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-lg bg-surface-50 border border-surface-border space-y-1">
                <div className="text-[10px] text-text-muted">AgentStore</div>
                <input
                  type="text"
                  value={storePort}
                  onChange={(e) => setStorePort(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded px-2 py-1 text-emerald-300 font-bold"
                />
              </div>

              <div className="p-3 rounded-lg bg-surface-50 border border-surface-border space-y-1">
                <div className="text-[10px] text-text-muted">AgentOS</div>
                <input
                  type="text"
                  value={osPort}
                  onChange={(e) => setOsPort(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded px-2 py-1 text-emerald-300 font-bold"
                />
              </div>

              <div className="p-3 rounded-lg bg-surface-50 border border-surface-border space-y-1">
                <div className="text-[10px] text-text-muted">GovernOS</div>
                <input
                  type="text"
                  value={governPort}
                  onChange={(e) => setGovernPort(e.target.value)}
                  className="w-full bg-surface-100 border border-surface-border rounded px-2 py-1 text-emerald-300 font-bold"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: LLM Provider API Keys */}
        <div className="glass-card rounded-xl p-5 border border-surface-border space-y-4">
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <Key className="w-3.5 h-3.5 text-violet-400" />
              Foundation Model Provider Keys
            </h3>

            <button
              onClick={() => setShowSecrets(!showSecrets)}
              className="text-[10px] text-text-muted hover:text-text-primary flex items-center gap-1"
            >
              {showSecrets ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              {showSecrets ? "Hide" : "Show"}
            </button>
          </div>

          <div className="space-y-3">
            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-text-muted">
                <span>Google Gemini (gemini-2.5-pro, flash)</span>
                <span className="text-emerald-400 font-bold">Active</span>
              </div>
              <input
                type={showSecrets ? "text" : "password"}
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-text-muted">
                <span>Anthropic Claude (claude-3-5-sonnet)</span>
                <span className="text-emerald-400 font-bold">Active</span>
              </div>
              <input
                type={showSecrets ? "text" : "password"}
                value={claudeKey}
                onChange={(e) => setClaudeKey(e.target.value)}
                className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-text-muted">
                <span>OpenAI (gpt-4o, gpt-4o-mini)</span>
                <span className="text-emerald-400 font-bold">Active</span>
              </div>
              <input
                type={showSecrets ? "text" : "password"}
                value={openAiKey}
                onChange={(e) => setOpenAiKey(e.target.value)}
                className="w-full bg-surface-100 border border-surface-border rounded-lg px-3 py-1.5 text-text-primary font-mono text-xs"
              />
            </div>
          </div>

          {/* MicroVM Sandbox settings */}
          <div className="pt-2 border-t border-surface-border space-y-2">
            <div className="text-[10px] text-text-muted uppercase font-bold flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              MicroVM Isolation Engine
            </div>
            <div className="p-3 rounded-lg bg-[#0B0D14] border border-surface-border text-[11px] text-text-secondary space-y-1 font-mono">
              <div className="flex justify-between">
                <span>Isolation Mode:</span>
                <strong className="text-emerald-400">Firecracker MicroVM (KVM)</strong>
              </div>
              <div className="flex justify-between">
                <span>Coldstart Overhead:</span>
                <strong className="text-emerald-400">38ms</strong>
              </div>
              <div className="flex justify-between">
                <span>Default Memory Limit:</span>
                <strong className="text-text-primary">512 MB</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
