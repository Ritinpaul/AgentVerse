"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient, SystemHealth } from "@/lib/api";

export interface PolicyRule {
  id: string;
  code: string;
  name: string;
  category: "injection" | "scope" | "pii" | "cost" | "sandbox" | "compliance" | "a2a";
  mode: "ENFORCE" | "AUDIT" | "DISABLED";
  severity: "Critical" | "High" | "Medium" | "Low";
  description: string;
  enabled: boolean;
  enforcements_today: number;
  blocked_count: number;
  config: Record<string, string | number | boolean | string[]>;
}

export interface AuditRecord {
  id: string;
  hash: string;
  previous_hash: string;
  timestamp: string;
  timestamp_iso: string;
  agent: string;
  agent_slug: string;
  session_id: string;
  action: string;
  tool_scope: string;
  outcome: "ALLOW" | "BLOCKED" | "REDACTED" | "FLAGGED";
  policy_rule: string;
  latency_ms: number;
  reason?: string;
  signer: string;
}

export interface ApprovalRequest {
  id: string;
  agent_slug: string;
  agent_name: string;
  session_id: string;
  tool_name: string;
  requested_scope: "write" | "admin";
  target_resource: string;
  risk_score: number;
  risk_level: "Critical" | "High" | "Medium";
  timestamp: string;
  timeout_seconds: number;
  status: "pending" | "approved" | "rejected";
  payload: Record<string, unknown>;
}

export interface CacheAnalytics {
  total_queries: number;
  cache_hits: number;
  cache_misses: number;
  hit_rate_pct: number;
  cost_saved_usd: number;
  tokens_saved: number;
  avg_cache_latency_ms: number;
  avg_llm_latency_ms: number;
}

export interface ASIScanResult {
  agent_id: string;
  agent_name: string;
  agent_slug: string;
  scan_timestamp: string;
  score: number;
  status: "passed" | "warning" | "failed";
  findings: Array<{
    rule_id: string;
    rule_name: string;
    severity: "Critical" | "High" | "Medium" | "Low";
    status: "pass" | "warn" | "fail";
    description: string;
    remediation: string;
  }>;
}

export interface ComplianceFramework {
  id: string;
  name: string;
  version: string;
  status: "Certified" | "Compliant" | "Review Required";
  score: number;
  controls_total: number;
  controls_passed: number;
  last_audit_date: string;
  description: string;
}

const INITIAL_POLICIES: PolicyRule[] = [];
const INITIAL_AUDITS: AuditRecord[] = [];
const INITIAL_APPROVALS: ApprovalRequest[] = [];

const INITIAL_CACHE_METRICS: CacheAnalytics = {
  total_queries: 0,
  cache_hits: 0,
  cache_misses: 0,
  hit_rate_pct: 0.0,
  cost_saved_usd: 0.0,
  tokens_saved: 0,
  avg_cache_latency_ms: 0,
  avg_llm_latency_ms: 0,
};

const INITIAL_COMPLIANCE: ComplianceFramework[] = [
  {
    id: "soc2",
    name: "SOC2 Type II",
    version: "2026",
    status: "Review Required",
    score: 0.0,
    controls_total: 48,
    controls_passed: 0,
    last_audit_date: "Pending Runtime Sentinel Audit",
    description: "Security, Availability, and Confidentiality trust service criteria monitored in real time.",
  },
  {
    id: "hipaa",
    name: "HIPAA Security Rule",
    version: "HITECH",
    status: "Review Required",
    score: 0.0,
    controls_total: 32,
    controls_passed: 0,
    last_audit_date: "Pending Runtime Sentinel Audit",
    description: "ePHI protection and automated PII sanitization via GovernOS zero-trust inspection.",
  },
  {
    id: "gdpr",
    name: "GDPR & EU Data Protection",
    version: "2018/679",
    status: "Review Required",
    score: 0.0,
    controls_total: 24,
    controls_passed: 0,
    last_audit_date: "Pending Runtime Sentinel Audit",
    description: "Data minimization and runtime isolation enforced inside MicroVM sandboxes.",
  },
  {
    id: "eu_ai_act",
    name: "EU AI Act — High Risk AI",
    version: "2024/1689",
    status: "Review Required",
    score: 0.0,
    controls_total: 30,
    controls_passed: 0,
    last_audit_date: "Pending Runtime Sentinel Audit",
    description: "Human-in-the-loop (HITL) approval gates and immutable audit ledger.",
  },
];


function normalizePolicy(p: any): PolicyRule {
  return {
    id: p.id ? String(p.code || p.id) : "POL-00",
    code: p.code || "ASI",
    name: p.name || "Governance Policy",
    category: p.category || "compliance",
    mode: p.mode || (p.enabled ? "ENFORCE" : "DISABLED"),
    severity: p.severity || "High",
    description: p.description || "",
    enabled: p.enabled ?? true,
    enforcements_today: p.enforcements_today ?? 0,
    blocked_count: p.blocked_count ?? 0,
    config: p.config_json || p.config || {},
  };
}

function normalizeAudit(d: any): AuditRecord {
  return {
    id: d.id || `dec-${Math.random()}`,
    hash: d.hash || "sha256:000000",
    previous_hash: d.previous_hash || "sha256:000000",
    timestamp: d.created_at ? new Date(d.created_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
    timestamp_iso: d.created_at || new Date().toISOString(),
    agent: d.agent_name || d.agent_id || "Finance Auditor",
    agent_slug: d.agent_slug || "finance-auditor",
    session_id: d.session_id || "sess_000",
    action: d.action || "tool_execution",
    tool_scope: d.tool_scope || "execute",
    outcome: (d.verdict as any) || (d.outcome as any) || "ALLOW",
    policy_rule: d.rule_triggered || "POL-01",
    latency_ms: d.execution_ms ?? 12,
    reason: d.reason || undefined,
    signer: d.signer_identity || "ANCESTOR-KMS-01",
  };
}

function normalizeEscalation(e: any): ApprovalRequest {
  return {
    id: e.id,
    agent_slug: e.agent_slug || "finance-auditor",
    agent_name: e.agent_name || e.agent_id || "Finance Auditor",
    session_id: e.session_id || "sess_000",
    tool_name: e.action_requested || "wire_transfer",
    requested_scope: e.requested_scope || "write",
    target_resource: e.target_resource || "stripe_billing",
    risk_score: e.risk_score || 85,
    risk_level: e.risk_level || "High",
    timestamp: e.created_at ? new Date(e.created_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
    timeout_seconds: e.timeout_seconds || 300,
    status: e.status ? (e.status.toLowerCase() as any) : "pending",
    payload: e.payload || {},
  };
}

export function useGovernance() {
  const [policies, setPolicies] = useState<PolicyRule[]>(INITIAL_POLICIES);
  const [audits, setAudits] = useState<AuditRecord[]>(INITIAL_AUDITS);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>(INITIAL_APPROVALS);
  const [cacheMetrics] = useState<CacheAnalytics>(INITIAL_CACHE_METRICS);
  const [complianceFrameworks] = useState<ComplianceFramework[]>(INITIAL_COMPLIANCE);

  useEffect(() => {
    let isMounted = true;
    let ws: WebSocket | null = null;

    async function loadLiveGovernance() {
      try {
        const [livePolicies, liveAudits, liveApprovals] = await Promise.allSettled([
          apiClient.getGovernancePolicies(),
          apiClient.getAuditLedger(),
          apiClient.getPendingApprovals(),
        ]);

        if (isMounted) {
          if (livePolicies.status === "fulfilled" && Array.isArray(livePolicies.value) && livePolicies.value.length > 0) {
            setPolicies(livePolicies.value.map(normalizePolicy));
          }
          if (liveAudits.status === "fulfilled" && Array.isArray(liveAudits.value) && liveAudits.value.length > 0) {
            setAudits(liveAudits.value.map(normalizeAudit));
          }
          if (liveApprovals.status === "fulfilled" && Array.isArray(liveApprovals.value) && liveApprovals.value.length > 0) {
            setApprovals(liveApprovals.value.map(normalizeEscalation));
          }
        }
      } catch {
        // Fallback to initial state
      }
    }

    loadLiveGovernance();
    const interval = setInterval(loadLiveGovernance, 10000);

    // Establish Real-Time WebSocket Connection to AgentGovernOS
    try {
      ws = new WebSocket("ws://localhost:8025/ws/live");
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "telemetry_event" && isMounted) {
            const newAudit: AuditRecord = {
              id: `aud-${Date.now()}`,
              hash: `0x${Math.random().toString(16).substring(2, 10)}`,
              previous_hash: "0x8fa92b...4c19",
              timestamp: "Just now",
              timestamp_iso: new Date().toISOString(),
              agent: data.agent_id || "Live Agent",
              agent_slug: data.agent_id || "live-agent",
              session_id: "sess_live_ws",
              action: data.action_name || "mcp_proxy_call",
              tool_scope: "execute",
              outcome: data.verdict === "ALLOW" ? "ALLOW" : "BLOCKED",
              policy_rule: "SENTINEL-WS",
              latency_ms: 8,
              signer: "govern_os_ws_kernel"
            };
            setAudits((prev) => [newAudit, ...prev.slice(0, 49)]);
          }
        } catch {}
      };
    } catch {}

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, []);

  const togglePolicy = useCallback((id: string) => {
    setPolicies((prev) => {
      const updated = prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p));
      const target = updated.find(p => p.id === id);
      if (target && apiClient.updatePolicy) {
        apiClient.updatePolicy(id, { enabled: target.enabled });
      }
      return updated;
    });
  }, []);

  const updatePolicyMode = useCallback((id: string, mode: PolicyRule["mode"]) => {
    setPolicies((prev) => {
      const updated = prev.map((p) => (p.id === id ? { ...p, mode } : p));
      const target = updated.find(p => p.id === id);
      if (target && apiClient.updatePolicy) {
        apiClient.updatePolicy(id, { mode: target.mode });
      }
      return updated;
    });
  }, []);

  const approveRequest = useCallback((id: string) => {
    apiClient.approveAction(id);
    setApprovals((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "approved" as const } : a))
    );
  }, []);

  const rejectRequest = useCallback((id: string) => {
    apiClient.rejectAction(id);
    setApprovals((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "rejected" as const } : a))
    );
  }, []);

  const addPolicy = useCallback((newPol: Omit<PolicyRule, "id" | "enforcements_today" | "blocked_count">) => {
    const id = `POL-${(policies.length + 1).toString().padStart(2, "0")}`;
    setPolicies((prev) => [
      ...prev,
      { ...newPol, id, enforcements_today: 0, blocked_count: 0 },
    ]);
  }, [policies.length]);

  const computedFrameworks = complianceFrameworks.map((fw) => {
    if (audits.length === 0) {
      return {
        ...fw,
        controls_passed: 0,
        score: 0,
        status: "Review Required" as const,
        last_audit_date: "Pending Runtime Sentinel Audit",
      };
    }
    const allowedRatio = audits.filter((a) => a.outcome === "ALLOW").length / audits.length;
    const passedControls = Math.round(fw.controls_total * allowedRatio);
    const scorePct = Math.round((passedControls / fw.controls_total) * 100);
    return {
      ...fw,
      controls_passed: passedControls,
      score: scorePct,
      status: (scorePct === 100 ? "Certified" : scorePct >= 80 ? "Compliant" : "Review Required") as any,
      last_audit_date: "Active Runtime Sentinel",
    };
  });

  return {
    policies,
    activePolicies: policies.filter((p) => p.enabled),
    recentAudits: audits,
    approvals,
    pendingApprovalsCount: approvals.filter((a) => a.status === "pending").length,
    cacheMetrics,
    complianceFrameworks: computedFrameworks,
    totalEnforced: policies.reduce((acc, p) => acc + p.enforcements_today, 0),
    blockedThreats: policies.reduce((acc, p) => acc + p.blocked_count, 0),
    complianceScore: audits.length > 0
      ? Math.round((audits.filter(a => a.outcome === "ALLOW").length / audits.length) * 1000) / 10
      : 0.0,
    togglePolicy,
    updatePolicyMode,
    approveRequest,
    rejectRequest,
    addPolicy,
  };
}

export function useSystemHealth() {
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    let mounted = true;
    apiClient.getSystemHealth().then((h) => {
      if (mounted) setHealth(h);
    });
    const interval = setInterval(() => {
      apiClient.getSystemHealth().then((h) => {
        if (mounted) setHealth(h);
      });
    }, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return health;
}

export function useGatewayTelemetry() {
  const [gatewayInfo, setGatewayInfo] = useState({
    port: 8025,
    host: "127.0.0.1",
    status: "STANDBY",
    mtls_enabled: false,
    enforcement_latency_ms: 0.0,
    cert_expiry: "2027-08-01 (Standby)",
  });

  useEffect(() => {
    let mounted = true;
    async function checkGateway() {
      const data = await apiClient.getGatewayStatus();
      if (mounted) {
        if (data) {
          setGatewayInfo((prev) => ({ ...prev, ...data }));
        } else {
          setGatewayInfo((prev) => ({
            ...prev,
            status: "STANDBY",
            mtls_enabled: false,
            enforcement_latency_ms: 0.0,
          }));
        }
      }
    }
    checkGateway();
    const interval = setInterval(checkGateway, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return gatewayInfo;
}


