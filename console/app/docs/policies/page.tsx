"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Settings } from "lucide-react";

export default function PoliciesPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Settings className="w-3.5 h-3.5" />Security & Governance
        </div>
        <h1 className="text-4xl font-black text-white mb-4">Policy Engine</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The GovernOS Policy Engine lets you define, version, and enforce fine-grained behavioral rules
          for every agent in your organization. Policies are evaluated in the Sentinel kernel hotpath.
        </p>
      </div>

      <DocH2>Policy Structure</DocH2>
      <CodeBlock language="yaml" code={`# policy.yaml
id: my-enterprise-policy
version: "2.0.0"
inherits: standard  # Extend a base policy set

rules:
  # Require human approval for admin-scope tool calls
  - id: require-admin-approval
    trigger: tool_call
    condition: scope == "admin"
    action: require_hitl
    priority: 1

  # Block PII in model outputs
  - id: no-pii-output
    trigger: model_response
    condition: contains_pii == true
    action: mask_and_log
    priority: 2

  # Cost budget alert
  - id: cost-alert
    trigger: token_count
    condition: cumulative_cost_usd > 0.40
    action: alert_and_continue
    priority: 3
    threshold: 0.40

  # Hard cost stop
  - id: cost-ceiling
    trigger: token_count
    condition: cumulative_cost_usd >= 0.50
    action: halt
    priority: 1`} filename="policy.yaml" />

      <DocH2>Policy Actions</DocH2>
      <div className="space-y-2 mb-6">
        {[
          { action: "allow",            desc: "Permit the action and continue execution" },
          { action: "deny",             desc: "Reject the action with a 403 error response" },
          { action: "require_hitl",     desc: "Pause execution and send to Eclipse HITL queue" },
          { action: "mask_and_log",     desc: "Sanitize sensitive data and log the event to ANCESTOR" },
          { action: "alert_and_continue", desc: "Trigger an alert notification but allow execution to proceed" },
          { action: "halt",             desc: "Immediately terminate the execution with a budget/policy error" },
        ].map(item => (
          <div key={item.action} className="flex items-start gap-3 p-3 rounded-lg bg-white/4 border border-white/8">
            <code className="text-[#E5252A] text-xs w-32 shrink-0 font-mono">{item.action}</code>
            <span className="text-white/55 text-xs font-sans">{item.desc}</span>
          </div>
        ))}
      </div>

      <DocH2>Versioning & Rollback</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Every policy change is versioned. You can roll back to any previous version without downtime.
        Policy changes take effect within 30 seconds for all running agents in the organization.
      </p>
      <CodeBlock language="bash" code={`# List policy versions
curl http://localhost:8025/api/v1/policies/my-enterprise-policy/revisions

# Rollback to a previous version
curl -X POST http://localhost:8025/api/v1/policies/my-enterprise-policy/rollback \\
  -H "Content-Type: application/json" \\
  -d '{"target_version": "1.0.0"}'`} />

      <Callout type="important">
        Policy changes are applied immediately. Test in a staging environment before rolling out
        policy updates to production agents.
      </Callout>
    </article>
  );
}
