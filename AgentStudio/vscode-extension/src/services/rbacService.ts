import { AuthService } from './authService';
import { exec } from 'child_process';
import * as vscode from 'vscode';

export type UserRole = 'owner' | 'admin' | 'write' | 'triage' | 'read' | 'developer' | 'team_lead' | 'ciso' | 'auditor';

export interface UserContext {
    username: string;
    role: UserRole;
    email: string;
}

export class RBACService {
    /**
     * Resolves the current user context from active AuthService session
     * or local workspace git identity.
     */
    public async getCurrentUser(): Promise<UserContext> {
        try {
            const auth = AuthService.getInstance();
            if (auth) {
                const session = await auth.getSession();
                if (session) {
                    const role = (session.role?.toLowerCase() as UserRole) || 'owner';
                    return {
                        username: session.name || session.email.split('@')[0],
                        role: RBACService.ROLE_PERMISSIONS[role] ? role : 'developer',
                        email: session.email,
                    };
                }
            }
        } catch {
            // AuthService not yet initialized
        }

        // Fallback: detect local git user
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        try {
            const [gitName, gitEmail] = await Promise.all([
                new Promise<string>((res) => exec('git config user.name', { cwd: workspaceFolder }, (_, out) => res(out.trim()))),
                new Promise<string>((res) => exec('git config user.email', { cwd: workspaceFolder }, (_, out) => res(out.trim()))),
            ]);
            if (gitName || gitEmail) {
                return {
                    username: gitName || 'Local Developer',
                    role: 'developer',
                    email: gitEmail || 'developer@local.workspace',
                };
            }
        } catch {
            // git config failed
        }

        return {
            username: 'Developer',
            role: 'developer',
            email: 'dev@local.workspace',
        };
    }

    /**
     * GitHub Standard Role Permission Matrix
     */
    public static readonly ROLE_PERMISSIONS: Record<UserRole, string[]> = {
        owner: ['*'], // Full unrestricted root permission
        admin: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'edit_policy', 'approve_production', 'manage_team_keys'],
        write: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'deploy_staging'],
        triage: ['run_locally', 'test_agent', 'view_dashboard', 'approve_staging'],
        read: ['view_dashboard', 'view_audit'],
        // Backward Compatible Aliases
        developer: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'deploy_staging'],
        team_lead: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'edit_policy', 'approve_staging'],
        ciso: ['view_dashboard', 'view_audit', 'approve_production', 'edit_policy'],
        auditor: ['view_dashboard', 'view_audit']
    };

    /**
     * Check if a specific role has a permission
     */
    public can(role: UserRole, action: string): boolean {
        const permissions = RBACService.ROLE_PERMISSIONS[role] || [];
        return permissions.includes(action);
    }
}
