"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { BookOpen } from "lucide-react";

export default function ConceptsPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <BookOpen className="w-3.5 h-3.5" />Getting Started
        </div>
        <h1 className="text-4xl font-black text-white mb-4">Core Concepts</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Key concepts you need to understand to build, deploy, and govern autonomous AI agents on AgentVerse.
        </p>
      </div>

      <DocH2>What is an Agent?</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        An <strong className="text-white">agent</strong> in AgentVerse is an autonomous AI program that uses an LLM as its reasoning
        engine. It receives a goal, plans steps using available tools, executes those steps, and iterates
        until the goal is achieved — all without continuous human intervention.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
        {[
          { title: "Perception", desc: "Receives input from users, APIs, or event streams" },
          { title: "Reasoning", desc: "LLM generates a plan of action using available tools" },
          { title: "Action", desc: "Executes tool calls — read email, write to DB, call API" },
        ].map(c => (
          <div key={c.title} className="p-4 rounded-xl bg-white/4 border border-white/10">
            <div className="text-[#E5252A] font-bold text-sm mb-1">{c.title}</div>
            <div className="text-white/55 text-xs font-sans">{c.desc}</div>
          </div>
        ))}
      </div>

      <DocH2>The Agent Manifest (agent.yaml)</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Every agent is declared via an <InlineCode>agent.yaml</InlineCode> manifest — a portable, versionable,
        JSON-Schema-validated specification. Think of it like a <code>package.json</code> for AI agents.
        See the <a href="/docs/agent-yaml" className="text-[#4EC9B0] underline">agent.yaml Reference</a> for the full schema.
      </p>

      <DocH2>Tools & Model Context Protocol (MCP)</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Agents gain superpowers through <strong className="text-white">tools</strong>. AgentVerse uses the
        Model Context Protocol (MCP) as the standard interface between LLMs and tools.
        Each tool is scoped (<InlineCode>read</InlineCode> / <InlineCode>write</InlineCode> / <InlineCode>admin</InlineCode>)
        and validated by GovernOS Sentinel before execution.
      </p>

      <DocH2>Trust Score</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Every agent has a <strong className="text-white">Trust Score</strong> (0–100) calculated by the PULSE engine.
        It increases with successful executions, zero policy violations, and positive human feedback.
        It decreases with security violations, HITL rejections, and anomalous behavior.
      </p>

      <DocH2>Human-in-the-Loop (HITL)</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        Agents with <InlineCode>enterprise-strict</InlineCode> policy require human approval for
        <InlineCode>write</InlineCode> or <InlineCode>admin</InlineCode> scope actions. The ECLIPSE module
        surfaces these as a pending approval queue in the GovernOS dashboard.
      </p>

      <DocH2>Agent Lifecycle</DocH2>
      <div className="rounded-xl border border-white/10 bg-[#070910] p-5 font-mono text-xs mb-6 overflow-x-auto">
        <pre className="text-white/70 leading-relaxed">{`
  DRAFT → VALIDATE → PUBLISH → ACTIVE → RETRACTED
                                  ↓
                           Execution Request
                                  ↓
                         GovernOS Sentinel
                          ↙           ↘
                      APPROVED       REJECTED
                          ↓               ↓
                    MicroVM Run     Error + Audit Log
                          ↓
                    SHA-256 Audit Entry → ANCESTOR Ledger
`}</pre>
      </div>

      <DocH2>Multi-Tenancy</DocH2>
      <p className="text-white/60 text-sm leading-relaxed font-sans">
        AgentVerse supports full multi-tenancy. Each organization gets isolated namespaces, separate
        policy sets, independent trust scoring, and GDPR-compliant data boundaries. Agents from
        different orgs cannot access each other's data or tools.
      </p>
    </article>
  );
}
