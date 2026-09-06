import * as vscode from 'vscode';
import * as path from 'path';

// ── Run Agent Command ──────────────────────────────────────────────────────

export async function runAgent(
  context: vscode.ExtensionContext,
  agentId?: string,
): Promise<void> {

  // Determine agent ID from active file if not provided
  if (!agentId) {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      const fname = path.basename(editor.document.fileName);
      if (fname.endsWith('.yaml') || fname.endsWith('.yml')) {
        agentId = fname.replace(/\.(yaml|yml)$/, '');
      }
    }
  }

  if (!agentId) {
    vscode.window.showErrorMessage('AgentVerse: No agent selected. Open an agent.yaml file first.');
    return;
  }

  // Get or create terminal
  const terminalName = `AgentVerse: ${agentId}`;
  let terminal = vscode.window.terminals.find(t => t.name === terminalName);
  if (!terminal) {
    terminal = vscode.window.createTerminal({
      name: terminalName,
      env: { AGENTVERSE_API_URL: 'http://localhost:8013' },
    });
  }

  terminal.show(false); // false = don't steal focus from editor
  terminal.sendText(`agent run ${agentId}`);

  // Also show a notification
  vscode.window.setStatusBarMessage(`$(loading~spin) Running ${agentId}...`, 5000);
}

// ── Show Agent Graph Command ───────────────────────────────────────────────

export async function showAgentGraph(context: vscode.ExtensionContext): Promise<void> {
  const { AgentGraphProvider } = await import('../providers/agentCopilot');
  AgentGraphProvider.createOrShow(context.extensionUri);
}

// ── Sign In Command ────────────────────────────────────────────────────────

export async function signIn(context?: vscode.ExtensionContext): Promise<void> {
  // Bring the AgentVerse Account view to the foreground so the in-IDE
  // Sign In / Create Account experience is immediately visible.
  try {
    await vscode.commands.executeCommand('agentverse.signin.focus');
  } catch {
    // view focus command unavailable
  }

  const { AuthService } = await import('../services/authService');
  const auth = AuthService.getInstance(context);
  const isAuthed = await auth.isAuthenticated();

  if (isAuthed) {
    const session = await auth.getSession();
    const choice = await vscode.window.showInformationMessage(
      `Currently signed in as ${session?.name || session?.email} (${session?.role || 'developer'}).`,
      'Open Account Panel',
      'Sign Out'
    );
    if (choice === 'Sign Out') {
      await auth.signOut();
    } else if (choice === 'Open Account Panel') {
      await vscode.commands.executeCommand('agentverse.signin.focus');
    }
    return;
  }

  const choice = await vscode.window.showInformationMessage(
    'Sign in to AgentVerse to run agents and access free models.',
    { modal: false },
    'Open Account Panel',
    '1-Click Local Dev Login',
  );

  if (choice === 'Open Account Panel') {
    await vscode.commands.executeCommand('agentverse.signin.focus');
  } else if (choice === '1-Click Local Dev Login') {
    await auth.loginLocalDev();
  }
}

export async function signOut(context: vscode.ExtensionContext): Promise<void> {
  const { AuthService } = await import('../services/authService');
  const auth = AuthService.getInstance(context);
  await auth.signOut();
}

