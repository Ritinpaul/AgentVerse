import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import { URL } from 'url';
import { AuthService } from '../services/authService';

const DAILY_LIMIT = 50_000;
const POLL_INTERVAL_MS = 60_000; // refresh every 60 s when idle

/**
 * Status bar item showing the user's remaining free-tier token budget for today.
 *
 * - Green  → > 50% remaining
 * - Yellow → 10–50% remaining
 * - Red    → < 10% remaining (or exceeded)
 * - Pulsing animation fires whenever a stream is active.
 */
export class BudgetStatusBar {
  private readonly item: vscode.StatusBarItem;
  private _pollTimer: NodeJS.Timeout | undefined;
  private _streaming = false;
  private _pulseTimer: NodeJS.Timeout | undefined;

  constructor(private readonly context: vscode.ExtensionContext) {
    this.item = vscode.window.createStatusBarItem(
      'agentverse.budget',
      vscode.StatusBarAlignment.Right,
      99, // just left of the auth item
    );
    this.item.command = 'agentverse.openSettings';
    this.item.tooltip = 'Daily free AI token budget — click to open Settings';
    context.subscriptions.push(this.item);

    // Subscribe to auth changes — show/hide based on sign-in state
    const auth = AuthService.getInstance(context);
    context.subscriptions.push(
      auth.onDidAuthChange((session) => {
        if (session) {
          this._startPolling();
        } else {
          this._stopPolling();
          this.item.hide();
        }
      }),
    );

    // Initial render
    auth.isAuthenticated().then((authed) => {
      if (authed) { this._startPolling(); }
    });
  }

  /** Call this when a streaming response begins. */
  public setStreaming(active: boolean): void {
    this._streaming = active;
    if (active) {
      this._startPulse();
    } else {
      this._stopPulse();
      this._fetchAndRender(); // refresh after stream ends
    }
  }

  /** Call after FreeBuff emits a budget_update event (real-time from stream). */
  public updateFromEvent(used: number, remaining: number): void {
    this._render(used, remaining);
  }

  // ── Private ──────────────────────────────────────────────────────────────

  private _startPolling(): void {
    this._fetchAndRender();
    this._stopPolling(); // clear any existing timer
    this._pollTimer = setInterval(() => this._fetchAndRender(), POLL_INTERVAL_MS);
  }

  private _stopPolling(): void {
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = undefined;
    }
  }

  private _startPulse(): void {
    let flip = false;
    this._stopPulse();
    this._pulseTimer = setInterval(() => {
      this.item.text = flip
        ? this.item.text.replace('$(loading~spin) ', '').replace(/^🔮/, '🔮')
        : `$(loading~spin) ${this.item.text.replace('$(loading~spin) ', '')}`;
      flip = !flip;
    }, 800);
  }

  private _stopPulse(): void {
    if (this._pulseTimer) {
      clearInterval(this._pulseTimer);
      this._pulseTimer = undefined;
    }
    // Strip the spinner prefix if present
    this.item.text = this.item.text.replace('$(loading~spin) ', '');
  }

  private async _fetchAndRender(): Promise<void> {
    const auth = AuthService.getInstance(this.context);
    const session = await auth.getSession();
    if (!session) {
      this.item.hide();
      return;
    }

    const governosBase = vscode.workspace
      .getConfiguration('agentverse')
      .get<string>('governosUrl', 'http://localhost:8003');

    try {
      const data = await this._httpGet(
        `${governosBase}/api/v1/freebuff/budget`,
        { Authorization: `Bearer ${session.accessToken}` },
      );
      const budget = data?.budget;
      if (budget) {
        this._render(budget.used ?? 0, budget.remaining ?? DAILY_LIMIT);
      }
    } catch {
      // GovernOS offline — show a neutral indicator without erroring
      this.item.text = '🔮 — / 50k';
      this.item.backgroundColor = undefined;
      this.item.show();
    }
  }

  private _render(used: number, remaining: number): void {
    const pct = (remaining / DAILY_LIMIT) * 100;
    const usedK = Math.round(used / 100) / 10;    // e.g. 12345 → 12.3
    const remK  = Math.round(remaining / 100) / 10;

    this.item.text = `🔮 ${remK}k / 50k`;

    if (pct > 50) {
      this.item.backgroundColor = undefined; // default (green-ish)
      this.item.tooltip = `${usedK}k tokens used today — ${remK}k remaining (resets midnight UTC)`;
    } else if (pct > 10) {
      this.item.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
      this.item.tooltip = `⚠ ${usedK}k / 50k tokens used — consider adding a BYOK key`;
    } else {
      this.item.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
      this.item.tooltip = `🚨 Almost out of free tokens! ${remK}k remaining. Add a BYOK API key to continue.`;
    }

    this.item.show();
  }

  private _httpGet(url: string, headers: Record<string, string>): Promise<any> {
    return new Promise((resolve, reject) => {
      const parsed = new URL(url);
      const client = parsed.protocol === 'https:' ? https : http;

      client.get(
        {
          hostname: parsed.hostname,
          port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
          path: parsed.pathname + parsed.search,
          headers,
          timeout: 4000,
        },
        (res) => {
          let body = '';
          res.on('data', (c: Buffer) => (body += c.toString()));
          res.on('end', () => {
            try { resolve(JSON.parse(body)); } catch { resolve(null); }
          });
        },
      ).on('error', reject).on('timeout', () => reject(new Error('timeout')));
    });
  }
}
