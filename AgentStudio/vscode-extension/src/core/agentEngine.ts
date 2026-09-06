import * as vscode from 'vscode';
import { AgentTools, ToolResult } from './agentTools';

export interface AgentMessage {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'tool';
    type: 'text' | 'diff' | 'run' | 'approval_request';
    content: string;
    timestamp: string;
    toolCall?: {
        name: string;
        args: Record<string, any>;
        status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed';
        result?: ToolResult;
    };
}

export class AgentEngine {
    private static _instance: AgentEngine;
    private _activeRunId: string | null = null;
    private _pendingApprovalResolver: ((approved: boolean) => void) | null = null;

    public static get instance(): AgentEngine {
        if (!this._instance) {
            this._instance = new AgentEngine();
        }
        return this._instance;
    }

    /**
     * Main Agent Execution Loop
     */
    public async runAgentLoop(
        prompt: string,
        modelName: string,
        onEvent: (msg: AgentMessage) => void
    ): Promise<void> {
        const runId = Date.now().toString();
        this._activeRunId = runId;

        // 1. Initial User Message ACK
        onEvent({
            id: `msg-${Date.now()}-1`,
            role: 'assistant',
            type: 'text',
            content: `Analyzing workspace and formulating plan for: "${prompt}"...`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });

        try {
            // Step A: Search context / check workspace
            const statusRes = await AgentTools.gitStatus();
            
            // Step B: Formulate plan & suggested tool call
            if (prompt.toLowerCase().includes('search') || prompt.toLowerCase().includes('find')) {
                const query = prompt.replace(/(search|find|for|in|workspace)/gi, '').trim() || 'agent';
                await this._executeOrRequestTool({
                    name: 'grep_search',
                    args: { query },
                    autoApprove: true,
                }, onEvent);
            } else if (prompt.toLowerCase().includes('list') || prompt.toLowerCase().includes('files')) {
                await this._executeOrRequestTool({
                    name: 'list_dir',
                    args: { dirPath: '.' },
                    autoApprove: true,
                }, onEvent);
            } else if (prompt.toLowerCase().includes('run') || prompt.toLowerCase().includes('test') || prompt.toLowerCase().includes('build')) {
                const cmd = prompt.toLowerCase().includes('test') ? 'npm test' : prompt.toLowerCase().includes('build') ? 'npm run build' : 'git status';
                await this._executeOrRequestTool({
                    name: 'run_command',
                    args: { command: cmd },
                    autoApprove: false, // Shell execution requires user approval
                }, onEvent);
            } else {
                // Default helper guidance
                onEvent({
                    id: `msg-${Date.now()}-reply`,
                    role: 'assistant',
                    type: 'text',
                    content: `I am ready to assist with model **${modelName}**. I can read/write files, apply precision diffs, search workspace, or run terminal commands. What task would you like me to execute?`,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                });
            }
        } catch (err: any) {
            onEvent({
                id: `msg-${Date.now()}-err`,
                role: 'assistant',
                type: 'text',
                content: `An error occurred during execution: ${err.message || err}`,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            });
        } finally {
            this._activeRunId = null;
        }
    }

    /**
     * Execute tool or request user approval if high-risk (e.g. bash commands)
     */
    private async _executeOrRequestTool(
        tool: { name: string; args: Record<string, any>; autoApprove: boolean },
        onEvent: (msg: AgentMessage) => void
    ): Promise<ToolResult> {
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        if (!tool.autoApprove) {
            // Render approval request in UI
            onEvent({
                id: `approval-${Date.now()}`,
                role: 'assistant',
                type: 'approval_request',
                content: `Tool Execution Request: **${tool.name}**\nCommand: \`${tool.args.command || JSON.stringify(tool.args)}\``,
                timestamp,
                toolCall: {
                    name: tool.name,
                    args: tool.args,
                    status: 'pending',
                },
            });

            // Await approval resolution from webview message
            const approved = await new Promise<boolean>((resolve) => {
                this._pendingApprovalResolver = resolve;
            });
            this._pendingApprovalResolver = null;

            if (!approved) {
                const rejectResult: ToolResult = { success: false, output: '', error: 'User rejected tool execution.' };
                onEvent({
                    id: `rejected-${Date.now()}`,
                    role: 'assistant',
                    type: 'text',
                    content: `Tool execution rejected by user.`,
                    timestamp,
                });
                return rejectResult;
            }
        }

        // Execute tool
        onEvent({
            id: `exec-${Date.now()}`,
            role: 'assistant',
            type: 'text',
            content: `Executing \`${tool.name}\`...`,
            timestamp,
        });

        let res: ToolResult;
        switch (tool.name) {
            case 'read_file':
                res = await AgentTools.readFile(tool.args.filePath, tool.args.startLine, tool.args.endLine);
                break;
            case 'write_file':
                res = await AgentTools.writeFile(tool.args.filePath, tool.args.content);
                break;
            case 'apply_diff':
                res = await AgentTools.applyDiff(tool.args.filePath, tool.args.searchStr, tool.args.replaceStr);
                break;
            case 'run_command':
                res = await AgentTools.executeCommand(tool.args.command, (chunk) => {
                    onEvent({
                        id: `stream-${Date.now()}`,
                        role: 'assistant',
                        type: 'run',
                        content: chunk,
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    });
                });
                break;
            case 'grep_search':
                res = await AgentTools.grepSearch(tool.args.query, tool.args.filePattern);
                break;
            case 'list_dir':
                res = await AgentTools.listDir(tool.args.dirPath);
                break;
            default:
                res = { success: false, output: '', error: `Unknown tool: ${tool.name}` };
        }

        if (res.diffData) {
            onEvent({
                id: `diff-${Date.now()}`,
                role: 'assistant',
                type: 'diff',
                content: res.output,
                timestamp,
                toolCall: {
                    name: tool.name,
                    args: tool.args,
                    status: res.success ? 'completed' : 'failed',
                    result: res,
                },
            });
        } else {
            onEvent({
                id: `res-${Date.now()}`,
                role: 'assistant',
                type: 'text',
                content: res.success ? res.output : `Error: ${res.error || 'Execution failed'}`,
                timestamp,
            });
        }

        return res;
    }

    /**
     * Resolve pending user approval gate
     */
    public resolveApproval(approved: boolean): void {
        if (this._pendingApprovalResolver) {
            this._pendingApprovalResolver(approved);
        }
    }
}
