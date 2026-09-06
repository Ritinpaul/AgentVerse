import * as React from 'react';
import { useState, useEffect } from 'react';
import '../styles/ide-tokens.css';
import { postVsCodeMessage } from '../services/vscodeApi';

export const AgentInspector: React.FC = () => {
  const [agent, setAgent] = useState<any>(null);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [manifestHash, setManifestHash] = useState<string>('');
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [newToolId, setNewToolId] = useState('');
  const [newToolRisk, setNewToolRisk] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');

  // Request workspace agent from extension host on mount
  useEffect(() => {
    postVsCodeMessage({ type: 'GET_WORKSPACE_AGENT' });

    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (!msg) return;

      if (msg.type === 'AGENT_STATE') {
        if (msg.agent) setAgent(msg.agent);
        if (msg.filePath) setFilePath(msg.filePath);
        if (msg.manifestHash) setManifestHash(msg.manifestHash);
        if (msg.canUndo !== undefined) setCanUndo(msg.canUndo);
        if (msg.canRedo !== undefined) setCanRedo(msg.canRedo);
      } else if (msg.type === 'NO_AGENT') {
        setAgent(null);
        setFilePath(null);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleModelChange = (field: string, val: any) => {
    const newModel = { ...agent.model, [field]: val };
    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'UpdateModelConfig',
        args: newModel,
      },
    });
    setAgent((prev: any) => ({ ...prev, model: newModel }));
  };

  const handleInstructionsChange = (val: string) => {
    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'UpdateInstructions',
        args: { instructions: val },
      },
    });
    setAgent((prev: any) => ({ ...prev, instructions: val }));
  };

  const handleAddTool = () => {
    if (!newToolId.trim()) return;
    const tool = {
      id: newToolId.trim(),
      type: 'mcp',
      server: `mcp-${newToolId.trim()}`,
      tool: 'execute',
      risk: newToolRisk,
    };

    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'AddTool',
        args: { tool },
      },
    });

    setAgent((prev: any) => ({ ...prev, tools: [...(prev.tools || []), tool] }));
    setNewToolId('');
  };

  const handleRemoveTool = (toolId: string) => {
    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'RemoveTool',
        args: { toolId },
      },
    });

    setAgent((prev: any) => ({
      ...prev,
      tools: (prev.tools || []).filter((t: any) => t.id !== toolId),
    }));
  };

  const handleBudgetChange = (cost: number) => {
    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'UpdateBudget',
        args: { maxCostPerRun: cost },
      },
    });
    setAgent((prev: any) => ({ ...prev, budget: { ...prev.budget, maxCostPerRun: cost } }));
  };

  if (!agent) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          padding: 24,
          textAlign: 'center',
          background: 'var(--av-bg-panel)',
          fontFamily: 'var(--av-font-ui)',
          color: 'var(--av-text-secondary)',
          gap: 12,
        }}
      >
        <div style={{ fontSize: 28, color: 'var(--av-text-muted)' }}>⚙️</div>
        <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--av-text-heading)' }}>
          No Agent Manifest Active
        </div>
        <div style={{ fontSize: 11, lineHeight: 1.5, maxWidth: 260 }}>
          Open any <code style={{ color: 'var(--av-text-heading)', background: 'rgba(255,255,255,0.06)', padding: '1px 4px', borderRadius: 3 }}>agent.yaml</code> in your workspace, or create a new agent manifest.
        </div>
        <button
          className="av-btn av-btn-primary"
          style={{ fontSize: 11, marginTop: 8 }}
          onClick={() => postVsCodeMessage({ type: 'CREATE_DEFAULT_AGENT' })}
        >
          + Create agent.yaml
        </button>
        <button
          className="av-btn av-btn-ghost"
          style={{ fontSize: 11 }}
          onClick={() => postVsCodeMessage({ type: 'GET_WORKSPACE_AGENT' })}
        >
          Scan Workspace
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--av-bg-panel)', fontFamily: 'var(--av-font-ui)', fontSize: 12 }}>
      {/* Header with Undo/Redo */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', borderBottom: '1px solid var(--av-border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
          <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--av-text-secondary)' }}>
            Inspector
          </span>
          {filePath && (
            <span style={{ fontSize: 10, background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: 3, color: 'var(--av-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 110 }}>
              {filePath}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="av-btn av-btn-ghost" onClick={() => postVsCodeMessage({ type: 'UNDO_COMMAND' })} disabled={!canUndo} style={{ fontSize: 11, padding: '2px 6px' }}>
            ↩ Undo
          </button>
          <button className="av-btn av-btn-ghost" onClick={() => postVsCodeMessage({ type: 'REDO_COMMAND' })} disabled={!canRedo} style={{ fontSize: 11, padding: '2px 6px' }}>
            ↪ Redo
          </button>
        </div>
      </div>

      {/* Scrollable Form Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
        {/* Metadata */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--av-text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
            Metadata
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
            <span style={{ color: 'var(--av-text-muted)', minWidth: 60 }}>Name:</span>
            <span style={{ fontWeight: 600, color: 'var(--av-text-primary)' }}>{agent.metadata?.name || 'unnamed'}</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <span style={{ color: 'var(--av-text-muted)', minWidth: 60 }}>Version:</span>
            <span>{agent.metadata?.version || '1.0.0'}</span>
          </div>
        </div>

        {/* Model Config */}
        <div style={{ marginBottom: 14, borderTop: '1px solid var(--av-border)', paddingTop: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--av-text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            Model Configuration
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Provider:</span>
              <select
                value={agent.model?.provider || 'openai'}
                onChange={(e) => handleModelChange('provider', e.target.value)}
                style={{ background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, padding: '2px 4px' }}
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
                <option value="ollama">Ollama</option>
                <option value="openrouter">OpenRouter</option>
              </select>
            </label>

            <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Model Name:</span>
              <input
                type="text"
                value={agent.model?.name || ''}
                onChange={(e) => handleModelChange('name', e.target.value)}
                style={{ background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, padding: '2px 4px', width: 140 }}
              />
            </label>

            <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Temperature ({agent.model?.temperature ?? 0.7}):</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={agent.model?.temperature ?? 0.7}
                onChange={(e) => handleModelChange('temperature', parseFloat(e.target.value))}
                style={{ width: 100 }}
              />
            </label>
          </div>
        </div>

        {/* System Prompt Instructions */}
        <div style={{ marginBottom: 14, borderTop: '1px solid var(--av-border)', paddingTop: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--av-text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            System Instructions
          </div>
          <textarea
            rows={3}
            value={agent.instructions || ''}
            onChange={(e) => handleInstructionsChange(e.target.value)}
            style={{ width: '100%', background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, padding: 6, fontSize: 11, fontFamily: 'monospace' }}
          />
        </div>

        {/* Tools */}
        <div style={{ marginBottom: 14, borderTop: '1px solid var(--av-border)', paddingTop: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--av-text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            Tools ({agent.tools?.length || 0})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8 }}>
            {(agent.tools || []).map((tool: any) => (
              <div key={tool.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--av-bg-elevated)', padding: '4px 8px', borderRadius: 3 }}>
                <span>{tool.id} ({tool.risk || 'low'})</span>
                <button onClick={() => handleRemoveTool(tool.id)} style={{ background: 'none', border: 'none', color: '#EF4444', cursor: 'pointer' }}>✕</button>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 4 }}>
            <input
              type="text"
              placeholder="New tool ID..."
              value={newToolId}
              onChange={(e) => setNewToolId(e.target.value)}
              style={{ flex: 1, background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, padding: '2px 6px', fontSize: 11 }}
            />
            <select
              value={newToolRisk}
              onChange={(e) => setNewToolRisk(e.target.value as any)}
              style={{ background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, fontSize: 11 }}
            >
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
              <option value="critical">Critical Risk</option>
            </select>
            <button className="av-btn av-btn-primary" onClick={handleAddTool} style={{ fontSize: 11, padding: '2px 8px' }}>
              + Add
            </button>
          </div>
        </div>

        {/* Budget */}
        <div style={{ marginBottom: 14, borderTop: '1px solid var(--av-border)', paddingTop: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--av-text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            Budget Limits
          </div>
          <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Max Cost / Run ($):</span>
            <input
              type="number"
              step="0.05"
              value={agent.budget?.maxCostPerRun ?? 0.25}
              onChange={(e) => handleBudgetChange(parseFloat(e.target.value) || 0.05)}
              style={{ background: 'var(--av-bg-elevated)', color: 'var(--av-text-primary)', border: '1px solid var(--av-border)', borderRadius: 3, padding: '2px 4px', width: 80 }}
            />
          </label>
        </div>

        {/* Policy Disclaimer Notice */}
        <div style={{ background: '#1A180D', border: '1px solid #F59E0B', borderRadius: 4, padding: 8, fontSize: 10, color: '#FDE68A' }}>
          ℹ️ Local Policy Check: Local policy checks are advisory hints for IDE feedback. Authoritative policy evaluation is performed by GovernOS SENTINEL before run execution.
        </div>
      </div>

      {/* Footer / Hash */}
      <div style={{ padding: '6px 12px', borderTop: '1px solid var(--av-border)', fontSize: 10, fontFamily: 'monospace', color: 'var(--av-text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
        {manifestHash ? `Hash: ${manifestHash}` : 'Draft manifest'}
      </div>
    </div>
  );
};

export default AgentInspector;
