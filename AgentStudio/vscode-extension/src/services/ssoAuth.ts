import * as vscode from 'vscode';
import { AuthService } from './authService';

/**
 * Compatibility shim — delegates to the real AuthService (Supabase PKCE).
 * Kept to avoid mass-refactoring of existing callers in extension.ts,
 * signInStatusBar.ts, and runAgent.ts.
 */
export class SSOAuthService {
  private auth: AuthService;

  constructor(context: vscode.ExtensionContext) {
    this.auth = AuthService.getInstance(context);
  }

  public async login(provider: 'Okta' | 'AzureAD' | 'Google'): Promise<boolean> {
    // Map legacy provider names → Supabase OAuth providers
    const supabaseProvider = provider === 'Google' ? 'google' : 'github';
    await this.auth.signIn(supabaseProvider);
    return this.auth.isAuthenticated();
  }

  public async logout(): Promise<void> {
    await this.auth.signOut();
  }

  public async isAuthenticated(): Promise<boolean> {
    return this.auth.isAuthenticated();
  }
}
