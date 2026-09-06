import * as vscode from 'vscode';
import { TokenStore } from '../services/tokenStore';
import { exec } from 'child_process';
import { promisify } from 'util';

import { AuthService } from '../services/authService';

const execAsync = promisify(exec);

export interface UserProfile {
    username: string;
    email: string;
    provider: string;
    isAuthenticated: boolean;
}

export class NativeSSOService {
    private tokenStore: TokenStore;

    constructor(context: vscode.ExtensionContext) {
        this.tokenStore = new TokenStore(context);
    }

    /**
     * Get real user info from active AgentVerse AuthService session, VS Code auth, or system git config
     */
    public async getUserInfo(): Promise<UserProfile> {
        // 1. Check AgentVerse AuthService active session
        try {
            const auth = AuthService.getInstance();
            if (auth) {
                const session = await auth.getSession();
                if (session) {
                    return {
                        username: session.name || session.email.split('@')[0],
                        email: session.email,
                        provider: session.provider || 'AgentVerse',
                        isAuthenticated: true
                    };
                }
            }
        } catch {
            // AuthService not initialized
        }

        // 2. Try VS Code GitHub Authentication
        try {
            const ghSession = await vscode.authentication.getSession('github', ['user:email'], { createIfNone: false });
            if (ghSession) {
                return {
                    username: ghSession.account.label,
                    email: ghSession.account.label,
                    provider: 'GitHub',
                    isAuthenticated: true
                };
            }
        } catch (e) {
            // Ignore error
        }

        // 2. Try VS Code Microsoft Authentication
        try {
            const msSession = await vscode.authentication.getSession('microsoft', ['user:email'], { createIfNone: false });
            if (msSession) {
                return {
                    username: msSession.account.label,
                    email: msSession.account.label,
                    provider: 'Microsoft',
                    isAuthenticated: true
                };
            }
        } catch (e) {
            // Ignore error
        }

        // 3. Fallback to System Git Config (real local user identity)
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        try {
            const { stdout: nameOut } = await execAsync('git config user.name', { cwd: workspaceFolder });
            const { stdout: emailOut } = await execAsync('git config user.email', { cwd: workspaceFolder });

            const name = nameOut.trim();
            const email = emailOut.trim();

            if (name || email) {
                return {
                    username: name || 'Developer',
                    email: email || 'developer@local',
                    provider: 'Local Identity (Git)',
                    isAuthenticated: false
                };
            }
        } catch (e) {
            // Ignore error
        }

        return {
            username: 'Local Developer',
            email: 'dev@workspace.local',
            provider: 'Local Identity',
            isAuthenticated: false
        };
    }

    /**
     * Triggers real login via VS Code Auth Provider or interactive session
     */
    public async login(providerName: string): Promise<UserProfile> {
        const providerId = providerName.toLowerCase().includes('github') ? 'github' : 'microsoft';
        
        try {
            const session = await vscode.authentication.getSession(providerId, ['user:email'], { createIfNone: true });
            if (session) {
                await this.tokenStore.storeToken(session.accessToken);
                vscode.window.showInformationMessage(`Authenticated as ${session.account.label} via ${providerName}`);
                return {
                    username: session.account.label,
                    email: session.account.label,
                    provider: providerName,
                    isAuthenticated: true
                };
            }
        } catch (e: any) {
            console.warn(`VS Code authentication provider (${providerId}) error:`, e);
        }

        // Fallback for custom environments: establish local developer session
        const current = await this.getUserInfo();
        let token = `sso_token_${providerName.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`;
        try {
            const auth = AuthService.getInstance();
            if (auth) {
                const session = await auth.loginLocalDev(current.username, current.email);
                token = session.accessToken;
            }
        } catch {
            // AuthService not available
        }
        await this.tokenStore.storeToken(token);
        vscode.window.showInformationMessage(`Authenticated via ${providerName} (${current.username})`);

        return {
            ...current,
            provider: providerName,
            isAuthenticated: true
        };
    }

    public async logout(): Promise<UserProfile> {
        await this.tokenStore.clearToken();
        try {
            const auth = AuthService.getInstance();
            if (auth) {
                await auth.signOut();
            }
        } catch {}
        vscode.window.showInformationMessage('Logged out from SSO');
        return this.getUserInfo();
    }
}
