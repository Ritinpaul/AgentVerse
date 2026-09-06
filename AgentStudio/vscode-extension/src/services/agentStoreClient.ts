/**
 * AgentStore API Client for AgentStudio VS Code Extension.
 * Handles publish, trust score retrieval, and billing via the AgentStore backend.
 *
 * Bridge 1: AgentStudio → AgentStore (Publish Pipeline)
 */
import * as vscode from 'vscode';

export interface AgentStoreListing {
    id: string;
    slug: string;            // e.g. "nuuvixx/support-agent"
    name: string;
    builder: string;
    trust_score: number;     // 0–100
    status: string;          // "listed" | "pending_review" | "rejected"
    marketplace_url: string;
}

export interface AgentStorePublishResult {
    success: boolean;
    listing?: AgentStoreListing;
    error?: string;
    trust_score?: number;
    scan_results?: Record<string, string>; // ASI rule → pass/fail
}

export class AgentStoreClient {
    private readonly baseUrl: string;
    private readonly apiKey: string | undefined;

    constructor(private context: vscode.ExtensionContext) {
        const config = vscode.workspace.getConfiguration('nuuvixx');
        this.baseUrl = config.get<string>('agentStoreUrl') ?? 'http://127.0.0.1:8005';
        this.apiKey = config.get<string>('apiKey');
    }

    /**
     * Returns common headers for all AgentStore API requests.
     */
    private buildHeaders(): Record<string, string> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        // Retrieve stored JWT token from VS Code SecretStorage
        return headers;
    }

    /**
     * Returns common headers with a JWT token if available.
     */
    private async buildAuthHeaders(): Promise<Record<string, string>> {
        const headers = this.buildHeaders();
        try {
            const token = await this.context.secrets.get('agentstudio.enterprise.sso.token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        } catch {
            // No token stored — will fall back to API key auth
        }
        return headers;
    }

    /**
     * Publishes an agent manifest to the AgentStore marketplace.
     * Triggers ASI01–ASI10 security scan and returns trust score.
     */
    public async publishAgent(manifestData: Record<string, unknown>): Promise<AgentStorePublishResult> {
        const headers = await this.buildAuthHeaders();
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/registry/agents`, {
                method: 'POST',
                headers,
                body: JSON.stringify(manifestData),
            });

            if (!response.ok) {
                const errorBody = await response.text();
                return {
                    success: false,
                    error: `AgentStore returned ${response.status}: ${errorBody}`,
                };
            }

            const listing = await response.json() as AgentStoreListing;
            return {
                success: true,
                listing,
                trust_score: listing.trust_score,
            };
        } catch (err) {
            return {
                success: false,
                error: `Network error: ${String(err)}`,
            };
        }
    }

    /**
     * Fetches an existing listing by slug.
     */
    public async getListing(builder: string, agentName: string): Promise<AgentStoreListing | null> {
        const headers = await this.buildAuthHeaders();
        try {
            const response = await fetch(
                `${this.baseUrl}/api/v1/registry/agents/${builder}/${agentName}`,
                { headers }
            );
            if (!response.ok) { return null; }
            return await response.json() as AgentStoreListing;
        } catch {
            return null;
        }
    }

    /**
     * Triggers an on-demand ASI security scan for an already-listed agent.
     */
    public async triggerScan(builder: string, agentName: string): Promise<{ scan_id: string } | null> {
        const headers = await this.buildAuthHeaders();
        try {
            const response = await fetch(
                `${this.baseUrl}/api/v1/verification/agents/${builder}/${agentName}/scan/trigger`,
                { method: 'POST', headers }
            );
            if (!response.ok) { return null; }
            return await response.json() as { scan_id: string };
        } catch {
            return null;
        }
    }

    /**
     * Returns the revenue summary for a builder.
     */
    public async getRevenueSummary(builderId: string): Promise<Record<string, unknown> | null> {
        const headers = await this.buildAuthHeaders();
        try {
            const response = await fetch(
                `${this.baseUrl}/api/v1/billing/builders/${builderId}/revenue`,
                { headers }
            );
            if (!response.ok) { return null; }
            return await response.json() as Record<string, unknown>;
        } catch {
            return null;
        }
    }

    /** Exposes the resolved base URL for display purposes */
    public get storeUrl(): string { return this.baseUrl; }

    /** Opens the marketplace page for a listing in the system browser */
    public openInMarketplace(builder: string, agentName: string): void {
        const frontendUrl = vscode.workspace.getConfiguration('nuuvixx')
            .get<string>('agentStoreFrontendUrl') ?? 'http://127.0.0.1:8050';
        const url = vscode.Uri.parse(`${frontendUrl}/agents/${builder}/${agentName}`);
        vscode.env.openExternal(url);
    }
}
