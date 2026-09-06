/**
 * src/core/embeddedRBACEngine.ts
 *
 * LocalRBACHint — Provides local role hint resolution for IDE UI rendering.
 *
 * NOTE: Local role resolution is ADVISORY ONLY for UI menu visibility hints.
 * Authoritative user authentication and authorization checks are enforced server-side
 * by AgentGovernOS AUTH and Control Plane API Gateway.
 */

let vscode: any;
try {
  vscode = require('vscode');
} catch (e) {
  vscode = null;
}
import * as fs from 'fs';
import * as path from 'path';

export type UserRole = 'developer' | 'team_lead' | 'ciso' | 'auditor';

export interface RBACMember {
  email: string;
  role: UserRole;
  name?: string;
}

export interface RBACConfig {
  defaultRole: UserRole;
  members: RBACMember[];
}

export class LocalRBACHint {
  public readonly isAuthoritative: boolean = false;

  private getRBACPath(): string | null {
    if (!vscode || !vscode.workspace) return null;
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) return null;

    const dir = path.join(workspaceFolders[0].uri.fsPath, '.agentstudio');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    return path.join(dir, 'rbac.json');
  }

  public getRBACConfig(): RBACConfig {
    const rbacPath = this.getRBACPath();
    if (rbacPath && fs.existsSync(rbacPath)) {
      try {
        const data = fs.readFileSync(rbacPath, 'utf8');
        return JSON.parse(data);
      } catch (e) {
        console.error('Failed to read rbac.json file', e);
      }
    }

    // Default initial team & roles config
    return {
      defaultRole: 'developer',
      members: [],
    };
  }

  public saveRBACConfig(config: RBACConfig): boolean {
    const rbacPath = this.getRBACPath();
    if (!rbacPath) return false;

    try {
      fs.writeFileSync(rbacPath, JSON.stringify(config, null, 2), 'utf8');
      return true;
    } catch (e) {
      console.error('Failed to write rbac.json file', e);
      return false;
    }
  }

  public resolveUserRole(email?: string): UserRole {
    if (!email) return 'developer';

    const config = this.getRBACConfig();
    const normalizedEmail = email.trim().toLowerCase();

    const match = config.members.find((m) => m.email.trim().toLowerCase() === normalizedEmail);
    if (match) {
      return match.role;
    }

    return config.defaultRole || 'developer';
  }
}

// Backward compatibility alias for legacy callers
export const EmbeddedRBACEngine = LocalRBACHint;
export type EmbeddedRBACEngine = LocalRBACHint;
