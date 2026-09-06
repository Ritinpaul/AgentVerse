import * as vscode from 'vscode';

/**
 * Status Bar button for 1-click access to AgentVerse Settings.
 */
export class SettingsStatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor(context: vscode.ExtensionContext) {
    this.item = vscode.window.createStatusBarItem(
      'agentverse.settingsStatus',
      vscode.StatusBarAlignment.Right,
      200 // Higher priority to stay prominently visible
    );
    this.item.text = '$(gear) AgentVerse Settings';
    this.item.tooltip = 'Open AgentVerse IDE Settings (Models, Local Runtimes, MCP, Governance)';
    this.item.command = 'agentverse.openSettings';
    context.subscriptions.push(this.item);
    this.item.show();
  }
}
