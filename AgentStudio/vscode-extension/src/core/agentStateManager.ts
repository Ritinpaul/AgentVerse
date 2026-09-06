/**
 * src/core/agentStateManager.ts
 *
 * Manages active Agent AST state, file synchronization, and CommandHistory (Undo/Redo)
 * within the Extension Host.
 */

let vscode: any;
try {
  vscode = require('vscode');
} catch (e) {
  // Standalone test environment without VS Code host
  vscode = null;
}

import {
  Agent,
  createDefaultAgent,
  YamlParser,
  YamlSerializer,
  ManifestHasher,
  CommandHistory,
  Command,
  ValidationError,
  Result,
} from '@agentstudio/agent-core';

export class AgentStateManager {
  private static _instance: AgentStateManager;
  private _currentAgent: Agent | null = null;
  private _currentFileUri: any | null = null;
  private _history: CommandHistory = new CommandHistory();

  public static get instance(): AgentStateManager {
    if (!this._instance) {
      this._instance = new AgentStateManager();
    }
    return this._instance;
  }

  public get currentAgent(): Agent | null {
    return this._currentAgent;
  }

  public get currentFileUri(): any | null {
    return this._currentFileUri;
  }

  public get history(): CommandHistory {
    return this._history;
  }

  /**
   * Load agent AST from a YAML file string or file URI.
   */
  public loadFromYaml(yamlContent: string, fileUri?: any): Result<Agent, ValidationError[]> {
    const parseResult = YamlParser.parse(yamlContent);
    if (parseResult.ok) {
      this._currentAgent = parseResult.value;
      if (fileUri) {
        this._currentFileUri = fileUri;
      }
      this._history.clear(); // Clear history when loading a new file
    }
    return parseResult;
  }

  /**
   * Create and set a default Agent object.
   */
  public createDefault(name: string): Agent {
    this._currentAgent = createDefaultAgent(name);
    this._currentFileUri = null;
    this._history.clear();
    return this._currentAgent;
  }

  /**
   * Apply a command mutation to the current Agent AST.
   */
  public applyCommand(command: Command): Agent | null {
    if (!this._currentAgent) {
      return null;
    }
    this._currentAgent = this._history.apply(command, this._currentAgent);
    return this._currentAgent;
  }

  /**
   * Undo last mutation command.
   */
  public undo(): Agent | null {
    if (!this._currentAgent) return null;
    const undone = this._history.undo(this._currentAgent);
    if (undone) {
      this._currentAgent = undone;
    }
    return this._currentAgent;
  }

  /**
   * Redo previously undone command.
   */
  public redo(): Agent | null {
    if (!this._currentAgent) return null;
    const redone = this._history.redo(this._currentAgent);
    if (redone) {
      this._currentAgent = redone;
    }
    return this._currentAgent;
  }

  /**
   * Serialize current Agent AST to canonical YAML text.
   */
  public toYaml(): string | null {
    if (!this._currentAgent) return null;
    return YamlSerializer.serialize(this._currentAgent);
  }

  /**
   * Compute deterministic sha256 hash of current Agent.
   */
  public computeHash(): string | null {
    if (!this._currentAgent) return null;
    return ManifestHasher.computeHash(this._currentAgent);
  }

  /**
   * Save current Agent AST back to disk if fileUri is known.
   */
  public async saveToFile(): Promise<boolean> {
    if (!this._currentAgent || !this._currentFileUri) return false;
    const yamlStr = this.toYaml();
    if (!yamlStr) return false;

    const encoder = new TextEncoder();
    await vscode.workspace.fs.writeFile(this._currentFileUri, encoder.encode(yamlStr));
    return true;
  }
}
