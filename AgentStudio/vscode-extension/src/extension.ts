import * as vscode from 'vscode';
import { AgentExplorerProvider } from './providers/agentExplorer';
import {
  AgentInspectorProvider,
  MonitorPanelProvider,
  SignInPanelProvider,
  TracesPanelProvider,
  RedTeamViewProvider,
  EnterpriseViewProvider,
  AgentStoreViewProvider,
  SettingsPanelProvider,
} from './providers/agentCopilot';
import { PolicyDiagnosticsProvider } from './providers/diagnostics';
import { BudgetStatusBar } from './providers/budgetStatusBar';
import { SignInStatusBar } from './providers/signInStatusBar';
import { SettingsStatusBar } from './providers/settingsStatusBar';
import { RedTeamProvider } from './providers/redTeamProvider';
import { RemoteDebugProvider } from './providers/remoteDebugProvider';
import { EnterpriseProvider } from './providers/enterpriseProvider';
import { VisualizerPanelProvider } from './providers/visualizer';
import { EmbeddedCore } from './core/embeddedCore';
import { SSOAuthService } from './services/ssoAuth';
import { AuthService } from './services/authService';
import { runAgent, showAgentGraph, signIn, signOut } from './commands/runAgent';
import { registerExplorerCommands } from './commands/explorerCommands';
import { publishToStore } from './commands/publishToStore';
import { deployToCloud } from './commands/deployToCloud';
import { SettingsService } from './services/settingsService';
import { ModelRouter } from './services/modelRouter';

export function activate(context: vscode.ExtensionContext) {
  console.log('AgentVerse IDE extension is now active!');

  // ── Initialize core services ─────────────────────────────────────────────
  const settings = SettingsService.getInstance(context);
  const auth = AuthService.getInstance(context);
  ModelRouter.getInstance(context);
  const embeddedCore = new EmbeddedCore(context);

  // Auto-configure free models immediately on startup if not initialized
  settings.ensureFreeModelsConfigured().catch(() => {});

  // Restore persisted session (validates + refreshes token silently)
  auth.restoreSession().catch(() => { /* silent — user will be prompted to sign in */ });


  // ── Agent Explorer (native workspace tree) ───────────────────────────────
  const agentExplorerProvider = new AgentExplorerProvider();
  vscode.window.registerTreeDataProvider('agentverse.explorer', agentExplorerProvider);
  registerExplorerCommands(context, agentExplorerProvider);

  // ── Webview View Providers (sidebar panels) ───────────────────────────────

  const inspectorProvider = new AgentInspectorProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(AgentInspectorProvider.viewType, inspectorProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const monitorProvider = new MonitorPanelProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(MonitorPanelProvider.viewType, monitorProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const signInPanelProvider = new SignInPanelProvider(context);
  vscode.window.registerWebviewViewProvider(SignInPanelProvider.viewType, signInPanelProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const tracesProvider = new TracesPanelProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(TracesPanelProvider.viewType, tracesProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const redTeamViewProvider = new RedTeamViewProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(RedTeamViewProvider.viewType, redTeamViewProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const enterpriseViewProvider = new EnterpriseViewProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(EnterpriseViewProvider.viewType, enterpriseViewProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const storeViewProvider = new AgentStoreViewProvider(context.extensionUri);
  vscode.window.registerWebviewViewProvider(AgentStoreViewProvider.viewType, storeViewProvider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  // ── Phase 2 Diagnostics / Budget Bar ────────────────────────────────────
  new PolicyDiagnosticsProvider(context);
  new BudgetStatusBar(context);

  // ── Sign-in status (status bar + first-run focus on the Account view) ────
  const signInStatusBar = new SignInStatusBar(context);
  new SettingsStatusBar(context);

  // Show sign-in panel on first launch for unauthenticated users
  auth.isAuthenticated().then((authed) => {
    if (!authed) {
      setTimeout(() => {
        Promise.resolve(vscode.commands.executeCommand('agentverse.signin.focus')).catch(() => {
          // view focus not available — status bar entry is the fallback
        });
      }, 600);
    }
  });


  // ── Commands ─────────────────────────────────────────────────────────────

  const commands: vscode.Disposable[] = [

    // Run Agent — main CTA (Ctrl+Shift+R)
    vscode.commands.registerCommand('agentverse.runAgent', (agentId?: string) =>
      runAgent(context, agentId)
    ),

    // Show Agent Graph editor panel
    vscode.commands.registerCommand('agentverse.showGraph', () =>
      showAgentGraph(context)
    ),

    // Sign In / Sign Up
    vscode.commands.registerCommand('agentverse.signIn', () =>
      signIn(context)
    ),
    vscode.commands.registerCommand('agentverse.signOut', () =>
      signOut(context)
    ),

    // Refresh Explorer
    vscode.commands.registerCommand('agentverse.refreshExplorer', () =>
      agentExplorerProvider.refresh()
    ),

    // Deploy
    vscode.commands.registerCommand('agentverse.deploy', () =>
      deployToCloud(context)
    ),

    // Publish to Store
    vscode.commands.registerCommand('agentverse.publishToStore', () =>
      publishToStore(context)
    ),

    // Diff helpers used by the Copilot webview
    vscode.commands.registerCommand('agentverse.applyDiff', (filename?: string, diff?: string) => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || typeof diff !== 'string') {
        vscode.window.showWarningMessage('AgentVerse: No editor focused to apply diff.');
        return;
      }
      editor.edit((editBuilder) => {
        const pos = editor.selection.active;
        editBuilder.insert(pos, `\n${diff}\n`);
      });
      vscode.window.showInformationMessage(`Applied proposed change${filename ? ' to ' + filename : ''}.`);
    }),
    vscode.commands.registerCommand('agentverse.openDiff', (filename?: string) => {
      if (!filename) return;
      vscode.workspace.findFiles(`**/${filename}`, '**/node_modules/**', 1).then((matches) => {
        if (matches[0]) vscode.window.showTextDocument(matches[0]);
      });
    }),

    // Red-Team Suite
    vscode.commands.registerCommand('agentverse.runRedTeamSuite', () =>
      RedTeamProvider.createOrShow(context.extensionUri)
    ),

    // Remote Debug
    vscode.commands.registerCommand('agentverse.remoteDebug', () =>
      RemoteDebugProvider.createOrShow(context.extensionUri)
    ),

    // Enterprise Dashboard
    vscode.commands.registerCommand('agentverse.enterpriseDashboard', () =>
      EnterpriseProvider.createOrShow(context.extensionUri, context)
    ),

    // Swarm Visualizer (legacy, routed through AgentGraph)
    vscode.commands.registerCommand('agentverse.showVisualizer', () =>
      VisualizerPanelProvider.createOrShow(context.extensionUri)
    ),

    // Dual Workspace Mode Commands (Open full Main Editor Workspace tabs)
    vscode.commands.registerCommand('agentverse.openStoreEditor', () =>
      AgentStoreViewProvider.createOrShow(context.extensionUri)
    ),
    vscode.commands.registerCommand('agentverse.openGovernEditor', () =>
      TracesPanelProvider.createOrShow(context.extensionUri)
    ),
    vscode.commands.registerCommand('agentverse.openInspectorEditor', () =>
      AgentInspectorProvider.createOrShow(context.extensionUri)
    ),
    vscode.commands.registerCommand('agentverse.openSettings', () =>
      SettingsPanelProvider.createOrShow(context.extensionUri)
    ),
  ];

  context.subscriptions.push(...commands);
}

export function deactivate() {}
