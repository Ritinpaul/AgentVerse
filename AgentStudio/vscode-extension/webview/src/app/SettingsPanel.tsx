import * as React from 'react';
import { useState, useEffect } from 'react';
import { postVsCodeMessage } from '../services/vscodeApi';

// ── Types ──────────────────────────────────────────────────────────────────────

type SettingsTab = 'models' | 'cloud' | 'local' | 'mcp' | 'governance' | 'features' | 'general';

interface ModelItem {
  id: string;
  name: string;
  provider: string;
  type: 'cloud' | 'local';
  enabled: boolean;
  isDefault?: boolean;
  status: 'available' | 'unavailable';
  statusMessage?: string;
}

interface ProviderConfig {
  id: string;
  name: string;
  type: 'cloud' | 'local';
  status: 'connected' | 'disconnected' | 'checking' | 'unconfigured';
  statusMessage?: string;
  hasKey?: boolean;
  baseUrl?: string;
  modelCount: number;
}

interface McpServerConfig {
  id: string;
  name: string;
  transport: 'stdio' | 'sse' | 'http';
  commandOrUrl: string;
  status: 'active' | 'inactive' | 'error';
  statusMessage?: string;
  enabled: boolean;
}

// ── Icon Components (Clean SVG, No Emojis) ─────────────────────────────────────

const GearIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

const CpuIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M9 2v2M15 20v2M9 20v2M2 15h2M2 9h2M20 15h2M20 9h2"/>
  </svg>
);

const CloudIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/>
  </svg>
);

const ServerIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
  </svg>
);

const ShieldIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

const RefreshIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
  </svg>
);

const SearchIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const PlusIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);

const TrashIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
);

// ── Main Settings Panel Component ──────────────────────────────────────────────

export const SettingsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('models');
  const [models, setModels] = useState<ModelItem[]>([]);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServerConfig[]>([]);
  const [autoDetectLocal, setAutoDetectLocal] = useState(true);
  const [guardrailProfile, setGuardrailProfile] = useState<'strict' | 'balanced' | 'permissive'>('balanced');
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [notice, setNotice] = useState<{ msg: string; isError?: boolean } | null>(null);

  // Inputs state
  const [apiKeyInputs, setApiKeyInputs] = useState<Record<string, string>>({});
  const [baseUrlInputs, setBaseUrlInputs] = useState<Record<string, string>>({});
  const [testingProviders, setTestingProviders] = useState<Record<string, boolean>>({});

  // Add MCP Modal
  const [showMcpModal, setShowMcpModal] = useState(false);
  const [mcpName, setMcpName] = useState('');
  const [mcpTransport, setMcpTransport] = useState<'stdio' | 'sse' | 'http'>('stdio');
  const [mcpCommand, setMcpCommand] = useState('');

  const showNotice = (msg: string, isError: boolean = false) => {
    setNotice({ msg, isError });
    setTimeout(() => setNotice(null), 4000);
  };

  // IPC Event Listener
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      const msg = e.data;
      if (!msg) return;

      if (msg.type === 'SETTINGS_STATE_RESPONSE') {
        if (msg.state) {
          setModels(msg.state.models || []);
          setProviders(msg.state.providers || []);
          setMcpServers(msg.state.mcpServers || []);
          setAutoDetectLocal(msg.state.autoDetectLocal ?? true);
          setGuardrailProfile(msg.state.guardrailProfile || 'balanced');
        }
        setLoading(false);
      } else if (msg.type === 'SAVE_API_KEY_RESPONSE') {
        if (msg.state) {
          setModels(msg.state.models || []);
          setProviders(msg.state.providers || []);
        }
        setTestingProviders(prev => ({ ...prev, [msg.providerId]: false }));
        if (msg.testRes?.connected) {
          showNotice(`API key saved & tested successfully for ${msg.providerId.toUpperCase()}`);
        } else {
          showNotice(`API key saved, but test failed: ${msg.testRes?.statusMessage || 'Disconnected'}`, true);
        }
      } else if (msg.type === 'TEST_PROVIDER_RESPONSE') {
        if (msg.state) {
          setModels(msg.state.models || []);
          setProviders(msg.state.providers || []);
        }
        setTestingProviders(prev => ({ ...prev, [msg.providerId]: false }));
        if (msg.testRes?.connected) {
          showNotice(`Connection test succeeded for ${msg.providerId.toUpperCase()}: ${msg.testRes.statusMessage}`);
        } else {
          showNotice(`Connection test failed for ${msg.providerId.toUpperCase()}: ${msg.testRes?.statusMessage || 'Unreachable'}`, true);
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Initial state request
    postVsCodeMessage({ type: 'GET_SETTINGS_STATE' });

    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleSaveApiKey = (providerId: string) => {
    const key = apiKeyInputs[providerId] || '';
    setTestingProviders(prev => ({ ...prev, [providerId]: true }));
    postVsCodeMessage({
      type: 'SAVE_API_KEY',
      providerId,
      apiKey: key,
    });
  };

  const handleTestProvider = (providerId: string) => {
    const baseUrl = baseUrlInputs[providerId];
    setTestingProviders(prev => ({ ...prev, [providerId]: true }));
    postVsCodeMessage({
      type: 'TEST_PROVIDER',
      providerId,
      baseUrl,
    });
  };

  const handleToggleModel = (modelId: string, currentEnabled: boolean) => {
    postVsCodeMessage({
      type: 'TOGGLE_MODEL',
      modelId,
      enabled: !currentEnabled,
    });
  };

  const handleSetDefaultModel = (modelId: string) => {
    postVsCodeMessage({
      type: 'SET_DEFAULT_MODEL',
      modelId,
    });
    showNotice(`Default model updated`);
  };

  const handleToggleAutoDetect = (enabled: boolean) => {
    setAutoDetectLocal(enabled);
    postVsCodeMessage({
      type: 'TOGGLE_AUTO_DETECT_LOCAL',
      enabled,
    });
  };

  const handleSetGuardrail = (profile: 'strict' | 'balanced' | 'permissive') => {
    setGuardrailProfile(profile);
    postVsCodeMessage({
      type: 'SET_GUARDRAIL_PROFILE',
      profile,
    });
    showNotice(`Guardrail policy updated to ${profile.toUpperCase()}`);
  };

  const handleAddMcpServer = () => {
    if (!mcpName.trim() || !mcpCommand.trim()) return;
    const newServer: McpServerConfig = {
      id: `mcp-${Date.now()}`,
      name: mcpName.trim(),
      transport: mcpTransport,
      commandOrUrl: mcpCommand.trim(),
      status: 'active',
      enabled: true,
    };
    postVsCodeMessage({
      type: 'SAVE_MCP_SERVER',
      server: newServer,
    });
    setMcpName('');
    setMcpCommand('');
    setShowMcpModal(false);
    showNotice(`Added MCP Server "${newServer.name}"`);
  };

  const handleDeleteMcpServer = (serverId: string) => {
    postVsCodeMessage({
      type: 'DELETE_MCP_SERVER',
      serverId,
    });
    showNotice(`Removed MCP server`);
  };

  const handleToggleMcpServer = (serverId: string, currentEnabled: boolean) => {
    postVsCodeMessage({
      type: 'TOGGLE_MCP_SERVER',
      serverId,
      enabled: !currentEnabled,
    });
  };

  const filteredModels = models.filter(m =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.provider.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      width: '100%',
      background: 'var(--av-bg-editor, #090A10)',
      color: 'var(--av-text-primary, #E2E8F0)',
      fontFamily: 'var(--vscode-font-family, system-ui, sans-serif)',
      boxSizing: 'border-box',
    }}>
      {/* ── Left Sidebar Navigation ──────────────────────────────────────── */}
      <div style={{
        width: 220,
        flexShrink: 0,
        background: '#0B0C12',
        borderRight: '1px solid #1E2028',
        padding: '16px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}>
        <div style={{
          fontSize: 11,
          fontWeight: 700,
          color: '#8B919D',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          padding: '4px 10px 10px',
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          IDE Settings
        </div>

        {[
          { id: 'models', label: 'Models', icon: <CpuIcon />, badge: models.filter(m => m.enabled).length },
          { id: 'cloud', label: 'Cloud Providers', icon: <CloudIcon />, badge: providers.filter(p => p.type === 'cloud' && p.status === 'connected').length },
          { id: 'local', label: 'Local Providers', icon: <ServerIcon />, badge: providers.filter(p => p.type === 'local' && p.status === 'connected').length },
          { id: 'mcp', label: 'MCP Servers', icon: <ServerIcon />, badge: mcpServers.filter(s => s.enabled).length },
          { id: 'governance', label: 'Agent & Governance', icon: <ShieldIcon /> },
          { id: 'features', label: 'Feature Flags', icon: <GearIcon /> },
          { id: 'general', label: 'General', icon: <GearIcon /> },
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: 5,
                border: 'none',
                background: isActive ? '#1A1C26' : 'transparent',
                color: isActive ? '#FFFFFF' : '#8B919D',
                fontWeight: isActive ? 600 : 500,
                fontSize: 12,
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background 0.12s, color 0.12s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: isActive ? '#B22222' : '#8B919D' }}>{tab.icon}</span>
                <span>{tab.label}</span>
              </div>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  background: isActive ? '#B22222' : 'rgba(255,255,255,0.08)',
                  color: '#FFFFFF',
                  padding: '1px 6px',
                  borderRadius: 10,
                }}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Main Content Area ────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 32px',
        maxWidth: 960,
        boxSizing: 'border-box',
      }}>
        {notice && (
          <div style={{
            background: notice.isError ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
            border: notice.isError ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.3)',
            color: notice.isError ? '#EF4444' : '#10B981',
            padding: '8px 12px',
            borderRadius: 6,
            fontSize: 12,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span>[SYS]</span> {notice.msg}
          </div>
        )}

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#8B919D', fontSize: 13 }}>
            Querying provider runtimes and settings...
          </div>
        ) : (
          <>
            {/* ── 1. MODELS TAB ────────────────────────────────────────────────── */}
            {activeTab === 'models' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Model Registry</h2>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8B919D' }}>
                      Enable models to expose them in the Agent Console dropdown and Agent Inspector.
                    </p>
                  </div>

                  {models.length > 0 && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      background: '#13141A',
                      border: '1px solid #242732',
                      borderRadius: 6,
                      padding: '4px 10px',
                      width: 220,
                    }}>
                      <SearchIcon />
                      <input
                        type="text"
                        placeholder="Filter models..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#E2E8F0',
                          outline: 'none',
                          fontSize: 12,
                          marginLeft: 6,
                          width: '100%',
                        }}
                      />
                    </div>
                  )}
                </div>

                {models.length === 0 ? (
                  <div style={{
                    background: '#111218',
                    border: '1px border-dashed #242732',
                    borderRadius: 8,
                    padding: '40px 24px',
                    textAlign: 'center',
                  }}>
                    <div style={{ color: '#E2E8F0', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>
                      No models available
                    </div>
                    <div style={{ color: '#8B919D', fontSize: 12, maxWidth: 460, margin: '0 auto 16px', lineHeight: 1.5 }}>
                      Configure a Cloud AI Provider with an API key in the Cloud Providers tab, or launch a Local AI Runtime (Ollama, LM Studio, vLLM).
                    </div>
                    <button
                      onClick={() => setActiveTab('cloud')}
                      style={{
                        background: '#B22222',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: 5,
                        padding: '6px 14px',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Configure Cloud Provider
                    </button>
                  </div>
                ) : (
                  <div style={{ background: '#111218', border: '1px solid #1E2028', borderRadius: 8, overflow: 'hidden' }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '2fr 1.2fr 1fr 1.2fr 80px',
                      padding: '10px 16px',
                      background: '#0E0F14',
                      borderBottom: '1px solid #1E2028',
                      fontSize: 11,
                      fontWeight: 700,
                      color: '#8B919D',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>
                      <div>Model Name</div>
                      <div>Provider</div>
                      <div>Type</div>
                      <div>Status</div>
                      <div style={{ textAlign: 'right' }}>Active</div>
                    </div>

                    {filteredModels.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '2fr 1.2fr 1fr 1.2fr 80px',
                          padding: '12px 16px',
                          alignItems: 'center',
                          borderBottom: '1px solid #191B24',
                          fontSize: 12,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, color: '#FFFFFF' }}>{m.name}</span>
                          {m.isDefault && (
                            <span style={{
                              fontSize: 10,
                              fontWeight: 700,
                              background: 'rgba(178,34,34,0.18)',
                              color: '#B22222',
                              border: '1px solid rgba(178,34,34,0.3)',
                              padding: '1px 6px',
                              borderRadius: 4,
                            }}>
                              DEFAULT
                            </span>
                          )}
                        </div>
                        <div style={{ color: '#8B919D' }}>{m.provider}</div>
                        <div>
                          <span style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: 4,
                            background: m.type === 'local' ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.06)',
                            color: m.type === 'local' ? '#818CF8' : '#A0AEC0',
                          }}>
                            {m.type.toUpperCase()}
                          </span>
                        </div>
                        <div>
                          {!m.isDefault ? (
                            <button
                              onClick={() => handleSetDefaultModel(m.id)}
                              style={{
                                background: 'transparent',
                                border: '1px solid #282A36',
                                color: '#8B919D',
                                fontSize: 11,
                                padding: '3px 8px',
                                borderRadius: 4,
                                cursor: 'pointer',
                              }}
                            >
                              Set Default
                            </button>
                          ) : (
                            <span style={{ fontSize: 11, color: '#10B981' }}>Selected</span>
                          )}
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <input
                            type="checkbox"
                            checked={m.enabled}
                            onChange={() => handleToggleModel(m.id, m.enabled)}
                            style={{ cursor: 'pointer', accentColor: '#B22222' }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── 2. CLOUD PROVIDERS TAB ──────────────────────────────────────── */}
            {activeTab === 'cloud' && (
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Cloud AI Providers</h2>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: '#8B919D' }}>
                  Configure API keys for OpenAI, Anthropic, OpenRouter, and Google Gemini.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {providers.filter(p => p.type === 'cloud').map((p) => {
                    const isTesting = testingProviders[p.id];
                    return (
                      <div
                        key={p.id}
                        style={{
                          background: '#111218',
                          border: '1px solid #1E2028',
                          borderRadius: 8,
                          padding: 16,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 12,
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF' }}>{p.name}</span>
                            <span style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 4,
                              background:
                                p.status === 'connected' ? 'rgba(16,185,129,0.12)' :
                                p.status === 'disconnected' ? 'rgba(239,68,68,0.12)' : 'rgba(255,255,255,0.06)',
                              color:
                                p.status === 'connected' ? '#10B981' :
                                p.status === 'disconnected' ? '#EF4444' : '#8B919D',
                            }}>
                              {p.status.toUpperCase()}
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            {p.modelCount > 0 && (
                              <span style={{ fontSize: 11, color: '#8B919D' }}>{p.modelCount} models validated</span>
                            )}
                            <button
                              onClick={() => handleTestProvider(p.id)}
                              disabled={isTesting}
                              style={{
                                background: '#1A1C26',
                                border: '1px solid #282A36',
                                color: '#E2E8F0',
                                padding: '4px 10px',
                                borderRadius: 5,
                                fontSize: 11,
                                cursor: isTesting ? 'wait' : 'pointer',
                              }}
                            >
                              {isTesting ? 'Testing...' : 'Test Connection'}
                            </button>
                          </div>
                        </div>

                        {p.statusMessage && (
                          <div style={{ fontSize: 11, color: p.status === 'connected' ? '#8B919D' : '#EF4444' }}>
                            {p.statusMessage}
                          </div>
                        )}

                        {p.id === 'agentverse-free' ? (
                          <div style={{
                            fontSize: 12,
                            color: '#10B981',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            borderRadius: 6,
                            padding: '8px 12px',
                          }}>
                            <span>Active with your account (50,000 free tokens/day quota). No API key required.</span>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', gap: 10 }}>
                            <input
                              type="password"
                              placeholder={p.hasKey ? 'Key saved (enter new key to replace)...' : `Enter ${p.name} API Key...`}
                              value={apiKeyInputs[p.id] || ''}
                              onChange={(e) => setApiKeyInputs(prev => ({ ...prev, [p.id]: e.target.value }))}
                              style={{
                                flex: 1,
                                background: '#0B0C10',
                                border: '1px solid #242732',
                                borderRadius: 5,
                                padding: '6px 10px',
                                color: '#E2E8F0',
                                fontSize: 12,
                                outline: 'none',
                              }}
                            />
                            <button
                              onClick={() => handleSaveApiKey(p.id)}
                              disabled={isTesting}
                              style={{
                                background: '#B22222',
                                color: '#FFFFFF',
                                border: 'none',
                                borderRadius: 5,
                                padding: '6px 14px',
                                fontSize: 11,
                                fontWeight: 700,
                                cursor: isTesting ? 'wait' : 'pointer',
                              }}
                            >
                              Save Key
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── 3. LOCAL PROVIDERS TAB ──────────────────────────────────────── */}
            {activeTab === 'local' && (
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Local AI Runtimes</h2>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: '#8B919D' }}>
                  Connect to local GPU engines (Ollama, vLLM, LM Studio) for 100% offline inference.
                </p>

                <div style={{
                  background: '#111218',
                  border: '1px solid #1E2028',
                  borderRadius: 8,
                  padding: 14,
                  marginBottom: 20,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF' }}>Auto-Detect Local Runtimes</div>
                    <div style={{ fontSize: 11, color: '#8B919D', marginTop: 2 }}>
                      Automatically scan localhost ports (11434, 8000, 1234) on IDE startup.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={autoDetectLocal}
                    onChange={e => handleToggleAutoDetect(e.target.checked)}
                    style={{ cursor: 'pointer', accentColor: '#B22222' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {providers.filter(p => p.type === 'local').map((p) => {
                    const isTesting = testingProviders[p.id];
                    return (
                      <div
                        key={p.id}
                        style={{
                          background: '#111218',
                          border: '1px solid #1E2028',
                          borderRadius: 8,
                          padding: 16,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 10,
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF' }}>{p.name}</span>
                            <span style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 4,
                              background: p.status === 'connected' ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.06)',
                              color: p.status === 'connected' ? '#10B981' : '#8B919D',
                            }}>
                              {p.status === 'connected' ? 'RUNNING' : 'NOT DETECTED'}
                            </span>
                          </div>

                          <button
                            onClick={() => handleTestProvider(p.id)}
                            disabled={isTesting}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 6,
                              background: '#1A1C26',
                              border: '1px solid #282A36',
                              color: '#E2E8F0',
                              fontSize: 11,
                              padding: '4px 10px',
                              borderRadius: 5,
                              cursor: isTesting ? 'wait' : 'pointer',
                            }}
                          >
                            <RefreshIcon />
                            <span>{isTesting ? 'Scanning...' : 'Refresh Models'}</span>
                          </button>
                        </div>

                        {p.statusMessage && (
                          <div style={{ fontSize: 11, color: p.status === 'connected' ? '#10B981' : '#8B919D' }}>
                            {p.statusMessage}
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <span style={{ fontSize: 11, color: '#8B919D', width: 90 }}>Base Endpoint:</span>
                          <input
                            type="text"
                            value={baseUrlInputs[p.id] ?? p.baseUrl ?? ''}
                            onChange={(e) => setBaseUrlInputs(prev => ({ ...prev, [p.id]: e.target.value }))}
                            style={{
                              flex: 1,
                              background: '#0B0C10',
                              border: '1px solid #242732',
                              borderRadius: 5,
                              padding: '6px 10px',
                              color: '#E2E8F0',
                              fontSize: 12,
                              outline: 'none',
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── 4. MCP SERVERS TAB ──────────────────────────────────────────── */}
            {activeTab === 'mcp' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Model Context Protocol (MCP)</h2>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8B919D' }}>
                      Register external MCP tool servers to grant agents capability to access local files, APIs, and databases.
                    </p>
                  </div>

                  <button
                    onClick={() => setShowMcpModal(true)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      background: '#B22222',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: 5,
                      padding: '6px 12px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <PlusIcon />
                    <span>Add MCP Server</span>
                  </button>
                </div>

                {/* Add MCP Server Modal */}
                {showMcpModal && (
                  <div style={{
                    background: '#111218',
                    border: '1px solid #B22222',
                    borderRadius: 8,
                    padding: 16,
                    marginBottom: 20,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 12,
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#FFFFFF' }}>Register New MCP Server</div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <input
                        type="text"
                        placeholder="Server Name (e.g. Git Tools)"
                        value={mcpName}
                        onChange={e => setMcpName(e.target.value)}
                        style={{
                          flex: 1,
                          background: '#0B0C10',
                          border: '1px solid #242732',
                          borderRadius: 5,
                          padding: '6px 10px',
                          color: '#E2E8F0',
                          fontSize: 12,
                          outline: 'none',
                        }}
                      />
                      <select
                        value={mcpTransport}
                        onChange={e => setMcpTransport(e.target.value as any)}
                        style={{
                          background: '#0B0C10',
                          border: '1px solid #242732',
                          borderRadius: 5,
                          padding: '6px 10px',
                          color: '#E2E8F0',
                          fontSize: 12,
                          outline: 'none',
                        }}
                      >
                        <option value="stdio">stdio</option>
                        <option value="sse">sse</option>
                        <option value="http">http</option>
                      </select>
                    </div>
                    <input
                      type="text"
                      placeholder="Command or URL (e.g. npx -y @modelcontextprotocol/server-filesystem)"
                      value={mcpCommand}
                      onChange={e => setMcpCommand(e.target.value)}
                      style={{
                        background: '#0B0C10',
                        border: '1px solid #242732',
                        borderRadius: 5,
                        padding: '6px 10px',
                        color: '#E2E8F0',
                        fontSize: 12,
                        outline: 'none',
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                      <button
                        onClick={() => setShowMcpModal(false)}
                        style={{
                          background: 'transparent',
                          border: '1px solid #242732',
                          color: '#8B919D',
                          borderRadius: 4,
                          padding: '4px 12px',
                          fontSize: 11,
                          cursor: 'pointer',
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleAddMcpServer}
                        disabled={!mcpName.trim() || !mcpCommand.trim()}
                        style={{
                          background: '#B22222',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: 4,
                          padding: '4px 12px',
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        Save Server
                      </button>
                    </div>
                  </div>
                )}

                {mcpServers.length === 0 ? (
                  <div style={{
                    background: '#111218',
                    border: '1px border-dashed #242732',
                    borderRadius: 8,
                    padding: '36px 24px',
                    textAlign: 'center',
                  }}>
                    <div style={{ color: '#E2E8F0', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                      No MCP servers configured
                    </div>
                    <div style={{ color: '#8B919D', fontSize: 12, marginBottom: 12 }}>
                      Click "Add MCP Server" above to connect custom tool servers.
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {mcpServers.map((s) => (
                      <div
                        key={s.id}
                        style={{
                          background: '#111218',
                          border: '1px solid #1E2028',
                          borderRadius: 8,
                          padding: 14,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontWeight: 600, color: '#FFFFFF', fontSize: 13 }}>{s.name}</span>
                            <span style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: '1px 6px',
                              borderRadius: 3,
                              background: s.status === 'active' ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.06)',
                              color: s.status === 'active' ? '#10B981' : '#8B919D',
                            }}>
                              {s.status.toUpperCase()}
                            </span>
                          </div>
                          <div style={{
                            fontSize: 11,
                            color: '#8B919D',
                            marginTop: 4,
                            fontFamily: "'JetBrains Mono', monospace",
                          }}>
                            [{s.transport.toUpperCase()}] {s.commandOrUrl}
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <button
                            onClick={() => handleToggleMcpServer(s.id, s.enabled)}
                            style={{
                              background: s.enabled ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                              color: s.enabled ? '#EF4444' : '#10B981',
                              border: 'none',
                              borderRadius: 4,
                              padding: '4px 10px',
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: 'pointer',
                            }}
                          >
                            {s.enabled ? 'Disable' : 'Enable'}
                          </button>

                          <button
                            onClick={() => handleDeleteMcpServer(s.id)}
                            style={{
                              background: 'transparent',
                              border: '1px solid #282A36',
                              color: '#EF4444',
                              borderRadius: 4,
                              padding: '4px 8px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── 5. GOVERNANCE TAB ───────────────────────────────────────────── */}
            {activeTab === 'governance' && (
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Agent & Governance</h2>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: '#8B919D' }}>
                  Set safety guardrail policies, approval gates, and MicroVM resource boundaries.
                </p>

                <div style={{ background: '#111218', border: '1px solid #1E2028', borderRadius: 8, padding: 16, marginBottom: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF', marginBottom: 10 }}>Guardrail Security Level</div>
                  <div style={{ display: 'flex', gap: 10 }}>
                    {(['strict', 'balanced', 'permissive'] as const).map((p) => (
                      <button
                        key={p}
                        onClick={() => handleSetGuardrail(p)}
                        style={{
                          flex: 1,
                          padding: '10px 14px',
                          borderRadius: 6,
                          border: guardrailProfile === p ? '1.5px solid #B22222' : '1px solid #242732',
                          background: guardrailProfile === p ? 'rgba(178,34,34,0.12)' : '#0B0C10',
                          color: guardrailProfile === p ? '#FFFFFF' : '#8B919D',
                          fontWeight: 600,
                          fontSize: 12,
                          cursor: 'pointer',
                          textTransform: 'capitalize',
                        }}
                      >
                        {p} Policy
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── 6. FEATURES TAB ─────────────────────────────────────────────── */}
            {activeTab === 'features' && (
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>Feature Flags</h2>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: '#8B919D' }}>
                  Enable or disable experimental AI features across the IDE workspace.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[
                    { title: 'Swarm Visualizer Graph', desc: 'Render real-time multi-agent execution DAGs in the editor panel.', default: true },
                    { title: 'Red-Team Security Auditor', desc: 'Automatically scan generated tool code for privilege escalation & egress risks.', default: true },
                    { title: 'Inline AI Autocomplete', desc: 'Predictive code completion powered by local or cloud models.', default: false },
                  ].map((f, i) => (
                    <div key={i} style={{
                      background: '#111218',
                      border: '1px solid #1E2028',
                      borderRadius: 8,
                      padding: 14,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF' }}>{f.title}</div>
                        <div style={{ fontSize: 11, color: '#8B919D', marginTop: 2 }}>{f.desc}</div>
                      </div>
                      <input type="checkbox" defaultChecked={f.default} style={{ cursor: 'pointer', accentColor: '#B22222' }} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── 7. GENERAL TAB ──────────────────────────────────────────────── */}
            {activeTab === 'general' && (
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>General Preferences</h2>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: '#8B919D' }}>
                  Global workspace settings, system prompt defaults, and telemetry options.
                </p>

                <div style={{ background: '#111218', border: '1px solid #1E2028', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#FFFFFF' }}>System Instruction Template</span>
                    <span style={{ fontSize: 11, color: '#8B919D' }}>Default for new agents</span>
                  </div>
                  <textarea
                    rows={4}
                    defaultValue="You are a senior software engineer assistant operating inside AgentVerse IDE. Output clean, verified code."
                    style={{
                      background: '#0B0C10',
                      border: '1px solid #242732',
                      borderRadius: 6,
                      color: '#E2E8F0',
                      padding: 10,
                      fontSize: 12,
                      fontFamily: "'JetBrains Mono', monospace",
                      outline: 'none',
                      resize: 'vertical',
                    }}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
