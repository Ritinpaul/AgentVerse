import * as vscode from 'vscode';
import { SettingsService } from '../services/settingsService';
import { YamlParser, ManifestHasher } from '@agentstudio/agent-core';
import { AgentStateManager } from '../core/agentStateManager';
import { EmbeddedCore } from '../core/embeddedCore';
import { AuthService } from '../services/authService';
import * as yaml from 'yaml';

// ── Shared HTML builder ────────────────────────────────────────────────────

function getNonce(): string {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

function getWebviewHtml(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  panelId: string,
  title: string,
): string {
  const scriptPathOnDisk = vscode.Uri.joinPath(extensionUri, 'out', 'webview.js');
  const scriptUri = webview.asWebviewUri(scriptPathOnDisk);
  const nonce = getNonce();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none';
             style-src ${webview.cspSource} 'unsafe-inline' https://fonts.googleapis.com;
             script-src 'nonce-${nonce}';
             connect-src ws://localhost:* http://localhost:* wss://localhost:*;
             font-src ${webview.cspSource} data: https://fonts.gstatic.com;
             img-src ${webview.cspSource} data: https:;">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    html, body, #root { min-height: 100%; margin: 0; padding: 0; overflow: auto; }
    body { background: #090A10; color: #E2E8F0; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}">window.__PANEL_ID__ = '${panelId}';</script>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}

// ── Agent Copilot Provider ─────────────────────────────────────────────────

export class AgentCopilotProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.copilot';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'copilot', 'AgentVerse Copilot'
    );

    // Forward messages from webview to extension host
    webviewView.webview.onDidReceiveMessage(msg => {
      if (msg.type === 'APPLY_DIFF') {
        vscode.commands.executeCommand('agentverse.applyDiff', msg.filename, msg.diff);
      }
      if (msg.type === 'OPEN_DIFF') {
        vscode.commands.executeCommand('agentverse.openDiff', msg.filename);
      }
      if (msg.type === 'RUN_AGENT') {
        vscode.commands.executeCommand('agentverse.runAgent', msg.agentId);
      }
      if (msg.type === 'OPEN_AGENT_CONFIG') {
        vscode.workspace.findFiles('**/agent*.yaml', '**/node_modules/**', 1).then((m) => {
          if (m[0]) vscode.window.showTextDocument(m[0]);
          else vscode.window.showWarningMessage('AgentVerse: no agent yaml found in the workspace.');
        });
      }
      if (msg.type === 'OPEN_POLICY') {
        vscode.workspace.findFiles('**/*policy*.yaml', '**/node_modules/**', 1).then((m) => {
          if (m[0]) vscode.window.showTextDocument(m[0]);
          else vscode.window.showWarningMessage('AgentVerse: no policy yaml found in the workspace.');
        });
      }
    });
  }

  /** Send a context update to the Copilot webview */
  public updateContext(ctx: {
    activeFile?: string;
    activeAgentConfig?: string;
    diagnostics?: string[];
  }) {
    this._view?.webview.postMessage({ type: 'UPDATE_CONTEXT', ...ctx });
  }

  public postMessage(msg: unknown) {
    this._view?.webview.postMessage(msg);
  }
}

// ── Agent Graph Provider ───────────────────────────────────────────────────

export class AgentGraphProvider {
  public static currentPanel: AgentGraphProvider | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Beside
      : vscode.ViewColumn.One;

    if (AgentGraphProvider.currentPanel) {
      AgentGraphProvider.currentPanel._panel.reveal(column);
      AgentGraphProvider.currentPanel.syncActiveEditor();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'agentverse.graph',
      'Agent Graph',
      column,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        retainContextWhenHidden: true,
      }
    );

    AgentGraphProvider.currentPanel = new AgentGraphProvider(panel, extensionUri);
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    panel.iconPath = new vscode.ThemeIcon('type-hierarchy');
    panel.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
    };
    panel.webview.html = getWebviewHtml(panel.webview, extensionUri, 'graph', 'Agent Graph');

    // Message listener for webview IPC
    panel.webview.onDidReceiveMessage(
      async (message) => {
        if (message.type === 'GET_AGENT_STATE') {
          await this.syncActiveEditor();
        } else if (message.type === 'AGENT_COMMAND' || message.type === 'UNDO_COMMAND' || message.type === 'REDO_COMMAND') {
          if (EmbeddedCore.instance) {
            await EmbeddedCore.instance.handleWebviewMessage(message, panel.webview);
            await AgentStateManager.instance.saveToFile();
          }
        }
      },
      null,
      this._disposables
    );

    // Sync graph when active text editor changes or document text changes
    vscode.window.onDidChangeActiveTextEditor(
      () => this.syncActiveEditor(),
      null,
      this._disposables
    );

    vscode.workspace.onDidChangeTextDocument(
      (e) => {
        const activeDoc = vscode.window.activeTextEditor?.document;
        if (activeDoc && e.document.uri.toString() === activeDoc.uri.toString()) {
          this.syncActiveEditor();
        }
      },
      null,
      this._disposables
    );

    // Initial sync call
    setTimeout(() => this.syncActiveEditor(), 100);

    panel.onDidDispose(() => this.dispose(), null, this._disposables);
  }

  public async syncActiveEditor(): Promise<void> {
    try {
      let docText: string | undefined;
      let fileUri: vscode.Uri | undefined;

      const activeEditor = vscode.window.activeTextEditor;
      if (activeEditor && (activeEditor.document.fileName.endsWith('.yaml') || activeEditor.document.fileName.endsWith('.yml'))) {
        docText = activeEditor.document.getText();
        fileUri = activeEditor.document.uri;
      } else {
        // Search workspace for agent.yaml
        const files = await vscode.workspace.findFiles('**/agent.yaml', undefined, 5);
        if (files.length > 0) {
          const playgroundFile = files.find(f => f.fsPath.includes('playground'));
          fileUri = playgroundFile || files[0];
          const content = await vscode.workspace.fs.readFile(fileUri);
          docText = new TextDecoder('utf-8').decode(content);
        }
      }

      if (docText) {
        let agent: any = undefined;
        const parseRes = YamlParser.parse(docText);

        if (parseRes.ok && parseRes.value) {
          agent = parseRes.value;
          AgentStateManager.instance.loadFromYaml(docText, fileUri);
        } else {
          // Resilient fallback: parse raw YAML object
          try {
            const raw = yaml.parse(docText);
            if (raw && typeof raw === 'object') {
              agent = {
                metadata: raw.metadata || { name: 'agent-manifest', version: '1.0.0' },
                model: raw.model || { provider: 'openai', name: 'gpt-4' },
                instructions: raw.instructions || '',
                workflow: raw.workflow || { nodes: [], edges: [] },
              };
            }
          } catch (e) {
            // Ignore syntax errors while typing
          }
        }

        if (agent) {
          const manifestHash = ManifestHasher.computeHash(agent);
          this._panel.webview.postMessage({
            type: 'AGENT_STATE',
            agent,
            yamlText: docText,
            manifestHash,
            canUndo: AgentStateManager.instance.history.canUndo(),
            canRedo: AgentStateManager.instance.history.canRedo(),
          });
        }
      }
    } catch (err) {
      console.error('AgentGraphProvider syncActiveEditor error:', err);
    }
  }

  public dispose() {
    AgentGraphProvider.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }
}

// ── Monitor Panel Provider ─────────────────────────────────────────────────

export class MonitorPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.monitor';
  public static currentInstance?: MonitorPanelProvider;
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {
    MonitorPanelProvider.currentInstance = this;
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'monitor', 'AgentVerse Monitor'
    );

    webviewView.webview.onDidReceiveMessage((msg) => {
      if (msg.type === 'GET_MONITOR_STATE') {
        webviewView.webview.postMessage({
          type: 'MONITOR_STATE_UPDATE',
          events: [],
          agents: [],
          status: 'idle',
        });
      }
    });
  }

  public broadcastEvent(event: any) {
    this._view?.webview.postMessage({
      type: 'SWARM_TELEMETRY_EVENT',
      event,
    });
  }
}

// ── Traces Panel Provider ──────────────────────────────────────────────────

export class TracesPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.traces';
  public static currentPanel: TracesPanelProvider | undefined;
  private readonly _panel?: vscode.WebviewPanel;
  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Active
      : vscode.ViewColumn.One;

    if (TracesPanelProvider.currentPanel && TracesPanelProvider.currentPanel._panel) {
      TracesPanelProvider.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'agentverse.tracesEditor',
      'GovernOS Traces & Audit',
      column,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        retainContextWhenHidden: true,
      }
    );

    TracesPanelProvider.currentPanel = new TracesPanelProvider(extensionUri, panel);
  }

  constructor(
    private readonly _extensionUri: vscode.Uri,
    panel?: vscode.WebviewPanel
  ) {
    if (panel) {
      this._panel = panel;
      panel.iconPath = new vscode.ThemeIcon('shield');
      panel.webview.options = {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
      };
      panel.webview.html = getWebviewHtml(
        panel.webview, this._extensionUri, 'traces', 'GovernOS Traces'
      );
      panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'traces', 'GovernOS Traces'
    );
  }

  public dispose() {
    TracesPanelProvider.currentPanel = undefined;
    if (this._panel) {
      this._panel.dispose();
    }
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }
}

// ── Inspector Panel Provider ───────────────────────────────────────────────

export class AgentInspectorProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.inspector';
  public static currentPanel: AgentInspectorProvider | undefined;
  private readonly _panel?: vscode.WebviewPanel;
  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Active
      : vscode.ViewColumn.One;

    if (AgentInspectorProvider.currentPanel && AgentInspectorProvider.currentPanel._panel) {
      AgentInspectorProvider.currentPanel._panel.reveal(column);
      AgentInspectorProvider.currentPanel.syncActiveEditor();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'agentverse.inspectorEditor',
      'Agent Inspector Workspace',
      column,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        retainContextWhenHidden: true,
      }
    );

    AgentInspectorProvider.currentPanel = new AgentInspectorProvider(extensionUri, panel);
  }

  constructor(
    private readonly _extensionUri: vscode.Uri,
    panel?: vscode.WebviewPanel
  ) {
    if (panel) {
      this._panel = panel;
      panel.iconPath = new vscode.ThemeIcon('circuit-board');
      panel.webview.options = {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
      };
      panel.webview.html = getWebviewHtml(
        panel.webview, this._extensionUri, 'inspector', 'Agent Inspector'
      );
      panel.webview.onDidReceiveMessage(
        msg => this._handleInspectorMessage(msg, panel.webview),
        null,
        this._disposables
      );
      panel.onDidDispose(() => this.dispose(), null, this._disposables);

      // Initial sync
      this.syncActiveEditor(panel.webview);
    }

    // Keep inspector in sync with open active text editor or workspace documents
    vscode.window.onDidChangeActiveTextEditor(() => this.syncActiveEditor(), null, this._disposables);
    vscode.workspace.onDidSaveTextDocument(doc => {
      if (doc.fileName.endsWith('.yaml') || doc.fileName.endsWith('.yml')) {
        this.syncActiveEditor();
      }
    }, null, this._disposables);
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'inspector', 'Agent Inspector'
    );

    webviewView.webview.onDidReceiveMessage(
      msg => this._handleInspectorMessage(msg, webviewView.webview),
      null,
      this._disposables
    );

    // Initial sync
    this.syncActiveEditor(webviewView.webview);
  }

  public async syncActiveEditor(targetWebview?: vscode.Webview) {
    const webview = targetWebview || this._view?.webview || this._panel?.webview;
    if (!webview) return;

    try {
      let docText: string | undefined;
      let fileUri: vscode.Uri | undefined;

      const activeEditor = vscode.window.activeTextEditor;
      if (activeEditor && (activeEditor.document.fileName.endsWith('.yaml') || activeEditor.document.fileName.endsWith('.yml'))) {
        docText = activeEditor.document.getText();
        fileUri = activeEditor.document.uri;
      } else {
        const files = await vscode.workspace.findFiles('**/agent*.yaml', '**/node_modules/**', 5);
        if (files.length > 0) {
          const mainFile = files.find(f => f.fsPath.endsWith('agent.yaml')) || files[0];
          fileUri = mainFile;
          const content = await vscode.workspace.fs.readFile(fileUri);
          docText = new TextDecoder('utf-8').decode(content);
        }
      }

      if (docText) {
        let agent: any = undefined;
        const parseRes = YamlParser.parse(docText);
        if (parseRes.ok && parseRes.value) {
          agent = parseRes.value;
          AgentStateManager.instance.loadFromYaml(docText, fileUri);
        } else {
          try {
            const raw = yaml.parse(docText);
            if (raw && typeof raw === 'object') {
              agent = {
                metadata: raw.metadata || { name: 'agent-manifest', version: '1.0.0' },
                model: raw.model || { provider: 'openai', name: 'gpt-4o' },
                instructions: raw.instructions || '',
                tools: raw.tools || [],
                budget: raw.budget || { maxCostPerRun: 0.25 },
                runtime: raw.runtime || { sandbox: 'docker' },
                policies: raw.policies || {},
              };
            }
          } catch {}
        }

        if (agent) {
          const manifestHash = ManifestHasher.computeHash(agent);
          webview.postMessage({
            type: 'AGENT_STATE',
            agent,
            yamlText: docText,
            manifestHash,
            filePath: fileUri ? vscode.workspace.asRelativePath(fileUri) : undefined,
            canUndo: AgentStateManager.instance.history.canUndo(),
            canRedo: AgentStateManager.instance.history.canRedo(),
          });
          return;
        }
      }

      webview.postMessage({ type: 'NO_AGENT' });
    } catch (e) {
      console.error('AgentInspectorProvider sync error:', e);
    }
  }

  private async _handleInspectorMessage(msg: any, webview: vscode.Webview) {
    if (msg.type === 'GET_WORKSPACE_AGENT') {
      await this.syncActiveEditor(webview);
    } else if (msg.type === 'CREATE_DEFAULT_AGENT') {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (workspaceFolder) {
        const agentUri = vscode.Uri.joinPath(workspaceFolder.uri, 'agent.yaml');
        const defaultYaml = `metadata:\n  name: my-workspace-agent\n  version: 0.1.0\n  description: "Autonomous Agent in AgentVerse IDE"\n\nmodel:\n  provider: freebuff\n  name: meta-llama/Llama-3.3-70B-Instruct\n  temperature: 0.7\n\ninstructions: |\n  You are a dedicated AI agent running in AgentVerse IDE.\n\ntools:\n  - id: web-search\n    type: mcp\n    server: mcp-search\n    tool: search\n    risk: low\n\nbudget:\n  maxCostPerRun: 0.10\n\nruntime:\n  sandbox: standard\n`;
        await vscode.workspace.fs.writeFile(agentUri, Buffer.from(defaultYaml, 'utf8'));
        const doc = await vscode.workspace.openTextDocument(agentUri);
        await vscode.window.showTextDocument(doc);
        await this.syncActiveEditor(webview);
        vscode.window.showInformationMessage('Created agent.yaml in workspace.');
      } else {
        vscode.window.showWarningMessage('Open a workspace folder to create an agent.yaml file.');
      }
    } else if (msg.type === 'AGENT_COMMAND') {
      try {
        AgentStateManager.instance.applyCommand(msg.command);
        const activeEditor = vscode.window.activeTextEditor;
        const newYaml = AgentStateManager.instance.toYaml();
        if (activeEditor && newYaml && (activeEditor.document.fileName.endsWith('.yaml') || activeEditor.document.fileName.endsWith('.yml'))) {
          const fullRange = new vscode.Range(
            activeEditor.document.positionAt(0),
            activeEditor.document.positionAt(activeEditor.document.getText().length)
          );
          await activeEditor.edit(editBuilder => {
            editBuilder.replace(fullRange, newYaml);
          });
        }
      } catch (err: any) {
        vscode.window.showErrorMessage(`Inspector command error: ${err.message || err}`);
      }
    } else if (msg.type === 'RUN_AGENT') {
      vscode.commands.executeCommand('agentverse.runAgent', msg.agentId);
    } else if (msg.type === 'SIGN_IN') {
      vscode.commands.executeCommand('agentverse.signIn');
    }
  }

  public dispose() {
    AgentInspectorProvider.currentPanel = undefined;
    if (this._panel) {
      this._panel.dispose();
    }
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }
}

// ── Sign In Panel Provider ──────────────────────────────────────────────────

export class SignInPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.signin';
  private _view?: vscode.WebviewView;
  private readonly _extensionUri: vscode.Uri;
  private _disposables: vscode.Disposable[] = [];

  constructor(private readonly _context: vscode.ExtensionContext) {
    this._extensionUri = _context.extensionUri;
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'signin', 'AgentVerse Account & Auth'
    );

    const auth = AuthService.getInstance(this._context);

    const pushSessionState = async () => {
      const session = await auth.getSession();
      webviewView.webview.postMessage({
        type: 'SESSION_STATE',
        session: session ? {
          userId: session.userId,
          email: session.email,
          name: session.name,
          role: session.role,
          orgName: session.orgName,
          orgTier: session.orgTier,
          provider: session.provider,
        } : null,
      });
    };

    // Push initial session state
    pushSessionState();

    // Listen for auth state changes across the extension
    const authSub = auth.onDidAuthChange(() => {
      pushSessionState();
    });
    this._disposables.push(authSub);

    webviewView.onDidDispose(() => {
      authSub.dispose();
    });

    webviewView.webview.onDidReceiveMessage(async (msg) => {
      switch (msg.type) {
        case 'GET_SESSION': {
          await pushSessionState();
          break;
        }

        case 'SIGN_IN_CREDENTIALS': {
          const res = await auth.loginWithCredentials(msg.email, msg.password);
          if (res.success && res.session) {
            webviewView.webview.postMessage({
              type: 'AUTH_SUCCESS',
              session: {
                userId: res.session.userId,
                email: res.session.email,
                name: res.session.name,
                role: res.session.role,
                orgName: res.session.orgName,
                orgTier: res.session.orgTier,
                provider: res.session.provider,
              },
            });
          } else {
            webviewView.webview.postMessage({
              type: 'AUTH_ERROR',
              error: res.error || 'Authentication failed. Check your credentials.',
            });
          }
          break;
        }

        case 'SIGN_UP_CREDENTIALS': {
          const res = await auth.registerUser(msg.name, msg.email, msg.password, msg.orgName);
          if (res.success && res.session) {
            webviewView.webview.postMessage({
              type: 'AUTH_SUCCESS',
              session: {
                userId: res.session.userId,
                email: res.session.email,
                name: res.session.name,
                role: res.session.role,
                orgName: res.session.orgName,
                orgTier: res.session.orgTier,
                provider: res.session.provider,
              },
            });
          } else {
            webviewView.webview.postMessage({
              type: 'AUTH_ERROR',
              error: res.error || 'Registration failed.',
            });
          }
          break;
        }

        case 'SIGN_IN_LOCAL_DEV': {
          const session = await auth.loginLocalDev(msg.name, msg.email);
          webviewView.webview.postMessage({
            type: 'AUTH_SUCCESS',
            session: {
              userId: session.userId,
              email: session.email,
              name: session.name,
              role: session.role,
              orgName: session.orgName,
              orgTier: session.orgTier,
              provider: session.provider,
            },
          });
          break;
        }

        case 'SIGN_IN_OAUTH': {
          await auth.signIn(msg.provider || 'google');
          break;
        }

        case 'SIGN_OUT': {
          await auth.signOut();
          webviewView.webview.postMessage({ type: 'SESSION_STATE', session: null });
          break;
        }

        case 'OPEN_SETTINGS': {
          vscode.commands.executeCommand('agentverse.openSettings');
          break;
        }

        // Backward compatibility
        case 'SIGN_IN':
        case 'CREATE_ACCOUNT': {
          await auth.signIn('google');
          break;
        }
      }
    });
  }
}

// ── Red-Team Security View Provider ──────────────────────────────────────────

export class RedTeamViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.redteamView';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'redteam', 'Red-Team Security Suite'
    );
  }
}

// ── Enterprise Governance View Provider ──────────────────────────────────────

export class EnterpriseViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.enterpriseView';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'enterprise', 'Enterprise Governance'
    );
  }
}

// ── AgentStore Marketplace View Provider & Editor Panel ───────────────────────

export class AgentStoreViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.storeView';
  public static currentPanel: AgentStoreViewProvider | undefined;
  private readonly _panel?: vscode.WebviewPanel;
  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Active
      : vscode.ViewColumn.One;

    if (AgentStoreViewProvider.currentPanel && AgentStoreViewProvider.currentPanel._panel) {
      AgentStoreViewProvider.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'agentverse.storeEditor',
      'AgentStore Marketplace',
      column,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        retainContextWhenHidden: true,
      }
    );

    AgentStoreViewProvider.currentPanel = new AgentStoreViewProvider(extensionUri, panel);
  }

  constructor(
    private readonly _extensionUri: vscode.Uri,
    panel?: vscode.WebviewPanel
  ) {
    if (panel) {
      this._panel = panel;
      panel.iconPath = new vscode.ThemeIcon('package');
      panel.webview.options = {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
      };
      panel.webview.html = getWebviewHtml(
        panel.webview, this._extensionUri, 'builder', 'AgentStore Marketplace'
      );
      panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'builder', 'AgentStore Marketplace'
    );
  }

  public dispose() {
    AgentStoreViewProvider.currentPanel = undefined;
    if (this._panel) {
      this._panel.dispose();
    }
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }
}

// ── Settings Panel Provider ──────────────────────────────────────────────────

export class SettingsPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'agentverse.settingsView';
  public static currentPanel: SettingsPanelProvider | undefined;
  private readonly _panel?: vscode.WebviewPanel;
  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.window.activeTextEditor
      ? vscode.ViewColumn.Active
      : vscode.ViewColumn.One;

    if (SettingsPanelProvider.currentPanel && SettingsPanelProvider.currentPanel._panel) {
      SettingsPanelProvider.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'agentverse.settingsEditor',
      'AgentVerse Settings',
      column,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        retainContextWhenHidden: true,
      }
    );

    SettingsPanelProvider.currentPanel = new SettingsPanelProvider(extensionUri, panel);
  }

  constructor(
    private readonly _extensionUri: vscode.Uri,
    panel?: vscode.WebviewPanel
  ) {
    if (panel) {
      this._panel = panel;
      panel.iconPath = new vscode.ThemeIcon('settings-gear');
      panel.webview.options = {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
      };
      panel.webview.html = getWebviewHtml(
        panel.webview, this._extensionUri, 'settings', 'AgentVerse Settings'
      );
      panel.webview.onDidReceiveMessage(
        (message) => this._handleMessage(message, panel.webview),
        null,
        this._disposables
      );
      panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'out')],
    };
    webviewView.webview.html = getWebviewHtml(
      webviewView.webview, this._extensionUri, 'settings', 'AgentVerse Settings'
    );
    webviewView.webview.onDidReceiveMessage(
      (message) => this._handleMessage(message, webviewView.webview),
      null,
      this._disposables
    );
  }

  private async _handleMessage(message: any, webview: vscode.Webview): Promise<void> {
    try {
      const service = SettingsService.getInstance();

      switch (message.type) {
        case 'GET_SETTINGS_STATE': {
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'SAVE_API_KEY': {
          await service.saveApiKey(message.providerId, message.apiKey);
          const testRes = await service.testProvider(message.providerId);
          const state = await service.getSettingsState();
          webview.postMessage({
            type: 'SAVE_API_KEY_RESPONSE',
            providerId: message.providerId,
            testRes,
            state,
          });
          break;
        }
        case 'TEST_PROVIDER':
        case 'REFRESH_LOCAL': {
          const testRes = await service.testProvider(message.providerId, message.baseUrl);
          const state = await service.getSettingsState();
          webview.postMessage({
            type: 'TEST_PROVIDER_RESPONSE',
            providerId: message.providerId,
            testRes,
            state,
          });
          break;
        }
        case 'TOGGLE_MODEL': {
          await service.toggleModel(message.modelId, message.enabled);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'SET_DEFAULT_MODEL': {
          await service.setDefaultModel(message.modelId);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'TOGGLE_AUTO_DETECT_LOCAL': {
          await service.setAutoDetectLocal(message.enabled);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'SET_GUARDRAIL_PROFILE': {
          await service.setGuardrailProfile(message.profile);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'SAVE_MCP_SERVER': {
          await service.saveMcpServer(message.server);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'DELETE_MCP_SERVER': {
          await service.deleteMcpServer(message.serverId);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
        case 'TOGGLE_MCP_SERVER': {
          await service.toggleMcpServer(message.serverId, message.enabled);
          const state = await service.getSettingsState();
          webview.postMessage({ type: 'SETTINGS_STATE_RESPONSE', state });
          break;
        }
      }
    } catch (err: any) {
      vscode.window.showErrorMessage(`Settings operation failed: ${err.message || err}`);
    }
  }

  public dispose() {
    SettingsPanelProvider.currentPanel = undefined;
    if (this._panel) {
      this._panel.dispose();
    }
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }
}



