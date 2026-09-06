import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class NativeGitService {
    /**
     * Attempts to access the official VS Code Git extension API
     */
    private getGitApi() {
        const gitExtension = vscode.extensions.getExtension('vscode.git');
        if (!gitExtension) {
            return null;
        }
        const exports = gitExtension.exports;
        return exports.getAPI(1);
    }

    public async getStatus() {
        const git = this.getGitApi();
        if (git && git.repositories.length > 0) {
            const repo = git.repositories[0];
            const state = repo.state;
            const branch = state.HEAD?.name || 'main';

            const modifiedFiles = state.workingTreeChanges
                .filter((c: any) => c.status !== 7) // 7 = UNTRACKED
                .map((c: any) => vscode.workspace.asRelativePath(c.uri));

            const untrackedFiles = state.workingTreeChanges
                .filter((c: any) => c.status === 7)
                .map((c: any) => vscode.workspace.asRelativePath(c.uri));

            return {
                branch,
                modifiedFiles,
                untrackedFiles,
                isClean: modifiedFiles.length === 0 && untrackedFiles.length === 0
            };
        }

        // Fallback: run git status via shell in workspace folder
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (workspaceFolder) {
            try {
                const { stdout: branchOut } = await execAsync('git rev-parse --abbrev-ref HEAD', { cwd: workspaceFolder });
                const { stdout: statusOut } = await execAsync('git status --short', { cwd: workspaceFolder });
                
                const branch = branchOut.trim() || 'main';
                const lines = statusOut.split('\n').map(l => l.trim()).filter(Boolean);
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
                    isClean: modifiedFiles.length === 0 && untrackedFiles.length === 0
                };
            } catch (e) {
                console.error('Git status fallback failed:', e);
            }
        }

        return {
            branch: 'main',
            modifiedFiles: [],
            untrackedFiles: [],
            isClean: true
        };
    }

    public async commit(message: string): Promise<boolean> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

        // Try shell command git add -A && git commit -m "..." first (most reliable for unstaged files)
        if (workspaceFolder) {
            try {
                const sanitizedMsg = message.replace(/"/g, '\\"');
                await execAsync(`git add -A && git commit -m "${sanitizedMsg}"`, { cwd: workspaceFolder });
                vscode.window.showInformationMessage(`Git Committed: "${message}"`);
                return true;
            } catch (e: any) {
                console.warn('Git shell commit attempt failed, trying VS Code extension API:', e.message);
            }
        }

        // Fallback: Use VS Code Git Extension API with commit options
        const git = this.getGitApi();
        if (git && git.repositories.length > 0) {
            try {
                const repo = git.repositories[0];
                if (typeof repo.commit === 'function') {
                    await repo.commit(message, { all: true });
                    vscode.window.showInformationMessage(`Git Committed: "${message}"`);
                    return true;
                }
            } catch (e: any) {
                console.error('VS Code git extension commit failed:', e);
                vscode.window.showErrorMessage(`Git commit error: ${e.message || e}`);
                return false;
            }
        }

        vscode.window.showErrorMessage('Git commit failed: No active repository or Git provider available.');
        return false;
    }
}
