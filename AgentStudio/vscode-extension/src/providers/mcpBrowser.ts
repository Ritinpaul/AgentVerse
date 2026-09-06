import * as vscode from 'vscode';

export class MCPBrowserProvider implements vscode.TreeDataProvider<TreeItem> {
  getTreeItem(element: TreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: TreeItem): Thenable<TreeItem[]> {
    if (element) {
      if (element.label === 'AgentStore Registry') {
        return Promise.resolve([
          new TreeItem('nuuvixx/web-search', vscode.TreeItemCollapsibleState.None, 'A search tool using Tavily'),
          new TreeItem('nuuvixx/sql-query', vscode.TreeItemCollapsibleState.None, 'Query local databases'),
          new TreeItem('nuuvixx/github', vscode.TreeItemCollapsibleState.None, 'Manage issues and PRs')
        ]);
      }
      return Promise.resolve([]);
    } else {
      return Promise.resolve([
        new TreeItem('AgentStore Registry', vscode.TreeItemCollapsibleState.Expanded)
      ]);
    }
  }
}

class TreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly description?: string
  ) {
    super(label, collapsibleState);
    this.tooltip = this.description;
  }
}
