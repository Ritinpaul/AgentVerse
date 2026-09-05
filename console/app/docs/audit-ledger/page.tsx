"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock } from "@/components/docs/DocComponents";
import { Shield } from "lucide-react";

export default function AuditLedgerPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Shield className="w-3.5 h-3.5" />Security & Governance
        </div>
        <h1 className="text-4xl font-black text-white mb-4">SHA-256 Decision Ledger</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          ANCESTOR is AgentVerse's immutable audit ledger. Every agent decision, tool call, and model
          response is recorded as a SHA-256 hashed entry chained into a Merkle tree — tamper-evident
          by design.
        </p>
      </div>

      <DocH2>How It Works</DocH2>
      <div className="rounded-xl border border-white/10 bg-[#070910] p-5 font-mono text-xs mb-6 overflow-x-auto">
        <pre className="text-white/70 leading-relaxed">{`
  Agent Event (tool call, model response, policy check)
         ↓
  SHA-256(event_data + previous_hash + timestamp)
         ↓
  Merkle Tree Node
         ↓
  Chain: entry[n].prev_hash = SHA256(entry[n-1])
         ↓
  ANCESTOR Ledger (SQLite/PostgreSQL write-once table)
         ↓
  Queryable via GET /api/v1/audit/decisions
`}</pre>
      </div>

      <DocH2>Audit Entry Schema</DocH2>
      <CodeBlock language="json" code={`{
  "id": "entry_abc123",
  "timestamp": "2026-08-30T21:00:00.000Z",
  "agent_id": "nuuvixx/support-agent",
  "run_id": "run_xyz789",
  "event_type": "tool_call",
  "event_data": {
    "tool": "zendesk:get-ticket",
    "scope": "read",
    "args": { "ticket_id": "12345" },
    "result": "APPROVED"
  },
  "policy_checks": ["ASI-01", "ASI-02", "ASI-03"],
  "sha256_hash": "a8f2c1d9e4b5f6a7c8d9e0f1a2b3c4d5...",
  "prev_hash":   "7c3e9f1a2b4d5e6f7a8b9c0d1e2f3a4b...",
  "merkle_root": "1d4a8c2b7f9e0a1b2c3d4e5f6a7b8c9d..."
}`} />

      <DocH2>Querying the Ledger</DocH2>
      <CodeBlock language="bash" code={`# Get recent audit entries
curl http://localhost:8025/api/v1/audit/decisions?limit=20

# Filter by agent
curl "http://localhost:8025/api/v1/audit/decisions?agent_id=nuuvixx/support-agent"

# Filter by event type
curl "http://localhost:8025/api/v1/audit/decisions?event_type=policy_violation"

# Get a single entry with Merkle proof
curl http://localhost:8025/api/v1/audit/decisions/entry_abc123`} />

      <DocH2>GDPR — Right to Erasure</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Audit entries containing personal data can be pseudonymized for GDPR compliance.
        The underlying chain integrity is preserved via cryptographic nullification.
      </p>
      <CodeBlock language="bash" code={`# Export all data for a subject
curl http://localhost:8025/gdpr/export/user_123

# Right-to-Erasure — pseudonymize personal data
curl -X DELETE http://localhost:8025/gdpr/forget/user_123`} />

      <Callout type="warning">
        GDPR erasure is irreversible. Personal data fields are replaced with a SHA-256 placeholder.
        The audit chain structure is preserved, but the personal data cannot be recovered.
      </Callout>
    </article>
  );
}
