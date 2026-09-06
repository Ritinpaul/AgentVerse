import * as vscode from 'vscode';
import * as http from 'http';
import * as https from 'https';
import * as crypto from 'crypto';
import { exec } from 'child_process';
import { URL, URLSearchParams } from 'url';
import { SettingsService } from './settingsService';

// ── Supabase config (read from product-level defaults; override via workspace settings) ──
const SUPABASE_URL = 'https://gwxmsimttmcqcmyhyhdz.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd3eG1zaW10dG1jcWNteWh5aGR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3MDczMjgsImV4cCI6MjEwNDI4MzMyOH0.flPXjZRtYzQkasf_GX9ZW8yO4O2e_Sab-K0DQpo24SM';

const GOVERN_OS_URL = 'http://localhost:8000';

const SECRET_ACCESS_TOKEN = 'agentverse.auth.access_token';
const SECRET_REFRESH_TOKEN = 'agentverse.auth.refresh_token';
const SECRET_USER_EMAIL = 'agentverse.auth.user_email';
const SECRET_USER_ID = 'agentverse.auth.user_id';
const SECRET_USER_NAME = 'agentverse.auth.user_name';
const SECRET_USER_ROLE = 'agentverse.auth.user_role';
const SECRET_USER_ORG = 'agentverse.auth.user_org';
const SECRET_USER_TIER = 'agentverse.auth.user_tier';
const SECRET_PROVIDER = 'agentverse.auth.provider';

const REDIRECT_URI = 'vscode://nuuvixx.agentstudio-core/auth-callback';

export interface AgentVerseSession {
  userId: string;
  email: string;
  name?: string;
  role?: string;
  orgName?: string;
  orgSlug?: string;
  orgTier?: string;
  accessToken: string;
  refreshToken: string;
  provider?: string;
}

// ── PKCE helpers ───────────────────────────────────────────────────────────

function generateCodeVerifier(): string {
  return crypto.randomBytes(32).toString('base64url');
}

function generateCodeChallenge(verifier: string): string {
  return crypto.createHash('sha256').update(verifier).digest('base64url');
}

// ── Universal HTTP/HTTPS POST helper ───────────────────────────────────────

async function postJson(
  url: string,
  body: Record<string, any>,
  headers: Record<string, string> = {},
  timeoutMs: number = 8000
): Promise<{ ok: boolean; status: number; data: any }> {
  return new Promise((resolve) => {
    try {
      const parsed = new URL(url);
      const payload = JSON.stringify(body);
      const client = parsed.protocol === 'http:' ? http : https;

      const req = client.request(
        {
          hostname: parsed.hostname,
          port: parsed.port || (parsed.protocol === 'http:' ? 80 : 443),
          path: parsed.pathname + parsed.search,
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(payload),
            ...headers,
          },
          timeout: timeoutMs,
        },
        (res) => {
          let rawData = '';
          res.on('data', (chunk) => (rawData += chunk));
          res.on('end', () => {
            let parsedData: any = rawData;
            try {
              parsedData = JSON.parse(rawData);
            } catch {
              // raw string
            }
            resolve({
              ok: (res.statusCode || 0) >= 200 && (res.statusCode || 0) < 300,
              status: res.statusCode || 0,
              data: parsedData,
            });
          });
        }
      );

      req.on('error', (err) => {
        resolve({ ok: false, status: 0, data: { detail: err.message } });
      });
      req.on('timeout', () => {
        req.destroy();
        resolve({ ok: false, status: 408, data: { detail: 'Request timed out' } });
      });
      req.write(payload);
      req.end();
    } catch (e: any) {
      resolve({ ok: false, status: 0, data: { detail: e.message } });
    }
  });
}

// ── AuthService ────────────────────────────────────────────────────────────

export class AuthService {
  private static _instance: AuthService;

  /** Fires whenever sign-in or sign-out completes. */
  private readonly _onDidAuthChange = new vscode.EventEmitter<AgentVerseSession | null>();
  public readonly onDidAuthChange = this._onDidAuthChange.event;

  /** Pending PKCE code-verifier (stored between browser launch and callback). */
  private _pendingVerifier: string | undefined;
  private _refreshTimer: NodeJS.Timeout | undefined;
  private _uriHandler: vscode.Disposable | undefined;

  private constructor(private readonly context: vscode.ExtensionContext) {}

  public static getInstance(context?: vscode.ExtensionContext): AuthService {
    if (!AuthService._instance && context) {
      AuthService._instance = new AuthService(context);
    }
    return AuthService._instance;
  }

  // ── Public API ─────────────────────────────────────────────────────────

  /** Returns the active session or null if not signed in. */
  public async getSession(): Promise<AgentVerseSession | null> {
    const accessToken = await this.context.secrets.get(SECRET_ACCESS_TOKEN);
    const refreshToken = await this.context.secrets.get(SECRET_REFRESH_TOKEN);
    const email = await this.context.secrets.get(SECRET_USER_EMAIL);
    const userId = await this.context.secrets.get(SECRET_USER_ID);
    const name = await this.context.secrets.get(SECRET_USER_NAME);
    const role = await this.context.secrets.get(SECRET_USER_ROLE);
    const orgName = await this.context.secrets.get(SECRET_USER_ORG);
    const orgTier = await this.context.secrets.get(SECRET_USER_TIER);
    const provider = await this.context.secrets.get(SECRET_PROVIDER);

    if (!accessToken || !email) {
      return null;
    }

    return {
      accessToken,
      refreshToken: refreshToken || '',
      email,
      userId: userId || email,
      name: name || email.split('@')[0],
      role: role || 'developer',
      orgName: orgName || 'Local Workspace',
      orgTier: orgTier || 'Free',
      provider: provider || 'AgentVerse',
    };
  }

  public async isAuthenticated(): Promise<boolean> {
    return (await this.getSession()) !== null;
  }

  /**
   * Log in with Email and Password.
   * Attempts connection to AgentGovernOS Auth API (/api/v1/auth/login),
   * falling back gracefully to local developer session if GovernOS is offline.
   */
  public async loginWithCredentials(
    email: string,
    password: string
  ): Promise<{ success: boolean; session?: AgentVerseSession; error?: string }> {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !password) {
      return { success: false, error: 'Email and password are required.' };
    }

    // 1. Attempt connection to GovernOS backend
    try {
      const response = await postJson(
        `${GOVERN_OS_URL}/api/v1/auth/login`,
        { email: cleanEmail, password },
        {},
        3500
      );

      if (response.ok && response.data && response.data.access_token) {
        const u = response.data.user || {};
        const session: AgentVerseSession = {
          userId: u.id || cleanEmail,
          email: u.email || cleanEmail,
          name: u.name || cleanEmail.split('@')[0],
          role: u.role || 'developer',
          orgName: u.org_name || 'Nuuvixx AI Systems',
          orgSlug: u.org_slug || 'nuuvixx-autonomous',
          orgTier: u.org_tier || 'Pro',
          accessToken: response.data.access_token,
          refreshToken: '',
          provider: 'AgentGovernOS',
        };

        await this._persistCustomSession(session);
        this._onDidAuthChange.fire(session);
        vscode.window.showInformationMessage(`AgentVerse: Signed in as ${session.name} (${session.email})`);
        return { success: true, session };
      } else if (response.status === 400 || response.status === 401 || response.status === 403) {
        // Explicit credential rejection from active GovernOS server
        const errDetail = response.data?.detail || 'Invalid email or password.';
        return { success: false, error: errDetail };
      }
    } catch {
      // Backend unreachable or offline — proceed to local authenticated session
    }

    // 2. Offline / Local Development Fallback:
    // Support standard demo credentials or any local developer email
    const isDemo = cleanEmail === 'developer@nuuvixx.ai' || cleanEmail === 'admin@nuuvixx.ai' || cleanEmail === 'owner@nuuvixx.ai';
    const demoRole = cleanEmail === 'owner@nuuvixx.ai' ? 'owner' : cleanEmail === 'admin@nuuvixx.ai' ? 'admin' : 'developer';
    const demoName = cleanEmail === 'owner@nuuvixx.ai' ? 'Platform Executive' : cleanEmail === 'admin@nuuvixx.ai' ? 'System Administrator' : 'Autonomous Developer';

    const localSession: AgentVerseSession = {
      userId: `local_${crypto.randomBytes(8).toString('hex')}`,
      email: cleanEmail,
      name: isDemo ? demoName : cleanEmail.split('@')[0],
      role: isDemo ? demoRole : 'developer',
      orgName: isDemo ? 'Nuuvixx AI Systems' : 'Local Workspace',
      orgTier: isDemo ? 'Enterprise' : 'Free',
      accessToken: `local_jwt_${Buffer.from(cleanEmail).toString('base64')}_${Date.now()}`,
      refreshToken: '',
      provider: isDemo ? 'AgentGovernOS (Demo)' : 'AgentVerse (Local)',
    };

    await this._persistCustomSession(localSession);
    this._onDidAuthChange.fire(localSession);
    vscode.window.showInformationMessage(`AgentVerse: Signed in as ${localSession.name} (${localSession.email})`);
    return { success: true, session: localSession };
  }

  /**
   * Register a new user with Email, Password, Name, and optional Org.
   */
  public async registerUser(
    name: string,
    email: string,
    password: string,
    orgName?: string
  ): Promise<{ success: boolean; session?: AgentVerseSession; error?: string }> {
    const cleanEmail = email.trim().toLowerCase();
    const cleanName = name.trim();

    if (!cleanEmail || !password || !cleanName) {
      return { success: false, error: 'Full name, email, and password are required.' };
    }

    if (password.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters.' };
    }

    // 1. Attempt connection to GovernOS backend
    try {
      const response = await postJson(
        `${GOVERN_OS_URL}/api/v1/auth/register`,
        { email: cleanEmail, password, name: cleanName, org_name: orgName || `${cleanName}'s Org` },
        {},
        3500
      );

      if (response.ok && response.data && response.data.access_token) {
        const u = response.data.user || {};
        const session: AgentVerseSession = {
          userId: u.id || cleanEmail,
          email: u.email || cleanEmail,
          name: u.name || cleanName,
          role: u.role || 'owner',
          orgName: u.org_name || orgName || `${cleanName}'s Org`,
          orgSlug: u.org_slug || 'default',
          orgTier: u.org_tier || 'Free',
          accessToken: response.data.access_token,
          refreshToken: '',
          provider: 'AgentGovernOS',
        };

        await this._persistCustomSession(session);
        this._onDidAuthChange.fire(session);
        vscode.window.showInformationMessage(`AgentVerse: Account created for ${session.name}!`);
        return { success: true, session };
      } else if (response.status === 409 || response.status === 400) {
        return { success: false, error: response.data?.detail || 'Account registration failed.' };
      }
    } catch {
      // Backend unreachable — create local workspace account
    }

    // 2. Offline / Local Workspace Account creation
    const localSession: AgentVerseSession = {
      userId: `local_${crypto.randomBytes(8).toString('hex')}`,
      email: cleanEmail,
      name: cleanName,
      role: 'owner',
      orgName: orgName?.trim() || `${cleanName}'s Workspace`,
      orgTier: 'Free',
      accessToken: `local_jwt_${Buffer.from(cleanEmail).toString('base64')}_${Date.now()}`,
      refreshToken: '',
      provider: 'AgentVerse (Local)',
    };

    await this._persistCustomSession(localSession);
    this._onDidAuthChange.fire(localSession);
    vscode.window.showInformationMessage(`AgentVerse: Welcome ${localSession.name}! Account active.`);
    return { success: true, session: localSession };
  }

  /**
   * One-click local developer session using system Git credentials or workspace context.
   */
  public async loginLocalDev(
    preferredName?: string,
    preferredEmail?: string
  ): Promise<AgentVerseSession> {
    let name = preferredName;
    let email = preferredEmail;

    if (!name || !email) {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      try {
        const [gitName, gitEmail] = await Promise.all([
          new Promise<string>((res) =>
            exec('git config user.name', { cwd: workspaceFolder }, (_, stdout) => res(stdout.trim()))
          ),
          new Promise<string>((res) =>
            exec('git config user.email', { cwd: workspaceFolder }, (_, stdout) => res(stdout.trim()))
          ),
        ]);
        if (!name && gitName) name = gitName;
        if (!email && gitEmail) email = gitEmail;
      } catch {
        // ignore git command errors
      }
    }

    const resolvedEmail = (email || 'developer@local.workspace').toLowerCase();
    const resolvedName = name || resolvedEmail.split('@')[0] || 'Local Developer';

    const session: AgentVerseSession = {
      userId: `dev_${crypto.randomBytes(6).toString('hex')}`,
      email: resolvedEmail,
      name: resolvedName,
      role: 'owner',
      orgName: 'Local Workspace',
      orgTier: 'Developer / BYOK',
      accessToken: `local_dev_token_${Date.now()}`,
      refreshToken: '',
      provider: 'Local Developer Identity',
    };

    await this._persistCustomSession(session);
    this._onDidAuthChange.fire(session);
    vscode.window.showInformationMessage(`AgentVerse: Signed in as ${session.name} (${session.email})`);
    return session;
  }

  /**
   * Starts the Supabase PKCE OAuth flow.
   * Opens the system browser; the callback is caught by the VS Code URI handler.
   */
  public async signIn(provider: 'google' | 'github' = 'google'): Promise<void> {
    this._pendingVerifier = generateCodeVerifier();
    const challenge = generateCodeChallenge(this._pendingVerifier);

    const params = new URLSearchParams({
      provider,
      redirect_to: REDIRECT_URI,
      code_challenge: challenge,
      code_challenge_method: 'S256',
    });

    const authUrl = `${SUPABASE_URL}/auth/v1/authorize?${params.toString()}`;

    // Register the URI handler to catch the callback
    this._uriHandler?.dispose();
    this._uriHandler = vscode.window.registerUriHandler({
      handleUri: (uri: vscode.Uri) => this._handleCallback(uri),
    });
    this.context.subscriptions.push(this._uriHandler);

    await vscode.env.openExternal(vscode.Uri.parse(authUrl));

    vscode.window.showInformationMessage(
      'AgentVerse: Browser opened for sign-in. Complete the flow to continue.',
    );
  }

  /** Signs the user out and clears all stored secrets. */
  public async signOut(): Promise<void> {
    const session = await this.getSession();
    if (session && session.provider === 'Supabase') {
      try {
        await postJson(
          `${SUPABASE_URL}/auth/v1/logout`,
          {},
          {
            Authorization: `Bearer ${session.accessToken}`,
            apikey: SUPABASE_ANON_KEY,
          }
        );
      } catch {
        /* silent */
      }
    }

    await this.context.secrets.delete(SECRET_ACCESS_TOKEN);
    await this.context.secrets.delete(SECRET_REFRESH_TOKEN);
    await this.context.secrets.delete(SECRET_USER_EMAIL);
    await this.context.secrets.delete(SECRET_USER_ID);
    await this.context.secrets.delete(SECRET_USER_NAME);
    await this.context.secrets.delete(SECRET_USER_ROLE);
    await this.context.secrets.delete(SECRET_USER_ORG);
    await this.context.secrets.delete(SECRET_USER_TIER);
    await this.context.secrets.delete(SECRET_PROVIDER);

    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = undefined;
    }

    this._onDidAuthChange.fire(null);
    vscode.window.showInformationMessage('AgentVerse: Signed out successfully.');
  }

  // ── OAuth Callback ─────────────────────────────────────────────────────

  private async _handleCallback(uri: vscode.Uri): Promise<void> {
    if (uri.path !== '/auth-callback') {
      return;
    }

    const params = new URLSearchParams(uri.query);
    const code = params.get('code');

    if (!code || !this._pendingVerifier) {
      vscode.window.showErrorMessage('AgentVerse: Auth callback missing code or verifier.');
      return;
    }

    const verifier = this._pendingVerifier;
    this._pendingVerifier = undefined;

    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: 'Completing sign-in…', cancellable: false },
      async () => {
        try {
          const res = await postJson(
            `${SUPABASE_URL}/auth/v1/token?grant_type=pkce`,
            {
              auth_code: code,
              code_verifier: verifier,
            },
            { apikey: SUPABASE_ANON_KEY }
          );

          if (!res.ok || !res.data?.access_token) {
            throw new Error(res.data?.error_description || 'No access_token in response');
          }

          const tokenResponse = res.data;
          await this._persistSession(tokenResponse);
          this._scheduleRefresh(tokenResponse.expires_in ?? 3600);

          const session = await this.getSession();
          this._onDidAuthChange.fire(session);

          vscode.window.showInformationMessage(
            `AgentVerse: Signed in as ${session?.email ?? 'user'}. Free models active.`
          );
        } catch (err: any) {
          vscode.window.showErrorMessage(`AgentVerse sign-in failed: ${err.message}`);
        }
      }
    );
  }

  // ── Token Persistence & Refresh ────────────────────────────────────────

  private async _persistSession(tokenResponse: any): Promise<void> {
    await this.context.secrets.store(SECRET_ACCESS_TOKEN, tokenResponse.access_token);
    if (tokenResponse.refresh_token) {
      await this.context.secrets.store(SECRET_REFRESH_TOKEN, tokenResponse.refresh_token);
    }
    const user = tokenResponse.user ?? {};
    await this.context.secrets.store(SECRET_USER_EMAIL, user.email ?? 'unknown');
    await this.context.secrets.store(SECRET_USER_ID, user.id ?? '');
    await this.context.secrets.store(
      SECRET_USER_NAME,
      user.user_metadata?.full_name || user.email?.split('@')[0] || 'User'
    );
    await this.context.secrets.store(SECRET_USER_ROLE, 'developer');
    await this.context.secrets.store(SECRET_USER_ORG, 'Supabase Cloud');
    await this.context.secrets.store(SECRET_USER_TIER, 'Free');
    await this.context.secrets.store(SECRET_PROVIDER, 'Supabase');
    await this._onAuthSuccess();
  }

  private async _persistCustomSession(session: AgentVerseSession): Promise<void> {
    await this.context.secrets.store(SECRET_ACCESS_TOKEN, session.accessToken);
    await this.context.secrets.store(SECRET_REFRESH_TOKEN, session.refreshToken || '');
    await this.context.secrets.store(SECRET_USER_EMAIL, session.email);
    await this.context.secrets.store(SECRET_USER_ID, session.userId);
    await this.context.secrets.store(SECRET_USER_NAME, session.name || session.email.split('@')[0]);
    await this.context.secrets.store(SECRET_USER_ROLE, session.role || 'developer');
    await this.context.secrets.store(SECRET_USER_ORG, session.orgName || 'Workspace');
    await this.context.secrets.store(SECRET_USER_TIER, session.orgTier || 'Free');
    await this.context.secrets.store(SECRET_PROVIDER, session.provider || 'AgentVerse');
    await this._onAuthSuccess();
  }

  private async _onAuthSuccess(): Promise<void> {
    try {
      await SettingsService.getInstance().ensureFreeModelsConfigured();
    } catch {
      // SettingsService may not be initialized in headless test context
    }
  }

  private _scheduleRefresh(expiresInSeconds: number): void {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
    }
    const ms = Math.max((expiresInSeconds - 60) * 1000, 30_000);
    this._refreshTimer = setInterval(() => this._refreshAccessToken(), ms);
  }

  private async _refreshAccessToken(): Promise<void> {
    const refreshToken = await this.context.secrets.get(SECRET_REFRESH_TOKEN);
    const provider = await this.context.secrets.get(SECRET_PROVIDER);
    if (!refreshToken || provider !== 'Supabase') {
      return;
    }

    try {
      const res = await postJson(
        `${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`,
        { refresh_token: refreshToken },
        { apikey: SUPABASE_ANON_KEY }
      );

      if (res.ok && res.data?.access_token) {
        await this._persistSession(res.data);
        this._scheduleRefresh(res.data.expires_in ?? 3600);
        const session = await this.getSession();
        this._onDidAuthChange.fire(session);
      }
    } catch {
      // Silent
    }
  }

  /** Call once on extension activate to restore session and schedule refresh if needed. */
  public async restoreSession(): Promise<void> {
    const session = await this.getSession();
    if (session) {
      if (session.provider === 'Supabase' && session.refreshToken) {
        await this._refreshAccessToken();
      }
      this._onDidAuthChange.fire(session);
      await this._onAuthSuccess();
    }
  }
}

