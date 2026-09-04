"use client";

import React from "react";
import { GovernSubNav } from "@/components/govern/GovernSubNav";
import { Network, Server, Lock } from "lucide-react";
import { useGatewayTelemetry } from "@/hooks/useGovernance";
import { useAgents } from "@/hooks/useAgents";

export default function GatewaysPage() {
  const gatewayStatus = useGatewayTelemetry();
  const { agents } = useAgents();
  const activeMicroVMs = agents.filter((a) => a.status === "running" || a.status === "active").length;

  return (
    <div className="space-y-5 font-mono">
      <GovernSubNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-violet-400" />
            <h1 className="text-xl font-bold text-text-primary">
              GovernOS MicroVM Gateways & Proxy
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              ● Port {gatewayStatus.port} Online
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-sans">
            In-runtime interceptor proxy handling mTLS encryption, rate limiting, and zero-trust syscall verification between agents and host environments.
          </p>
        </div>
      </div>

      {/* Gateway Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Local Kernel Gateway */}
        <div className="glass-card rounded-xl p-5 border border-surface-border space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-primary-light" />
              <h3 className="font-bold text-sm text-text-primary">Local Kernel Interceptor</h3>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold">
              {gatewayStatus.status}
            </span>
          </div>

          <div className="space-y-2 text-xs divide-y divide-surface-border/60">
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Listen Address</span>
              <span className="text-text-primary font-bold">
                {gatewayStatus.host}:{gatewayStatus.port}
              </span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">mTLS Cryptographic Handshake</span>
              <span className="text-emerald-400 font-bold">
                {gatewayStatus.mtls_enabled ? "ENABLED (RSA-4096)" : "DISABLED"}
              </span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Enforcement Latency</span>
              <span className="text-emerald-400 font-bold">
                {gatewayStatus.enforcement_latency_ms}ms / request
              </span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">TLS Certificate Expiry</span>
              <span className="text-text-secondary">{gatewayStatus.cert_expiry}</span>
            </div>
          </div>
        </div>

        {/* Cloud VPC Gateway */}
        <div className="glass-card rounded-xl p-5 border border-surface-border space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-violet-400" />
              <h3 className="font-bold text-sm text-text-primary">Cloud Control Plane Gateway</h3>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 font-bold">
              STANDBY
            </span>
          </div>

          <div className="space-y-2 text-xs divide-y divide-surface-border/60">
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Gateway Endpoint</span>
              <span className="text-text-primary font-bold">https://govern.agentverse.io/v1</span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Isolated Firecracker Sandboxes</span>
              <span className="text-emerald-400 font-bold">{activeMicroVMs} Active MicroVMs</span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Syscall Whitelist Profile</span>
              <span className="text-text-secondary">seccomp_bpf_agentverse_v2</span>
            </div>
            <div className="flex justify-between pt-1">
              <span className="text-text-muted">Cross-Region Failover</span>
              <span className="text-text-secondary">us-east-1 · eu-west-1 · ap-south-1</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

