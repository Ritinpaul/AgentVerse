import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// ── Directories we never surface in the AgentVerse Explorer ──────────────────
const IGNORED_DIRS = new Set([
  '.git',
  '.hg',
  '.svn',
  'node_modules',
  'out',
  'dist',
  'build',
  '.next',
  '.vercel',
  'target',
  '.venv',
  'venv',
  '__pycache__',
  '.pytest_cache',
  '.vscode',
  '.idea',
  '.agentverse',
  'coverage',
]);

/**
 * AgentVerse Explorer — a real, native-feeling file explorer for the open
 * workspace. It mirrors what is on disk (like the built-in EXPLORER), so the
 * tree is never mock data: folders are collapsible, files open on click, and
 * an "Open Folder…" action item is shown when no workspace is open.
 */
export class AgentExplorerItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly kind: 'folder' | 'file' | 'open' | 'message',
    public readonly resourceUri?: vscode.Uri,
  ) {
    super(label, collapsibleState);
    this.contextValue = kind;

    if (kind === 'open') {
      this.command = {
        command: 'agentverse.explorerOpenFolder',
        title: 'Open Folder…',
      };
    } else if (kind !== 'folder' && resourceUri) {
      this.command = {
        command: 'vscode.open',
        title: 'Open File',
        arguments: [resourceUri],
      };
    }

    if (resourceUri) {
      this.tooltip = resourceUri.fsPath;
    }

    this.iconPath = this._getIcon();
  }

  private _getIcon(): vscode.ThemeIcon {
    const n = this.label.toLowerCase();
    switch (this.kind) {
      case 'folder':
        return vscode.ThemeIcon.Folder;
      case 'open':
        return new vscode.ThemeIcon('folder-opened');
      case 'file':
        if (/\.(ya?ml)$/.test(n)) return new vscode.ThemeIcon('file-code');
        if (/\.(py)$/.test(n)) return new vscode.ThemeIcon('file-code');
        if (/\.(ts|tsx|js)$/.test(n)) return new vscode.ThemeIcon('file-code');
        if (/\.(json)$/.test(n)) return new vscode.ThemeIcon('json');
        if (/\.(md)$/.test(n)) return new vscode.ThemeIcon('markdown');
        if (/\.(sh|bash)$/.test(n)) return new vscode.ThemeIcon('terminal');
        if (n.startsWith('.env')) return new vscode.ThemeIcon('gear');
        return vscode.ThemeIcon.File;
      default:
        return vscode.ThemeIcon.File;
    }
  }
}

export class AgentExplorerProvider implements vscode.TreeDataProvider<AgentExplorerItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<AgentExplorerItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private readonly watcher: vscode.FileSystemWatcher | undefined;

  constructor() {
    const root = this.rootPath;
    if (root) {
      this.watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(root, '**/*')
      );
      this.watcher.onDidChange(() => this.refresh());
      this.watcher.onDidCreate(() => this.refresh());
      this.watcher.onDidDelete(() => this.refresh());
      vscode.workspace.onDidChangeWorkspaceFolders(() => this.refresh());
    }
  }

  private get rootPath(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: AgentExplorerItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: AgentExplorerItem): Promise<AgentExplorerItem[]> {
    if (!element) {
      const root = this.rootPath;
      if (!root) {
        return [
          new AgentExplorerItem('Open Folder…', vscode.TreeItemCollapsibleState.None, 'open'),
          new AgentExplorerItem(
            'No workspace open — open a folder to edit agents.',
            vscode.TreeItemCollapsibleState.None,
            'message'
          ),
        ];
      }
      return this._scan(root);
    }

    if (element.kind === 'folder' && element.resourceUri) {
      return this._scan(element.resourceUri.fsPath);
    }

    return [];
  }

  private _scan(dirPath: string): AgentExplorerItem[] {
    if (!fs.existsSync(dirPath)) return [];

    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(dirPath, { withFileTypes: true });
    } catch {
      return [];
    }

    return entries
      .filter((e) => !this._isIgnored(e))
      .sort((a, b) => {
        if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
        return a.name.localeCompare(b.name);
      })
      .map((e) => {
        const full = path.join(dirPath, e.name);
        if (e.isDirectory()) {
          const hasChildren = this._hasVisibleChildren(full);
          return new AgentExplorerItem(
            e.name,
            hasChildren ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None,
            'folder',
            vscode.Uri.file(full)
          );
        }
        return new AgentExplorerItem(e.name, vscode.TreeItemCollapsibleState.None, 'file', vscode.Uri.file(full));
      });
  }

  private _isIgnored(e: fs.Dirent): boolean {
    if (e.isDirectory() && IGNORED_DIRS.has(e.name)) return true;
    if (e.name === '.DS_Store') return true;
    if (e.isDirectory() && e.name.startsWith('.')) return true;
    return false;
  }

  private _hasVisibleChildren(dirPath: string): boolean {
    try {
      return fs
        .readdirSync(dirPath, { withFileTypes: true })
        .some((e) => !this._isIgnored(e));
    } catch {
      return false;
    }
  }

  dispose() {
    this.watcher?.dispose();
  }
}