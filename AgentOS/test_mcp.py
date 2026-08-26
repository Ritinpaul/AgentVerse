import os
from nuuvixx.mcp import MCPClient

def main():
    print("Testing AgentOS Network Plane & MCP Integration")
    print("===============================================")
    
    # 1. Initialize the MCP Client (simulating an agent running inside AgentOS)
    os.environ["AGENTOS_AGENT_ID"] = "test-mcp-agent-999"
    
    # In local testing outside docker, the network plane is on localhost:8013
    os.environ["AGENTOS_NETWORK_PLANE_URL"] = "http://localhost:8013"
    
    client = MCPClient()
    
    # 2. Make a tool call to the 'sqlite' MCP server
    # We are calling the 'query' tool with a simple SELECT statement
    print(f"\n[Agent {client.agent_id}] Requesting tool call: sqlite -> query")
    try:
        result = client.call_tool(
            server_name="sqlite",
            tool_name="query",
            arguments={"sql": "SELECT 1 as test;"}
        )
        print("\n✅ Tool Call Successful!")
        print("Result from Network Plane:")
        print(result)
    except Exception as e:
        print("\n❌ Tool Call Failed!")
        print(e)
        print("(Note: If this is a 403 Forbidden, it means the mock AgentGovern policy randomly denied the request. Run it again!)")

if __name__ == "__main__":
    main()
