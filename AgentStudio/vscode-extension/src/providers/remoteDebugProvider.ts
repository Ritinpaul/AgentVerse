import * as vscode from 'vscode';

export class RemoteDebugProvider {
    public static currentPanel: RemoteDebugProvider | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (RemoteDebugProvider.currentPanel) {
            RemoteDebugProvider.currentPanel._panel.reveal(column);
            RemoteDebugProvider.currentPanel._panel.webview.postMessage({ type: 'SET_TAB', tab: 'remotedebug' });
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'agentStudioRemoteDebug',
            'AgentStudio: Remote Production Debugger',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')]
            }
        );

        RemoteDebugProvider.currentPanel = new RemoteDebugProvider(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._update();
        this._panel.webview.postMessage({ type: 'SET_TAB', tab: 'remotedebug' });
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

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
        RemoteDebugProvider.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        const scriptPathOnDisk = vscode.Uri.joinPath(this._extensionUri, 'out', 'webview.js');
        const scriptUri = webview.asWebviewUri(scriptPathOnDisk);
        const nonce = getNonce();

        return `<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src ws://localhost:* http://localhost:*; font-src ${webview.cspSource};">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AgentStudio: Remote Production Debugger</title>
            </head>
            <body>
                <div id="root"></div>
                <script nonce="${nonce}" src="${scriptUri}"></script>
            </body>
            </html>`;
    }
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
