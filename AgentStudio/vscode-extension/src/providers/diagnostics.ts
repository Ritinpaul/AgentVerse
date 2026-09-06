/**
 * src/providers/diagnostics.ts
 *
 * Local Policy & Manifest Diagnostics Provider using @agentstudio/agent-core.
 * Emits Diagnostic markers directly into the VS Code editor for agent.yaml files.
 */

import * as vscode from 'vscode';
import { YamlParser, ValidationError } from '@agentstudio/agent-core';

export class PolicyDiagnosticsProvider {
  private collection: vscode.DiagnosticCollection;

  constructor(context: vscode.ExtensionContext) {
    this.collection = vscode.languages.createDiagnosticCollection('agentGovernOS');
    context.subscriptions.push(this.collection);

    // Update diagnostics on file change or open
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (event.document.languageId === 'yaml' && event.document.fileName.endsWith('agent.yaml')) {
        this.updateDiagnostics(event.document);
      }
    });

    vscode.workspace.onDidOpenTextDocument((document) => {
      if (document.languageId === 'yaml' && document.fileName.endsWith('agent.yaml')) {
        this.updateDiagnostics(document);
      }
    });

    // Run initially for visible editors
    vscode.window.visibleTextEditors.forEach((editor) => {
      if (editor.document.languageId === 'yaml' && editor.document.fileName.endsWith('agent.yaml')) {
        this.updateDiagnostics(editor.document);
      }
    });
  }

  private updateDiagnostics(document: vscode.TextDocument) {
    const text = document.getText();
    const parseResult = YamlParser.parse(text);

    if (parseResult.ok) {
      this.collection.set(document.uri, []);
      return;
    }

    const diagnostics: vscode.Diagnostic[] = [];

    for (const error of parseResult.errors) {
      // Line position fallback
      let range = new vscode.Range(0, 0, 0, 80);

      if (error.path) {
        // Try finding path key in document
        const lineIdx = document.getText().split('\n').findIndex((line) => line.includes(error.path || ''));
        if (lineIdx !== -1) {
          range = new vscode.Range(lineIdx, 0, lineIdx, document.lineAt(lineIdx).text.length);
        }
      }

      const severity =
        error.severity === 'error'
          ? vscode.DiagnosticSeverity.Error
          : vscode.DiagnosticSeverity.Warning;

      const diagnostic = new vscode.Diagnostic(range, `AgentStudio: ${error.message}`, severity);
      diagnostic.code = error.code;
      diagnostic.source = 'AgentStudio Local Advisor';

      diagnostics.push(diagnostic);
    }

    this.collection.set(document.uri, diagnostics);
  }
}
