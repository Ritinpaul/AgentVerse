"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Code2 } from "lucide-react";

export default function VsCodeExtensionPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Code2 className="w-3.5 h-3.5" />Integrations
        </div>
        <h1 className="text-4xl font-black text-white mb-4">VS Code Extension</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The AgentVerse VS Code Extension gives you inline <InlineCode>agent.yaml</InlineCode> linting,
          one-click publish, live agent execution telemetry, and GovernOS Sentinel diagnostics —
          all directly inside your editor.
        </p>
      </div>

      <DocH2>Installation</DocH2>
      <CodeBlock language="bash" code={`# Install from VS Code marketplace:
code --install-extension nuuvixx.agentverse-studio

# Or open VS Code, press Cmd+P and run:
# ext install nuuvixx.agentverse-studio`} />

      <DocH2>Features</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
        {[
          { title: "agent.yaml IntelliSense",     desc: "Full autocompletion, hover documentation, and validation for agent.yaml" },
          { title: "Inline Sentinel Diagnostics", desc: "See OWASP ASI policy violations highlighted inline as you type" },
          { title: "One-Click Publish",           desc: "Publish to AgentStore directly from the VS Code command palette" },
          { title: "Agent Explorer",              desc: "Browse all your published agents in the VS Code sidebar" },
          { title: "Live Telemetry Stream",       desc: "Watch agent execution logs in the VS Code terminal panel" },
          { title: "YAML Schema Validation",      desc: "JSON Schema validation with immediate error highlighting" },
        ].map(f => (
          <div key={f.title} className="p-4 rounded-xl bg-white/4 border border-white/10">
            <div className="text-white font-semibold text-sm mb-1">{f.title}</div>
            <div className="text-white/50 text-xs font-sans">{f.desc}</div>
          </div>
        ))}
      </div>

      <DocH2>Configuration</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Open VS Code settings (<InlineCode>Cmd+,</InlineCode>) and search for <InlineCode>agentverse</InlineCode>:
      </p>
      <CodeBlock language="json" code={`{
  "agentverse.apiKey": "your-api-key",
  "agentverse.agentStoreUrl": "http://localhost:8005",
  "agentverse.governOsUrl": "http://localhost:8025",
  "agentverse.sentinelLinting": true,
  "agentverse.autoValidateOnSave": true,
  "agentverse.telemetryStream": true
}`} filename=".vscode/settings.json" />

      <DocH2>Commands</DocH2>
      <div className="space-y-2">
        {[
          { cmd: "AgentVerse: Publish Agent",      key: "Cmd+Shift+P",  desc: "Publish current agent.yaml to AgentStore" },
          { cmd: "AgentVerse: Validate Manifest",  key: "Cmd+Shift+V",  desc: "Run JSON Schema validation" },
          { cmd: "AgentVerse: Run Agent",          key: "Cmd+Shift+R",  desc: "Execute agent interactively in terminal" },
          { cmd: "AgentVerse: Open Dashboard",     key: "–",            desc: "Open AgentVerse Console in browser" },
          { cmd: "AgentVerse: View Audit Logs",    key: "–",            desc: "Open ANCESTOR ledger viewer" },
        ].map(c => (
          <div key={c.cmd} className="flex items-start gap-3 p-3 rounded-lg bg-white/4 border border-white/8">
            <code className="text-[#4EC9B0] text-xs w-52 shrink-0">{c.cmd}</code>
            <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/50 shrink-0">{c.key}</kbd>
            <span className="text-white/50 text-xs font-sans">{c.desc}</span>
          </div>
        ))}
      </div>

      <Callout type="note">
        The extension connects directly to your locally running services. Make sure
        <InlineCode>docker compose up</InlineCode> is running before using the extension features.
      </Callout>
    </article>
  );
}
