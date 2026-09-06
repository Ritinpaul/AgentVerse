import * as vscode from 'vscode';
import { AgentExplorerProvider } from '../providers/agentExplorer';

/**
 * Native-feeling file commands for the AgentVerse Explorer.
 * Mirrors the built-in EXPLORER actions (New File, New Folder, Open Folder).
 */
export function registerExplorerCommands(
  context: vscode.ExtensionContext,
  provider: AgentExplorerProvider
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('agentverse.explorerOpenFolder', async () => {
      const options: vscode.OpenDialogOptions = {
        canSelectFiles: false,
        canSelectFolders: true,
        canSelectMany: false,
        openLabel: 'Open Folder',
      };
      const folders = await vscode.window.showOpenDialog(options);
      if (folders && folders[0]) {
        await vscode.commands.executeCommand('vscode.openFolder', folders[0]);
      }
    }),

    vscode.commands.registerCommand('agentverse.newFile', async () => {
      const root = vscode.workspace.workspaceFolders?.[0]?.uri;
      if (!root) {
        vscode.window.showWarningMessage('Open a folder first (AgentVerse Explorer → Open Folder…).');
        return;
      }
      const name = await vscode.window.showInputBox({
        prompt: 'File name (relative to workspace root)',
        value: 'agent.yaml',
        validateInput: (v) => (v && v.trim().length > 0 ? null : 'Enter a file name'),
      });
      if (!name) return;

      const uri = vscode.Uri.joinPath(root, name.trim());
      const encoder = new TextEncoder();
      try {
        await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(root, name.trim().replace(/\/[^/]+$/, '')));
      } catch {
        // dir already exists — ignore
      }
      try {
        await vscode.workspace.fs.writeFile(uri, encoder.encode('# New AgentVerse agent file\n'));
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to create file: ${err.message ?? err}`);
        return;
      }
      await vscode.window.showTextDocument(uri);
      provider.refresh();
    }),

    vscode.commands.registerCommand('agentverse.newFolder', async () => {
      const root = vscode.workspace.workspaceFolders?.[0]?.uri;
      if (!root) {
        vscode.window.showWarningMessage('Open a folder first (AgentVerse Explorer → Open Folder…).');
        return;
      }
      const name = await vscode.window.showInputBox({
        prompt: 'Folder name (relative to workspace root)',
        validateInput: (v) => (v && v.trim().length > 0 ? null : 'Enter a folder name'),
      });
      if (!name) return;
      try {
        await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(root, name.trim()));
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to create folder: ${err.message ?? err}`);
        return;
      }
      provider.refresh();
    }),
  );
}