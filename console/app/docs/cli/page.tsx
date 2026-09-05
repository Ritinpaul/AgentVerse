"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Terminal } from "lucide-react";

const CLI_COMMANDS = [
  { cmd: "nuuvixx login",              desc: "Authenticate with your AgentVerse account" },
  { cmd: "nuuvixx logout",             desc: "Clear stored credentials" },
  { cmd: "nuuvixx whoami",             desc: "Show current authenticated user" },
  { cmd: "nuuvixx init [name]",        desc: "Scaffold a new agent project" },
  { cmd: "nuuvixx validate [file]",    desc: "Validate agent.yaml against JSON Schema" },
  { cmd: "nuuvixx publish",            desc: "Publish current agent to AgentStore" },
  { cmd: "nuuvixx publish --dry-run",  desc: "Validate publish payload without submitting" },
  { cmd: "nuuvixx list",               desc: "List your published agents" },
  { cmd: "nuuvixx get [slug]",         desc: "Get agent detail by slug" },
  { cmd: "nuuvixx retract [slug] [v]", desc: "Retract a published version" },
  { cmd: "nuuvixx run [slug]",         desc: "Run an agent interactively in the terminal" },
  { cmd: "nuuvixx logs [slug]",        desc: "Stream agent execution logs" },
  { cmd: "nuuvixx status",             desc: "Show status of all local AgentVerse services" },
];

export default function CliPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Terminal className="w-3.5 h-3.5" />
          Agent Development
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">CLI Reference</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          The AgentVerse CLI (<InlineCode>nuuvixx</InlineCode>) is your command-line interface for building,
          validating, publishing, and managing autonomous agents from the terminal.
        </p>
      </div>

      <DocH2>Installation</DocH2>
      <CodeBlock language="bash" code={`# Global install (recommended)
npm install -g @nuuvixx/cli

# Verify installation
nuuvixx --version
# Output: nuuvixx/1.0.0 linux-x64 node-v20.0.0`} />

      <DocH2>Authentication</DocH2>
      <CodeBlock language="bash" code={`# Login — opens browser for OAuth
nuuvixx login

# Or use an API key directly:
export NUUVIXX_API_KEY=your-api-key
nuuvixx login --api-key $NUUVIXX_API_KEY

# Verify authentication
nuuvixx whoami
# Output: Logged in as: ritindeep@nuuvixx.com (org: nuuvixx)`} />

      <DocH2>Project Initialization</DocH2>
      <CodeBlock language="bash" code={`# Create a new agent project
nuuvixx init my-support-agent

# Choose a template interactively:
# ❯ blank           — minimal agent.yaml
#   support-agent   — Zendesk + Slack integration
#   research-agent  — web search + summarization
#   devops-agent    — GitHub + CI/CD tools

cd my-support-agent
ls
# agent.yaml    README.md    .nuuvixx/`} />

      <DocH2>Validation</DocH2>
      <CodeBlock language="bash" code={`# Validate agent.yaml
nuuvixx validate
# Using: agent.yaml

# ✓ Schema validation passed
# ✓ Tool scopes within governance bounds
# ✓ Budget ceiling: $0.50 USD
# ✓ PII scan: ENABLED
# Ready to publish.

# Validate a specific file
nuuvixx validate path/to/other-agent.yaml`} />

      <Callout type="tip">
        Run <InlineCode>nuuvixx validate</InlineCode> in CI/CD pipelines before every push to catch
        manifest errors before they reach production.
      </Callout>

      <DocH2>Publishing</DocH2>
      <CodeBlock language="bash" code={`# Dry run (validate without publishing)
nuuvixx publish --dry-run

# Publish current directory's agent.yaml
nuuvixx publish

# Publishing as a different organization
nuuvixx publish --builder my-org

# Publish a specific category
nuuvixx publish --category finance

# Output:
# ✓ Validated agent.yaml
# ✓ Uploading to AgentStore...
# ✓ Published: my-org/my-support-agent@1.0.0
# 🌐 View: http://localhost:8050/agents/my-org/my-support-agent`} />

      <DocH2>Managing Agents</DocH2>
      <CodeBlock language="bash" code={`# List all your agents
nuuvixx list
# my-org/support-agent    v1.2.0    active    ⭐ 98.5
# my-org/research-agent   v0.9.0    active    ⭐ 87.2

# Get agent details
nuuvixx get my-org/support-agent

# Retract a version
nuuvixx retract my-org/support-agent 1.0.0
# ✓ Version 1.0.0 of my-org/support-agent retracted.`} />

      <DocH2>Running Agents</DocH2>
      <CodeBlock language="bash" code={`# Interactive agent REPL
nuuvixx run my-org/support-agent
# Connected to my-org/support-agent v1.2.0
# GovernOS Sentinel: enterprise-strict
# > What are the top 3 open tickets?

# Non-interactive with a prompt
nuuvixx run my-org/support-agent --prompt "Summarize open tickets"

# Stream live logs from a running agent
nuuvixx logs my-org/support-agent --tail 50 --follow`} />

      <DocH2>Service Status</DocH2>
      <CodeBlock language="bash" code={`nuuvixx status
# AgentVerse Services:
# ✓ AgentStore API       http://localhost:8005   healthy
# ✓ AgentVerse Console   http://localhost:3051   healthy
# ✓ GovernOS API         http://localhost:8025   healthy
# ✓ AgentStore Frontend  http://localhost:8050   healthy
# ⚠ Control Plane       http://localhost:8010   starting`} />

      <DocH2>Full Command Reference</DocH2>
      <div className="rounded-xl border border-white/10 overflow-hidden">
        <div className="bg-white/5 px-4 py-2 text-[10px] text-white/30 font-bold uppercase tracking-wider border-b border-white/10">
          nuuvixx &lt;command&gt; [options]
        </div>
        {CLI_COMMANDS.map((cmd, i) => (
          <div key={cmd.cmd} className={`flex items-start gap-3 px-4 py-3 ${i < CLI_COMMANDS.length - 1 ? "border-b border-white/6" : ""} hover:bg-white/3 transition-colors`}>
            <code className="text-emerald-400 text-xs shrink-0 w-52">{cmd.cmd}</code>
            <span className="text-white/50 text-xs font-sans">{cmd.desc}</span>
          </div>
        ))}
      </div>
    </article>
  );
}
