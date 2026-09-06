import * as vscode from 'vscode';
import { AuthService, AgentVerseSession } from '../services/authService';

/**
 * Status bar entry that surfaces the AgentVerse sign-in state.
 * Reacts to AuthService.onDidAuthChange — no polling required.
 */
export class SignInStatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor(context: vscode.ExtensionContext) {
    this.item = vscode.window.createStatusBarItem(
      'agentverse.auth',
      vscode.StatusBarAlignment.Right,
      100,
    );
    context.subscriptions.push(this.item);

    const auth = AuthService.getInstance(context);

    // Subscribe to auth state changes (sign-in / sign-out)
    context.subscriptions.push(
      auth.onDidAuthChange((session) => this._render(session)),
    );

    // Render initial state (async — fires quickly from SecretStorage)
    auth.getSession().then((session) => this._render(session));
  }

  private _render(session: AgentVerseSession | null): void {
    if (session) {
      this.item.text = `$(verified) ${session.email}`;
      this.item.tooltip = `Signed in to AgentVerse as ${session.email}\nClick to sign out`;
      this.item.command = 'agentverse.signOut';
      this.item.backgroundColor = undefined;
    } else {
      this.item.text = '$(account) Sign in to AgentVerse';
      this.item.tooltip = 'Sign in to use free AI models or add your own API key';
      this.item.command = 'agentverse.signIn';
      this.item.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }
    this.item.show();
  }
}