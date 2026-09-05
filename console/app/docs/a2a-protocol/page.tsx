"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, ApiEndpointCard, ApiPlayground } from "@/components/docs/DocComponents";
import { GitBranch } from "lucide-react";

export default function A2AProtocolPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <GitBranch className="w-3.5 h-3.5" />Integrations
        </div>
        <h1 className="text-4xl font-black text-white mb-4">A2A Protocol</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The <strong className="text-white">Agent-to-Agent (A2A) Protocol</strong> enables autonomous
          agents to discover, communicate with, and delegate tasks to other agents — with cryptographic
          identity verification and zero-trust trust scoring.
        </p>
      </div>

      <DocH2>How A2A Works</DocH2>
      <div className="rounded-xl border border-white/10 bg-[#070910] p-5 font-mono text-xs mb-6 overflow-x-auto">
        <pre className="text-white/70 leading-relaxed">{`
  Agent A (Orchestrator)
       ↓  discovers Agent B via AgentStore registry
  Agent B's DID + Public Key retrieved from GENESIS
       ↓  signs request with Agent A's private key
  GovernOS validates signatures + trust scores
       ↓  if APPROVED
  Agent B receives task delegation
       ↓  executes + returns result
  A2A Response logged to ANCESTOR ledger
`}</pre>
      </div>

      <DocH2>Declaring A2A Dependencies</DocH2>
      <CodeBlock language="yaml" code={`# In agent.yaml — declare which agents this agent can delegate to:
a2a:
  can_delegate_to:
    - slug: nuuvixx/research-agent
      trust_threshold: 85.0   # Min trust score required
      max_delegations: 5
      scope: read
    - slug: nuuvixx/data-analyst
      trust_threshold: 90.0
      scope: read`} />

      <DocH2>A2A API Endpoints</DocH2>
      <div className="space-y-1 mb-6 rounded-xl border border-white/10 overflow-hidden">
        <ApiEndpointCard method="POST" path="/api/v1/a2a/delegate"          desc="Delegate a task from one agent to another" />
        <ApiEndpointCard method="GET"  path="/api/v1/a2a/tasks/{task_id}"   desc="Check delegation task status" />
        <ApiEndpointCard method="GET"  path="/api/v1/a2a/discovery/{slug}"  desc="Discover an agent's A2A capabilities" />
        <ApiEndpointCard method="GET"  path="/api/v1/a2a/inbox"             desc="Get pending delegations for this agent" />
      </div>

      <DocH3>Try It — Agent Discovery</DocH3>
      <ApiPlayground
        method="GET"
        endpoint="/api/v1/a2a/discovery/nuuvixx%2Fsupport-agent"
        baseUrl="http://localhost:8025"
      />

      <Callout type="note">
        A2A delegation requires both agents to have Trust Scores above the declared
        <code>trust_threshold</code>. Agents with Trust Score below 60 cannot participate
        in A2A delegation as either orchestrator or worker.
      </Callout>
    </article>
  );
}
