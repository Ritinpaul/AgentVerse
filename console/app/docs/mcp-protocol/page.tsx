"use client";
import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Link2 } from "lucide-react";

export default function McpProtocolPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Link2 className="w-3.5 h-3.5" />Integrations
        </div>
        <h1 className="text-4xl font-black text-white mb-4">MCP Protocol</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          AgentVerse uses the <strong className="text-white">Model Context Protocol (MCP)</strong> as the
          standard interface between LLMs and external tools. MCP provides a secure, typed,
          schema-validated contract for every agent-to-tool interaction.
        </p>
      </div>

      <DocH2>What is MCP?</DocH2>
      <p className="text-white/60 text-sm leading-relaxed mb-4 font-sans">
        MCP is an open protocol for connecting AI models to external data sources and tools.
        It provides standardized request/response contracts, capability discovery, and
        bidirectional streaming — all JSON-RPC 2.0 over SSE or WebSocket.
      </p>

      <DocH2>Supported MCP Servers</DocH2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        {[
          "zendesk", "slack", "github", "jira", "notion",
          "salesforce", "hubspot", "brave-search", "filesystem",
          "postgresql", "redis", "stripe", "gmail", "calendar",
        ].map(s => (
          <div key={s} className="px-3 py-2 rounded-lg bg-white/4 border border-white/10 text-xs text-white/70 font-mono">
            mcp://{s}
          </div>
        ))}
      </div>

      <DocH2>Declaring MCP Tools in agent.yaml</DocH2>
      <CodeBlock language="yaml" code={`tools:
  - name: search_tickets
    type: mcp
    server: zendesk
    scope: read
    rate_limit: 30/minute
    
  - name: post_message
    type: mcp
    server: slack
    scope: write
    channels:
      - "#support-alerts"
      - "#on-call"`} />

      <DocH2>Creating a Custom MCP Server</DocH2>
      <CodeBlock language="bash" code={`# TypeScript MCP server skeleton:
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "my-service", version: "1.0.0" });

server.tool(
  "get_data",
  "Fetch data from my service",
  { id: z.string() },
  async ({ id }) => ({
    content: [{ type: "text", text: JSON.stringify(await fetchData(id)) }],
  })
);

await server.listen({ transport: "sse", port: 4001 });`} filename="mcp-server.ts" />

      <Callout type="note">
        Custom MCP servers must be registered in AgentStore before agents can reference them.
        Use <InlineCode>nuuvixx mcp register --name my-service --url http://localhost:4001</InlineCode>.
      </Callout>
    </article>
  );
}
