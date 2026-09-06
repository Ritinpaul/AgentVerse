import * as vscode from 'vscode';

export class TokenStore {
    private readonly SECRET_KEY = 'agentstudio.enterprise.sso.token';

    constructor(private context: vscode.ExtensionContext) {}

    /**
     * Stores a token securely using VS Code's SecretStorage
     */
    public async storeToken(token: string): Promise<void> {
        await this.context.secrets.store(this.SECRET_KEY, token);
    }

    /**
     * Retrieves the stored token
     */
    public async getToken(): Promise<string | undefined> {
        return await this.context.secrets.get(this.SECRET_KEY);
    }

    /**
     * Clears the stored token
     */
    public async clearToken(): Promise<void> {
        await this.context.secrets.delete(this.SECRET_KEY);
    }
}
