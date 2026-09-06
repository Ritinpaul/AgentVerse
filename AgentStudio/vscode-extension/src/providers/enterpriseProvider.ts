import * as vscode from 'vscode';
import { SSOAuthService } from '../services/ssoAuth';

export class EnterpriseProvider {
    public static currentPanel: EnterpriseProvider | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _ssoAuthService: SSOAuthService;

    public static createOrShow(extensionUri: vscode.Uri, context: vscode.ExtensionContext) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it.
        if (EnterpriseProvider.currentPanel) {
            EnterpriseProvider.currentPanel._panel.reveal(column);
            // Tell the webview to switch to the enterprise tab
            EnterpriseProvider.currentPanel._panel.webview.postMessage({ type: 'SET_TAB', tab: 'enterprise' });
            return;
        }

        // Otherwise, create a new panel.
        const panel = vscode.window.createWebviewPanel(
            'agentStudioEnterprise',
            'AgentStudio: Team & Enterprise',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(extensionUri, 'dist'),
                    vscode.Uri.joinPath(extensionUri, 'webview', 'dist')
                ]
            }
        );

        EnterpriseProvider.currentPanel = new EnterpriseProvider(panel, extensionUri, context);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, context: vscode.ExtensionContext) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._ssoAuthService = new SSOAuthService(context);

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Tell the webview (which uses the shared App.tsx) to switch to the enterprise tab
        setTimeout(() => {
            this._panel.webview.postMessage({ type: 'SET_TAB', tab: 'enterprise' });
        }, 500);

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                const { EmbeddedCore } = await import('../core/embeddedCore');
                if (EmbeddedCore.instance) {
                    await EmbeddedCore.instance.handleWebviewMessage(message, this._panel.webview);
                }
            },
            null,
            this._disposables
        );
    }

    public dispose() {
        EnterpriseProvider.currentPanel = undefined;

        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}
