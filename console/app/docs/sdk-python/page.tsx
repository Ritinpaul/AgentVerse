"use client";

import React from "react";
import { DocH2, DocH3, Callout, CodeBlock, InlineCode } from "@/components/docs/DocComponents";
import { Box } from "lucide-react";

export default function PythonSdkPage() {
  return (
    <article className="docs-article">
      <div className="mb-10">
        <div className="flex items-center gap-2 text-[#E5252A] text-xs font-bold tracking-widest uppercase mb-3">
          <Box className="w-3.5 h-3.5" />
          Agent Development
        </div>
        <h1 className="text-4xl font-black text-white mb-4 leading-tight">Python SDK</h1>
        <p className="text-white/60 text-base leading-relaxed font-sans">
          Build, test, and publish agents in Python using the official <InlineCode>nuuvixx</InlineCode> SDK.
          Supports async execution, structured tool interfaces, and direct GovernOS integration.
        </p>
      </div>

      <DocH2>Installation</DocH2>
      <CodeBlock language="bash" code={`pip install nuuvixx-sdk
# or with optional extras:
pip install nuuvixx-sdk[langchain,crewai]`} />

      <DocH2>Quickstart</DocH2>
      <CodeBlock language="python" code={`from nuuvixx import Agent, Tool, GovernOSClient

# Define your agent
agent = Agent(
    name="support-agent",
    model="gemini-2.5-pro",
    tools=[
        Tool.from_mcp("zendesk", scope="read"),
        Tool.from_mcp("slack", scope="write"),
    ],
    governance={
        "policy_set": "enterprise-strict",
        "pii_scan": True,
    }
)

# Run the agent
result = agent.run("Summarize the top 3 open tickets from Zendesk")
print(result.output)`} filename="main.py" />

      <DocH2>Async Execution</DocH2>
      <CodeBlock language="python" code={`import asyncio
from nuuvixx import AsyncAgent

async def main():
    agent = AsyncAgent(
        name="research-agent",
        model="gpt-4o",
    )
    
    # Stream results
    async for chunk in agent.stream("Research quantum computing trends"):
        print(chunk.text, end="", flush=True)

asyncio.run(main())`} filename="async_agent.py" />

      <DocH2>Tool Definition</DocH2>
      <DocH3>Using MCP Servers</DocH3>
      <CodeBlock language="python" code={`from nuuvixx import Tool

# Connect to a registered MCP server
zendesk = Tool.from_mcp("zendesk", scope="read")
slack = Tool.from_mcp("slack", scope="write")

# Custom HTTP tool
my_api = Tool.http(
    name="my-api",
    base_url="https://api.myservice.com",
    auth={"type": "bearer", "token_env": "MY_SERVICE_TOKEN"},
    scope="read",
)`} />

      <DocH3>Custom Python Tools</DocH3>
      <CodeBlock language="python" code={`from nuuvixx import tool

@tool(scope="read", description="Fetch weather for a city")
def get_weather(city: str) -> dict:
    import httpx
    res = httpx.get(f"https://wttr.in/{city}?format=j1")
    return res.json()

# Use in agent
agent = Agent(name="weather-agent", tools=[get_weather])`} />

      <DocH2>Publishing to AgentStore</DocH2>
      <CodeBlock language="python" code={`from nuuvixx import AgentStoreClient

client = AgentStoreClient(api_key="your-api-key")

# Publish from an agent.yaml file
result = client.publish(yaml_path="agent.yaml", category="automation")
print(f"Published: {result.slug} @ {result.current_version}")

# Or publish programmatically
result = client.publish_dict({
    "name": "my-agent",
    "version": "1.0.0",
    "description": "My awesome agent",
})`} />

      <DocH2>GovernOS Integration</DocH2>
      <CodeBlock language="python" code={`from nuuvixx import GovernOSClient

gov = GovernOSClient(
    base_url="http://localhost:8025",
    api_key="your-gov-api-key",
)

# Check agent trust score
agent_info = gov.genesis.get_agent("nuuvixx/support-agent")
print(f"Trust score: {agent_info.trust_score}")

# Submit human approval request
approval = gov.eclipse.request_approval(
    agent_id="nuuvixx/support-agent",
    action="delete_all_tickets",
    reason="Bulk cleanup requested by admin",
)
print(f"Approval ID: {approval.id}, Status: {approval.status}")`} />

      <Callout type="tip">
        Use <InlineCode>NUUVIXX_API_KEY</InlineCode> and <InlineCode>GOVEROS_API_KEY</InlineCode> environment
        variables to avoid hardcoding credentials. The SDK reads them automatically.
      </Callout>

      <DocH2>API Reference</DocH2>
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-white/5 border-b border-white/10">
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Class</th>
              <th className="text-left px-4 py-3 text-white/50 font-bold uppercase tracking-wider">Description</th>
            </tr>
          </thead>
          <tbody>
            {[
              { cls: "Agent",           desc: "Synchronous agent runner with tool dispatch and governance integration." },
              { cls: "AsyncAgent",      desc: "Async agent with stream support. Use in async contexts." },
              { cls: "Tool",            desc: "Tool factory: from_mcp(), http(), builtin(), custom()." },
              { cls: "AgentStoreClient", desc: "AgentStore registry: publish, list, search, versions." },
              { cls: "GovernOSClient",  desc: "GovernOS: genesis, sentinel, pulse, eclipse, audit, gdpr." },
            ].map(row => (
              <tr key={row.cls} className="border-b border-white/6 hover:bg-white/3">
                <td className="px-4 py-3"><code className="text-[#4EC9B0]">{row.cls}</code></td>
                <td className="px-4 py-3 text-white/55 font-sans">{row.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
