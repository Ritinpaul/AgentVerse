import * as vscode from 'vscode';

export function deployToCloud(context: vscode.ExtensionContext) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('AgentStudio: Please open a workspace folder first.');
        return;
    }

    const terminal = vscode.window.createTerminal('AgentStudio: Deploy');
    terminal.show();
    terminal.sendText('nuuvixx deploy');
}
