"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Box } from "lucide-react";

export default function TypeScriptSdkPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Box className="w-3.5 h-3.5" />
          Agent Development
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">TypeScript SDK</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Build agents in TypeScript/JavaScript with full type safety. Supports Node.js 18+, Edge Runtime,
          and browser environments. First-class Vercel AI SDK compatibility.
        </p>
      </div>

      <DocH2>Installation</DocH2>
      <CodeBlock language="bash" code={`npm install @nuuvixx/sdk
# or yarn / pnpm
pnpm add @nuuvixx/sdk`} />

      <DocH2>Quickstart</DocH2>
      <CodeBlock language="bash" code={`import { Agent, Tool } from "@nuuvixx/sdk";

const agent = new Agent({
  name: "support-agent",
  model: "gemini-2.5-pro",
  tools: [
    Tool.fromMcp("zendesk", { scope: "read" }),
    Tool.fromMcp("slack",   { scope: "write" }),
  ],
  governance: {
    policySet: "enterprise-strict",
    piiScan: true,
  },
});

const result = await agent.run("Summarize the top 3 open tickets");
console.log(result.output);`} filename="agent.ts" />

      <DocH2>Streaming Responses</DocH2>
      <CodeBlock language="bash" code={`import { Agent } from "@nuuvixx/sdk";

const agent = new Agent({ name: "chat-agent", model: "gpt-4o" });

// Stream text output
for await (const chunk of agent.stream("Explain quantum entanglement")) {
  process.stdout.write(chunk.text);
}

// Next.js App Router streaming
export async function POST(req: Request) {
  const { message } = await req.json();
  const stream = agent.toReadableStream(message);
  return new Response(stream);
}`} filename="api/chat/route.ts" />

      <DocH2>Custom Tool Definition</DocH2>
      <CodeBlock language="bash" code={`import { defineTool } from "@nuuvixx/sdk";
import { z } from "zod";

const getWeather = defineTool({
  name: "get_weather",
  description: "Get current weather for a city",
  scope: "read",
  input: z.object({ city: z.string() }),
  handler: async ({ city }) => {
    const res = await fetch(\`https://wttr.in/\${city}?format=j1\`);
    return res.json();
  },
});

const agent = new Agent({
  name: "weather-agent",
  tools: [getWeather],
});`} filename="tools/weather.ts" />

      <DocH2>Publishing to AgentStore</DocH2>
      <CodeBlock language="bash" code={`import { AgentStoreClient } from "@nuuvixx/sdk";
import { readFileSync } from "fs";

const client = new AgentStoreClient({
  apiKey: process.env.NUUVIXX_API_KEY!,
  baseUrl: "http://localhost:8005",
});

// Publish from YAML file
const agentYaml = readFileSync("agent.yaml", "utf-8");
const result = await client.registry.publish({
  agentYaml,
  category: "automation",
});

console.log(\`Published: \${result.slug} @ \${result.currentVersion}\`);`} filename="publish.ts" />

      <DocH2>React / Next.js Integration</DocH2>
      <CodeBlock language="bash" code={`"use client";

import { useAgent } from "@nuuvixx/sdk/react";

export function AgentChat() {
  const { messages, send, isLoading } = useAgent("nuuvixx/support-agent");

  return (
    <div>
      {messages.map(msg => (
        <div key={msg.id}>{msg.content}</div>
      ))}
      <button
        onClick={() => send("What are my open tickets?")}
        disabled={isLoading}
      >
        Ask Agent
      </button>
    </div>
  );
}`} filename="components/AgentChat.tsx" />

      <Callout type="note">
        The TypeScript SDK ships with full type definitions. All tool handlers, agent configs,
        and API responses are typed. Use <InlineCode>import type</InlineCode> for type-only imports
        in performance-critical paths.
      </Callout>
    </article>
  );
}
