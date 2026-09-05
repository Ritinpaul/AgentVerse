"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, ApiPlayground, ApiEndpointCard } from "@/components/docs/DocComponents";
import { Server } from "lucide-react";

export default function GovernanceApiPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Server className="w-3.5 h-3.5" />
          API Reference
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">Governance API</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The GovernOS Governance API provides enterprise-grade agent identity management, trust scoring,
          policy enforcement, audit logging, GDPR compliance, and human-in-the-loop orchestration.
          Running on <code className="text-[#4EC9B0]">localhost:8025</code>.
        </p>
      </div>

      <div className="flex items-center gap-3 p-4 rounded-xl bg-white/4 border border-white/10 mb-8">
        <Server className="w-5 h-5 text-[#E5252A] shrink-0" />
        <div>
          <div className="text-sm font-semibold text-white">Swagger UI — GovernOS API</div>
          <div className="text-xs text-white/50 font-sans">Full interactive documentation with 20+ endpoint modules</div>
        </div>
        <a href="http://localhost:8025/docs" target="_blank" rel="noopener noreferrer"
          className="ml-auto px-4 py-2 rounded-lg bg-[#E5252A] text-white text-xs font-bold hover:bg-[#E5252A]/80 transition-colors shrink-0">
          Open Swagger →
        </a>
      </div>

      <DocH2>Authentication (JWT)</DocH2>
      <DocH3>Get a JWT Token</DocH3>
      <ApiPlayground
        method="POST"
        endpoint="/auth/token"
        baseUrl="http://localhost:8025"
        defaultBody={JSON.stringify({ api_key: "dev-nuuvixx-svc-key-2026" }, null, 2)}
      />
      <Callout type="note">
        Use the returned <code>access_token</code> as a Bearer token in subsequent requests:
        <code>Authorization: Bearer &lt;token&gt;</code>
      </Callout>

      <DocH2>API Modules</DocH2>

      <DocH3>GENESIS — Agent Identity Registry</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="POST" path="/api/v1/genesis/agents"             desc="Register a new agent identity with DNA manifest" />
        <ApiEndpointCard method="GET"  path="/api/v1/genesis/agents/{agent_id}"  desc="Get full agent identity and DNA profile" />
        <ApiEndpointCard method="PUT"  path="/api/v1/genesis/agents/{agent_id}"  desc="Update agent DNA (requires admin scope)" />
        <ApiEndpointCard method="GET"  path="/api/v1/genesis/agents"             desc="List all registered agent identities" />
      </div>

      <DocH3>PULSE — Dynamic Trust Scoring Engine</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="GET"  path="/api/v1/pulse/score/{agent_id}"     desc="Get current trust score for an agent" />
        <ApiEndpointCard method="POST" path="/api/v1/pulse/event"                desc="Submit a behavioral event (success/failure/anomaly)" />
        <ApiEndpointCard method="GET"  path="/api/v1/pulse/history/{agent_id}"   desc="Get trust score history over time" />
      </div>

      <DocH3>SENTINEL — Policy Enforcement</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="POST" path="/api/v1/sentinel/evaluate"          desc="Evaluate a tool call against active policies" />
        <ApiEndpointCard method="GET"  path="/governance/owasp-coverage"         desc="Get current OWASP ASI coverage report" />
      </div>

      <DocH3>ANCESTOR — Audit Ledger</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="GET"  path="/api/v1/audit/decisions"            desc="Query the SHA-256 immutable decision ledger" />
        <ApiEndpointCard method="GET"  path="/api/v1/audit/decisions/{id}"       desc="Get a single audit entry with Merkle proof" />
        <ApiEndpointCard method="GET"  path="/api/v1/audit/summary"              desc="Aggregate audit stats for dashboards" />
      </div>

      <DocH3>ECLIPSE — Human-in-the-Loop (HITL)</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="GET"   path="/api/v1/eclipse/approvals"          desc="List pending human approval requests" />
        <ApiEndpointCard method="POST"  path="/api/v1/eclipse/approvals/{id}/approve" desc="Approve a HITL escalation" />
        <ApiEndpointCard method="POST"  path="/api/v1/eclipse/approvals/{id}/reject"  desc="Reject a HITL escalation" />
      </div>

      <DocH3>GDPR — Data Export & Erasure</DocH3>
      <div className="space-y-1 mb-4 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="GET"    path="/gdpr/export/{subject_id}"        desc="Export all personal data for a data subject" />
        <ApiEndpointCard method="DELETE" path="/gdpr/forget/{subject_id}"        desc="Right-to-Erasure: delete all subject data" />
      </div>

      <DocH2>Live API — Try It</DocH2>
      <DocH3>Get Agent Trust Score</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/api/v1/pulse/score/nuuvixx%2Fsupport-agent"
        baseUrl="http://localhost:8025"
      />

      <DocH3>List Pending HITL Approvals</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/api/v1/eclipse/approvals"
        baseUrl="http://localhost:8025"
      />
    </article>
  );
}
