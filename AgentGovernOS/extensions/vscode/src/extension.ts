import * as vscode from 'vscode';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

let mcpClient: Client | undefined;

export async function activate(context: vscode.ExtensionContext) {
  console.log('AgentGovern OS extension is now active!');

  // Register the manual scan command
  let disposable = vscode.commands.registerCommand('agentgovern.scan', async () => {
    vscode.window.showInformationMessage('Starting AgentGovern OS Scan...');
    
    // Create a terminal and run the CLI
    const terminal = vscode.window.createTerminal('AgentGovern');
    terminal.show();
    terminal.sendText('agentgovern scan --format table');
  });

  context.subscriptions.push(disposable);

  // Initialize MCP connection to the AgentGovern MCP server
  try {
    await setupMcpClient();
  } catch (error) {
    console.error('Failed to connect to AgentGovern MCP server:', error);
    vscode.window.showWarningMessage('AgentGovern MCP Server connection failed. AI tools may not have context.');
  }
}

async function setupMcpClient() {
  // In a real environment, this path would point to the built MCP server
  const serverCommand = 'node';
  // Assuming the user is running VSCode from the project root
  const serverArgs = ['mcp/build/index.js'];

  const transport = new StdioClientTransport({
    command: serverCommand,
    args: serverArgs,
  });

  mcpClient = new Client(
    {
      name: "vscode-client",
      version: "1.0.0",
    },
    {
      capabilities: {},
    }
  );

  await mcpClient.connect(transport);
  console.log('Connected to AgentGovern MCP Server');
}

export function deactivate() {
  if (mcpClient) {
    mcpClient.close();
  }
}
