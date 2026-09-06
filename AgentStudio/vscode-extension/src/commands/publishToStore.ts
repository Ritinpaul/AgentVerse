/**
 * Publish to AgentStore command.
 *
 * Bridge 1 (AgentStudio → AgentStore):
 *   1. Finds agent.yaml in workspace
 *   2. Parses it and sends to AgentStore POST /api/v1/registry/agents
 *   3. Shows trust score in-editor notification
 *   4. Auto-opens marketplace listing in browser
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { AgentStoreClient } from '../services/agentStoreClient';

export async function publishToStore(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('AgentStudio: Please open a workspace folder first.');
        return;
    }

    // ── 1. Locate agent.yaml ─────────────────────────────────────────────────
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const manifestPath = path.join(workspaceRoot, 'agent.yaml');

    if (!fs.existsSync(manifestPath)) {
        const create = await vscode.window.showWarningMessage(
            'No agent.yaml found in workspace root. Create one?',
            'Create agent.yaml',
            'Cancel'
        );
        if (create === 'Create agent.yaml') {
            const template = generateManifestTemplate(workspaceRoot);
            fs.writeFileSync(manifestPath, template);
            const doc = await vscode.workspace.openTextDocument(manifestPath);
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage('agent.yaml created. Fill in the details and run Publish again.');
        }
        return;
    }

    // ── 2. Parse YAML ─────────────────────────────────────────────────────────
    let manifestData: Record<string, unknown>;
    try {
        const rawYaml = fs.readFileSync(manifestPath, 'utf-8');
        manifestData = yaml.load(rawYaml) as Record<string, unknown>;
    } catch (err) {
        vscode.window.showErrorMessage(`AgentStudio: Failed to parse agent.yaml — ${String(err)}`);
        return;
    }

    // ── 3. Publish to AgentStore ───────────────────────────────────────────────
    const client = new AgentStoreClient(context);

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'AgentStudio: Publishing to AgentStore...',
            cancellable: false,
        },
        async (progress) => {
            progress.report({ message: 'Running ASI01–ASI10 security scan...' });

            const result = await client.publishAgent(manifestData);

            if (!result.success || !result.listing) {
                vscode.window.showErrorMessage(
                    `AgentStore Publish Failed: ${result.error ?? 'Unknown error'}`
                );
                return;
            }

            const { listing } = result;
            const trustScore = listing.trust_score ?? 0;
            const scoreLabel = trustScore >= 80 ? '[PASS]' : trustScore >= 60 ? '[WARN]' : '[RISK]';

            progress.report({ message: `Trust Score: ${scoreLabel} ${trustScore}/100 — Opening marketplace...` });

            // ── 4. Show trust score notification ─────────────────────────────
            const action = await vscode.window.showInformationMessage(
                `Published to AgentStore!\n` +
                `Agent: ${listing.builder}/${listing.name}\n` +
                `Trust Score: ${scoreLabel} ${trustScore}/100\n` +
                `Status: ${listing.status}`,
                'Open in Marketplace',
                'View Revenue',
                'Dismiss'
            );

            if (action === 'Open in Marketplace') {
                client.openInMarketplace(listing.builder, listing.name);
            } else if (action === 'View Revenue') {
                vscode.env.openExternal(
                    vscode.Uri.parse(`${client.storeUrl}/api/v1/billing/builders/${listing.builder}/revenue`)
                );
            }
        }
    );
}

/**
 * Generate a starter agent.yaml template.
 */
function generateManifestTemplate(workspaceRoot: string): string {
    const folderName = path.basename(workspaceRoot).toLowerCase().replace(/\s+/g, '-');
    return `# Nuuvixx Agent Manifest — agent.yaml
# Reference: https://docs.nuuvixx.ai/schema

apiVersion: nuuvixx/v1
kind: Agent

metadata:
  name: ${folderName}
  description: "A description of what this agent does."
  version: "1.0.0"
  builder: your-nuuvixx-username   # Your AgentStore builder ID
  tags:
    - productivity
    - automation

spec:
  entrypoint: main.py           # Entry point file
  runtime: python3.11           # Runtime environment
  capabilities:
    - text-processing
  mcp_servers:
    - name: filesystem
      command: mcp-server-filesystem

pricing:
  model: per_call               # free | per_call | subscription
  price_per_call_usd: 0.00

metadata_extended:
  homepage: ""
  source_code: ""
  license: MIT
`;
}
