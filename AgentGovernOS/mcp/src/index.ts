import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Define the AgentGovern API URL
const AGENTGOVERN_API_URL = process.env.AGENTGOVERN_API_URL || "http://127.0.0.1:8000";

const server = new Server(
  {
    name: "agentgovern-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "evaluate_action",
        description:
          "Evaluate an agent's proposed action against the AgentGovern OS policies. Use this before an agent executes a tool or performs a critical action.",
        inputSchema: {
          type: "object",
          properties: {
            agent_id: { type: "string", description: "The ID of the agent proposing the action." },
            intent: { type: "string", description: "The description of the intended action." },
            context: {
              type: "object",
              description: "Optional key-value context for the policy evaluation.",
            },
          },
          required: ["agent_id", "intent"],
        },
      },
      {
        name: "get_trust_score",
        description: "Retrieve the current trust score for an agent.",
        inputSchema: {
          type: "object",
          properties: {
            agent_id: { type: "string", description: "The ID of the agent." },
          },
          required: ["agent_id"],
        },
      },
    ],
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!args) {
    throw new Error(`Missing arguments for tool ${name}`);
  }

  try {
    if (name === "evaluate_action") {
      const { agent_id, intent, context } = args as Record<string, any>;
      
      const response = await fetch(`${AGENTGOVERN_API_URL}/api/v1/sentinel/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id,
          intent,
          context: context || {},
          caller_id: "mcp-client", // Indicates it's being requested via MCP/IDE
        }),
      });

      if (!response.ok) {
        throw new Error(`AgentGovern API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } 
    
    if (name === "get_trust_score") {
      const { agent_id } = args as Record<string, any>;
      
      const response = await fetch(`${AGENTGOVERN_API_URL}/api/v1/pulse/trust/${agent_id}`);
      
      if (!response.ok) {
        throw new Error(`AgentGovern API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error: any) {
    return {
      content: [{ type: "text", text: `Error executing tool ${name}: ${error.message}` }],
      isError: true,
    };
  }
});

// Start the server using stdio transport
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("AgentGovern MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Failed to start AgentGovern MCP Server:", error);
  process.exit(1);
});
