import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface DeploymentPolicy {
    minEvalScore: number;
    maxCostPerRun: number;
    requiresCISOApproval: boolean;
}

export interface DeploymentRequest {
    agentId: string;
    evalScore: number;
    estimatedCostPerRun: number;
}

export class DeploymentPolicyService {
    /**
     * Resolves the active deployment policy from workspace or default governance standards
     */
    public async getPolicy(): Promise<DeploymentPolicy> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (workspaceFolder) {
            const policyJsonPath = path.join(workspaceFolder, '.agentstudio', 'policy.json');
            if (fs.existsSync(policyJsonPath)) {
                try {
                    const data = JSON.parse(fs.readFileSync(policyJsonPath, 'utf8'));
                    return {
                        minEvalScore: typeof data.minEvalScore === 'number' ? data.minEvalScore : 90,
                        maxCostPerRun: typeof data.maxCostPerRun === 'number' ? data.maxCostPerRun : 0.50,
                        requiresCISOApproval: data.requiresCISOApproval !== false,
                    };
                } catch {
                    // fall back
                }
            }
        }

        return {
            minEvalScore: 90,
            maxCostPerRun: 0.50,
            requiresCISOApproval: true
        };
    }

    /**
     * Evaluates a deployment request against the current policy
     * Returns true if allowed automatically, false if blocked or requires manual approval
     */
    public async evaluateDeployment(request: DeploymentRequest): Promise<{ allowed: boolean, reason?: string, requiresApproval: boolean }> {
        const policy = await this.getPolicy();
        
        if (request.evalScore < policy.minEvalScore) {
            return { allowed: false, reason: `Evaluation score (${request.evalScore}%) is below the minimum required (${policy.minEvalScore}%).`, requiresApproval: false };
        }
        
        if (request.estimatedCostPerRun > policy.maxCostPerRun) {
            return { allowed: false, reason: `Estimated cost ($${request.estimatedCostPerRun}) exceeds the maximum allowed ($${policy.maxCostPerRun}).`, requiresApproval: false };
        }
        
        if (policy.requiresCISOApproval) {
            return { allowed: false, reason: `Deployment policies require manual CISO approval for all production deployments.`, requiresApproval: true };
        }

        return { allowed: true, requiresApproval: false };
    }
}
