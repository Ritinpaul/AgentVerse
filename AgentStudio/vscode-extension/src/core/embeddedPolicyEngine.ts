/**
 * src/core/embeddedPolicyEngine.ts
 *
 * LocalPolicyAdvisor — Provides immediate, offline policy hints within the IDE.
 *
 * NOTE: Local policy evaluations are ADVISORY ONLY for rapid UX feedback.
 * Authoritative security policy enforcement is performed server-side by AgentGovernOS SENTINEL.
 */

let vscode: any;
try {
  vscode = require('vscode');
} catch (e) {
  vscode = null;
}
import * as fs from 'fs';
import * as path from 'path';

export interface DeploymentPolicy {
  minEvalScore: number;
  maxCostPerRun: number;
  requiresCISOApproval: boolean;
  isAdvisoryOnly?: boolean;
}

export interface IAMPolicyEvaluationResult {
  allowed: boolean;
  reason: string;
  assumedRoleArn: string;
}

export class LocalPolicyAdvisor {
  /** Indicates to callers and UI that local policy checks are advisory hints */
  public readonly isAuthoritative: boolean = false;

  private getPolicyPath(): string | null {
    if (!vscode || !vscode.workspace) return null;
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) return null;

    const dir = path.join(workspaceFolders[0].uri.fsPath, '.agentstudio');
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    return path.join(dir, 'policies.json');
  }

  public getPolicy(): DeploymentPolicy {
    const policyPath = this.getPolicyPath();
    if (policyPath && fs.existsSync(policyPath)) {
      try {
        const data = fs.readFileSync(policyPath, 'utf8');
        const parsed = JSON.parse(data);
        return {
          ...parsed,
          isAdvisoryOnly: true,
        };
      } catch (e) {
        console.error('Failed to read local policy advisor file', e);
      }
    }

    // Default fallback advisory policy
    return {
      minEvalScore: 90,
      maxCostPerRun: 0.50,
      requiresCISOApproval: true,
      isAdvisoryOnly: true,
    };
  }

  public savePolicy(policy: DeploymentPolicy): boolean {
    const policyPath = this.getPolicyPath();
    if (!policyPath) return false;

    try {
      fs.writeFileSync(policyPath, JSON.stringify(policy, null, 2), 'utf8');
      return true;
    } catch (e) {
      console.error('Failed to write local policy advisor file', e);
      return false;
    }
  }

  /** Advisory check for AWS IAM Role ARN actions */
  public evaluateArnAction(roleArn: string, action: string, resourceArn?: string): IAMPolicyEvaluationResult {
    const roleName = roleArn.split('/').pop() || 'DeveloperRole';

    if (roleName === 'OwnerRole' || roleName === 'AdminRole') {
      return {
        allowed: true,
        reason: `Action ${action} permitted under elevated ${roleName} session`,
        assumedRoleArn: roleArn
      };
    }

    if (action.startsWith('iam:Delete') || action.startsWith('billing:')) {
      return {
        allowed: false,
        reason: `Action ${action} requires OwnerRole elevated session`,
        assumedRoleArn: roleArn
      };
    }

    return {
      allowed: true,
      reason: `Advisory allow for ${action} under ${roleName}`,
      assumedRoleArn: roleArn
    };
  }
}

// Backward compatibility alias for legacy callers
export const EmbeddedPolicyEngine = LocalPolicyAdvisor;
export type EmbeddedPolicyEngine = LocalPolicyAdvisor;
