import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import { NativeGitService } from '../core/nativeGit';

const execAsync = promisify(exec);

export interface GitStatus {
    branch: string;
    modifiedFiles: string[];
    untrackedFiles: string[];
    isClean: boolean;
}

export class GitWorkspaceService {
    private nativeGit = new NativeGitService();

    private getCwd(workspacePath?: string): string | undefined {
        return workspacePath || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    }

    /**
     * Queries the actual repository status in the workspace.
     */
    public async getStatus(workspacePath?: string): Promise<GitStatus> {
        const cwd = this.getCwd(workspacePath);
        if (!cwd) {
            return {
                branch: 'main',
                modifiedFiles: [],
                untrackedFiles: [],
                isClean: true,
            };
        }

        try {
            const [branchRes, statusRes] = await Promise.all([
                execAsync('git rev-parse --abbrev-ref HEAD', { cwd }).catch(() => ({ stdout: 'main' })),
                execAsync('git status --short', { cwd }).catch(() => ({ stdout: '' })),
            ]);

            const branch = branchRes.stdout.trim() || 'main';
            const lines = statusRes.stdout.split('\n').map((l) => l.trim()).filter(Boolean);
            const modifiedFiles: string[] = [];
            const untrackedFiles: string[] = [];

            for (const line of lines) {
                const status = line.substring(0, 2);
                const file = line.substring(3).trim();
                if (status.includes('?')) {
                    untrackedFiles.push(file);
                } else {
                    modifiedFiles.push(file);
                }
            }

            return {
                branch,
                modifiedFiles,
                untrackedFiles,
                isClean: modifiedFiles.length === 0 && untrackedFiles.length === 0,
            };
        } catch {
            return this.nativeGit.getStatus();
        }
    }

    /**
     * Executes a git commit operation.
     */
    public async commitChanges(workspacePath: string, message: string): Promise<boolean> {
        const cwd = this.getCwd(workspacePath);
        if (!cwd) {
            vscode.window.showErrorMessage('AgentVerse Git: No workspace folder open.');
            return false;
        }

        try {
            const sanitizedMsg = message.replace(/"/g, '\\"');
            await execAsync(`git add -A && git commit -m "${sanitizedMsg}"`, { cwd });
            vscode.window.showInformationMessage(`Committed changes: "${message}"`);
            return true;
        } catch (e: any) {
            return this.nativeGit.commit(message);
        }
    }

    /**
     * Executes a git push operation to remote origin.
     */
    public async pushChanges(workspacePath: string): Promise<boolean> {
        const cwd = this.getCwd(workspacePath);
        if (!cwd) {
            vscode.window.showErrorMessage('AgentVerse Git: No workspace folder open.');
            return false;
        }

        try {
            await execAsync('git push', { cwd });
            vscode.window.showInformationMessage('Pushed changes to remote origin');
            return true;
        } catch (e: any) {
            vscode.window.showErrorMessage(`Git push failed: ${e.message || e}`);
            return false;
        }
    }

    /**
     * Checks out an existing branch or creates a new one.
     */
    public async checkoutBranch(workspacePath: string, branchName: string): Promise<boolean> {
        const cwd = this.getCwd(workspacePath);
        if (!cwd) {
            vscode.window.showErrorMessage('AgentVerse Git: No workspace folder open.');
            return false;
        }

        try {
            await execAsync(`git checkout ${branchName}`, { cwd });
            vscode.window.showInformationMessage(`Checked out branch: ${branchName}`);
            return true;
        } catch (e: any) {
            vscode.window.showErrorMessage(`Git checkout failed: ${e.message || e}`);
            return false;
        }
    }
}
