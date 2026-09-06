import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';

export interface ToolResult {
    success: boolean;
    output: string;
    error?: string;
    diffData?: {
        filename: string;
        added: number;
        removed: number;
        diffLines: Array<{ lineNum: number; type: 'context' | 'added' | 'removed'; prefix: string; content: string }>;
    };
}

export class AgentTools {

    private static getWorkspaceRoot(): string {
        const folder = vscode.workspace.workspaceFolders?.[0];
        if (!folder) {
            throw new Error('No workspace folder is currently open.');
        }
        return folder.uri.fsPath;
    }

    private static resolvePath(filePath: string): string {
        if (path.isAbsolute(filePath)) {
            return filePath;
        }
        return path.join(this.getWorkspaceRoot(), filePath);
    }

    /**
     * Read file contents from workspace
     */
    public static async readFile(filePath: string, startLine?: number, endLine?: number): Promise<ToolResult> {
        try {
            const absPath = this.resolvePath(filePath);
            const uri = vscode.Uri.file(absPath);
            const bytes = await vscode.workspace.fs.readFile(uri);
            const content = new TextDecoder().decode(bytes);

            const lines = content.split('\n');
            if (startLine !== undefined || endLine !== undefined) {
                const start = Math.max(0, (startLine ?? 1) - 1);
                const end = endLine ? Math.min(lines.length, endLine) : lines.length;
                const sliced = lines.slice(start, end).join('\n');
                return {
                    success: true,
                    output: `--- Lines ${start + 1}-${end} of ${filePath} ---\n${sliced}`,
                };
            }

            return {
                success: true,
                output: content,
            };
        } catch (err: any) {
            return {
                success: false,
                output: '',
                error: `Failed to read file ${filePath}: ${err.message || err}`,
            };
        }
    }

    /**
     * Write new file or overwrite file in workspace
     */
    public static async writeFile(filePath: string, content: string): Promise<ToolResult> {
        try {
            const absPath = this.resolvePath(filePath);
            const uri = vscode.Uri.file(absPath);
            const bytes = new TextEncoder().encode(content);
            await vscode.workspace.fs.writeFile(uri, bytes);

            return {
                success: true,
                output: `Successfully wrote ${content.length} bytes to ${filePath}`,
            };
        } catch (err: any) {
            return {
                success: false,
                output: '',
                error: `Failed writing file ${filePath}: ${err.message || err}`,
            };
        }
    }

    /**
     * Apply a targeted string diff / replacement to a file
     */
    public static async applyDiff(filePath: string, searchStr: string, replaceStr: string): Promise<ToolResult> {
        try {
            const absPath = this.resolvePath(filePath);
            const uri = vscode.Uri.file(absPath);
            const bytes = await vscode.workspace.fs.readFile(uri);
            const originalContent = new TextDecoder().decode(bytes);

            if (!originalContent.includes(searchStr)) {
                return {
                    success: false,
                    output: '',
                    error: `Search string not found in ${filePath}. Target text must match exact characters.`,
                };
            }

            const updatedContent = originalContent.replace(searchStr, replaceStr);
            await vscode.workspace.fs.writeFile(uri, new TextEncoder().encode(updatedContent));

            // Generate diff lines for webview
            const searchLines = searchStr.split('\n');
            const replaceLines = replaceStr.split('\n');
            const diffLines: Array<{ lineNum: number; type: 'context' | 'added' | 'removed'; prefix: string; content: string }> = [];

            let lineNum = 1;
            searchLines.forEach(l => diffLines.push({ lineNum: lineNum++, type: 'removed', prefix: '-', content: l }));
            replaceLines.forEach(l => diffLines.push({ lineNum: lineNum++, type: 'added', prefix: '+', content: l }));

            return {
                success: true,
                output: `Applied diff to ${filePath}`,
                diffData: {
                    filename: filePath,
                    added: replaceLines.length,
                    removed: searchLines.length,
                    diffLines,
                },
            };
        } catch (err: any) {
            return {
                success: false,
                output: '',
                error: `Failed applying diff to ${filePath}: ${err.message || err}`,
            };
        }
    }

    /**
     * Execute a shell command in workspace terminal
     */
    public static async executeCommand(
        command: string,
        onStdoutData?: (chunk: string) => void
    ): Promise<ToolResult> {
        return new Promise((resolve) => {
            const root = this.getWorkspaceRoot();

            const child = exec(command, { cwd: root, maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
                const combinedOutput = stdout + (stderr ? `\n[stderr]\n${stderr}` : '');
                if (err) {
                    resolve({
                        success: false,
                        output: combinedOutput,
                        error: `Command failed with exit code ${err.code || 1}: ${err.message}`,
                    });
                } else {
                    resolve({
                        success: true,
                        output: combinedOutput,
                    });
                }
            });

            if (onStdoutData && child.stdout) {
                child.stdout.on('data', (data) => onStdoutData(data.toString()));
            }
            if (onStdoutData && child.stderr) {
                child.stderr.on('data', (data) => onStdoutData(data.toString()));
            }
        });
    }

    /**
     * Search files using ripgrep / glob pattern
     */
    public static async grepSearch(query: string, filePattern?: string): Promise<ToolResult> {
        try {
            const pattern = filePattern || '**/*';
            const uris = await vscode.workspace.findFiles(pattern, '**/node_modules/**');
            const matches: string[] = [];

            for (const uri of uris.slice(0, 100)) {
                try {
                    const bytes = await vscode.workspace.fs.readFile(uri);
                    const content = new TextDecoder().decode(bytes);
                    const relPath = vscode.workspace.asRelativePath(uri);

                    content.split('\n').forEach((line, idx) => {
                        if (line.toLowerCase().includes(query.toLowerCase())) {
                            matches.push(`${relPath}:${idx + 1}: ${line.trim()}`);
                        }
                    });
                } catch {
                    // skip binary/unreadable
                }
            }

            return {
                success: true,
                output: matches.length > 0
                    ? `Found ${matches.length} matches for "${query}":\n` + matches.slice(0, 50).join('\n')
                    : `No matches found for "${query}"`,
            };
        } catch (err: any) {
            return {
                success: false,
                output: '',
                error: `Grep search failed: ${err.message || err}`,
            };
        }
    }

    /**
     * List directory contents
     */
    public static async listDir(dirPath: string = '.'): Promise<ToolResult> {
        try {
            const absPath = this.resolvePath(dirPath);
            const uri = vscode.Uri.file(absPath);
            const entries = await vscode.workspace.fs.readDirectory(uri);

            const formatted = entries.map(([name, type]) => {
                const isDir = type === vscode.FileType.Directory;
                return `${isDir ? '[DIR] ' : '[FILE]'} ${name}`;
            }).join('\n');

            return {
                success: true,
                output: `Contents of ${dirPath}:\n${formatted}`,
            };
        } catch (err: any) {
            return {
                success: false,
                output: '',
                error: `Failed listing directory ${dirPath}: ${err.message || err}`,
            };
        }
    }

    /**
     * Git status inspection
     */
    public static async gitStatus(): Promise<ToolResult> {
        return this.executeCommand('git status --short');
    }
}
