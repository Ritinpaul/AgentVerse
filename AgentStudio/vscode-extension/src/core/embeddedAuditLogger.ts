import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface AuditLogEntry {
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    details: string;
}

export class EmbeddedAuditLogger {
    private getLogPath(): string | null {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) return null;

        const dir = path.join(workspaceFolders[0].uri.fsPath, '.agentstudio');
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        return path.join(dir, 'audit.json');
    }

    public getLogs(): AuditLogEntry[] {
        const logPath = this.getLogPath();
        if (logPath && fs.existsSync(logPath)) {
            try {
                const data = fs.readFileSync(logPath, 'utf8');
                return JSON.parse(data);
            } catch (e) {
                console.error('Failed to read audit log file', e);
            }
        }
        return [];
    }

    public logEvent(actor: string, action: string, details: string): void {
        const logs = this.getLogs();
        const newEntry: AuditLogEntry = {
            id: `audit_${Date.now()}`,
            timestamp: new Date().toISOString(),
            actor,
            action,
            details
        };
        logs.unshift(newEntry);

        const logPath = this.getLogPath();
        if (logPath) {
            fs.writeFileSync(logPath, JSON.stringify(logs, null, 2), 'utf8');
        }
    }
}
