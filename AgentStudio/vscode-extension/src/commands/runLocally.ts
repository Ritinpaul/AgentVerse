import * as vscode from 'vscode';

export function runLocally(context: vscode.ExtensionContext) {
    // Check if we are in a workspace
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('AgentStudio: Please open a workspace folder first.');
        return;
    }

    // Check if agent.yaml exists
    const agentYamlPath = vscode.Uri.joinPath(workspaceFolders[0].uri, 'agent.yaml');
    vscode.workspace.fs.stat(agentYamlPath).then(() => {
        // Spawn integrated terminal and run `nuuvixx run`
        const terminal = vscode.window.createTerminal('AgentStudio: Local Run');
        terminal.show();
        terminal.sendText('nuuvixx run');
    }, () => {
        vscode.window.showErrorMessage('AgentStudio: agent.yaml not found in the workspace root.');
    });
}
