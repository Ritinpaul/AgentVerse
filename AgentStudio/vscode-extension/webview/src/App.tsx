import * as React from 'react';
import { useState, useEffect, useCallback } from 'react';
import './styles/ide-tokens.css';
import { AgentCopilot } from './app/AgentCopilot';
import { AgentGraph } from './app/AgentGraph';
import { AgentInspector } from './app/AgentInspector';
import { MonitorPanel } from './app/MonitorPanel';
import { TracesPanel } from './app/TracesPanel';
import { RedTeamPanel } from './app/RedTeamPanel';
import { ComplianceReport } from './app/ComplianceReport';
import { RemoteDebugPanel } from './app/RemoteDebugPanel';
import { EnterpriseDashboard } from './app/EnterpriseDashboard';
import { AgentBuilderPanel } from './app/AgentBuilderPanel';
import { SignInPanel } from './app/SignInPanel';
import { SettingsPanel } from './app/SettingsPanel';
import { CommandPalette } from './app/CommandPalette';

import { getVsCodeApi } from './services/vscodeApi';
import { AgentOsClient, LogMessage, SwarmState } from './services/agentOsClient';

// VS Code API initialized (used by providers, not directly in this component)
getVsCodeApi();

// ── Panel ID type ──────────────────────────────────────────────────────────

type PanelId =
  | 'copilot'
  | 'graph'
  | 'inspector'
  | 'monitor'
  | 'traces'
  | 'builder'
  | 'redteam'
  | 'remotedebug'
  | 'enterprise'
  | 'visualizer'
  | 'signin'
  | 'settings';

const VALID_PANEL_IDS: PanelId[] = [
  'copilot',
  'graph',
  'inspector',
  'monitor',
  'traces',
  'builder',
  'redteam',
  'remotedebug',
  'enterprise',
  'visualizer',
  'signin',
  'settings',
];

/**
 * Each webview HTML is stamped with its intended panel via
 * `window.__PANEL_ID__` (see providers/agentCopilot.ts getWebviewHtml).
 * Use that to render the correct panel for the view the user opened.
 */
function getInitialPanel(): PanelId {
  try {
    const id = (window as any).__PANEL_ID__;
    if (id && VALID_PANEL_IDS.includes(id)) {
      return id;
    }
  } catch {
    // server-side / test render — fall through
  }
  return 'copilot';
}

// ── App Root ───────────────────────────────────────────────────────────────

export const App: React.FC = () => {
  const [activePanel, setActivePanel] = useState<PanelId>(getInitialPanel);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [swarmState, setSwarmState] = useState<SwarmState | null>(null);
  const [logs, setLogs] = useState<LogMessage[]>([]);

  // Bootstrap AgentOS connection
  useEffect(() => {
    const client = new AgentOsClient();
    const unsubscribe = client.onMessage((msg: LogMessage) => setLogs(prev => [...prev, msg]));

    client.fetchLatestSwarm()
      .then((state: SwarmState | null) => {
        if (state) {
          setSwarmState(state);
          client.subscribeToAgent(state.manager_agent_id);
          state.worker_agent_ids.forEach((id: string) => client.subscribeToAgent(id));
        }
      })
      .catch(() => {});

    // Listen for VS Code messages to switch panels
    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'SET_TAB' && msg.tab) {
        setActivePanel(msg.tab as PanelId);
      }
      if (msg.type === 'SHOW_PANEL' && msg.panel) {
        setActivePanel(msg.panel as PanelId);
      }
    };
    window.addEventListener('message', handleMessage);

    return () => {
      unsubscribe();
      client.disconnect();
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  // Global ⌘K / Ctrl+K → command palette (spec §9)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(o => !o);
      }
      if (e.key === 'Escape' && paletteOpen) {
        setPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [paletteOpen]);

  // Wire command palette selections to real panel navigation + actions.
  const handlePaletteSelect = (cmdId: string) => {
    switch (cmdId) {
      case 'open-monitor':
        setActivePanel('monitor');
        break;
      case 'show-traces':
        setActivePanel('traces');
        break;
      case 'open-inspector':
        setActivePanel('inspector');
        break;
      case 'open-copilot':
        setActivePanel('copilot');
        break;
      case 'run-agent':
        try {
          getVsCodeApi().postMessage({ type: 'RUN_AGENT', agentId: 'research-agent' });
        } catch {
          setActivePanel('copilot');
        }
        break;
      case 'edit-config':
        try {
          getVsCodeApi().postMessage({ type: 'OPEN_AGENT_CONFIG' });
        } catch {
          setActivePanel('copilot');
        }
        break;
      case 'view-policy':
        try {
          getVsCodeApi().postMessage({ type: 'OPEN_POLICY' });
        } catch {
          setActivePanel('traces');
        }
        break;
      default:
        break;
    }
  };

  // Render the active panel
  const renderPanel = () => {
    switch (activePanel) {
      case 'copilot':    return <AgentCopilot />;
      case 'graph':      return <AgentGraph />;
      case 'inspector':  return <AgentInspector />;
      case 'monitor':    return <MonitorPanel />;
      case 'traces':     return <TracesPanel />;
      case 'builder':    return <AgentBuilderPanel />;
      case 'redteam':    return <><RedTeamPanel /><ComplianceReport /></>;
      case 'remotedebug':return <RemoteDebugPanel />;
      case 'enterprise': return <EnterpriseDashboard />;
      case 'signin':     return <SignInPanel />;
      case 'settings':   return <SettingsPanel />;
      case 'visualizer':
      default:
        return (
          <div style={{
            padding: 24,
            background: 'var(--av-bg-editor)',
            color: 'var(--av-text-secondary)',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--av-font-ui)',
            gap: 12,
          }}>
            <div style={{ fontSize: 32 }}>⬡</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--av-text-primary)' }}>
              AgentVerse IDE
            </div>
            <div style={{ fontSize: 13, textAlign: 'center', maxWidth: 280, lineHeight: 1.6 }}>
              Select an agent from the Explorer, or open a panel from the Activity Bar to get started.
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                className="av-btn av-btn-primary"
                style={{ fontSize: 12 }}
                onClick={() => setActivePanel('copilot')}
              >
                Open Copilot
              </button>
              <button
                className="av-btn av-btn-ghost"
                style={{ fontSize: 12 }}
                onClick={() => setActivePanel('monitor')}
              >
                Open Monitor
              </button>
            </div>
          </div>
        );
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      overflow: 'auto',
      boxSizing: 'border-box',
      background: 'var(--av-bg-editor)',
      fontFamily: 'var(--av-font-ui)',
    }}>
      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectCommand={handlePaletteSelect}
      />
      {renderPanel()}
    </div>
  );
};
