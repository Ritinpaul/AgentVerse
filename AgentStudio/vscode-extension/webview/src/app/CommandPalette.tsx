import * as React from 'react';
import { useState, useEffect } from 'react';
import '../styles/ide-tokens.css';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectCommand?: (cmdId: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectCommand,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const recentItems = [
    { id: 'agent-research', icon: '►', label: 'research-agent', detail: 'agents/research-agent.yaml', type: 'agent' },
    { id: 'agent-reviewer', icon: '►', label: 'code-reviewer', detail: 'agents/code-reviewer.yaml', type: 'agent' },
  ];

  const commandItems = [
    { id: 'run-agent', icon: '▶', label: 'Run Agent (research-agent)', shortcut: '↵', type: 'cmd' },
    { id: 'open-inspector', icon: '↳', label: 'Open Agent Inspector', type: 'cmd' },
    { id: 'open-monitor', icon: '◉', label: 'Open Monitor Dashboard', type: 'cmd' },
    { id: 'open-copilot', icon: '✦', label: 'Open Copilot', type: 'cmd' },
    { id: 'show-traces', icon: '≣', label: 'Show Traces', type: 'cmd' },
    { id: 'edit-config', icon: '✎', label: 'Edit Agent Config', shortcut: 'agent.yaml', type: 'cmd' },
    { id: 'view-policy', icon: '⚑', label: 'View Governance Policy', type: 'cmd' },
  ];

  const fileItems = [
    { id: 'file-agent', icon: '▸', label: 'research-agent.yaml', detail: 'agents/', type: 'file' },
    { id: 'file-policy', icon: '▸', label: 'governance-policy.yaml', detail: 'policies/', type: 'file' },
    { id: 'file-tool', icon: '▸', label: 'web-search.ts', detail: 'tools/', type: 'file' },
  ];

  const handleSelect = (id: string) => {
    onSelectCommand?.(id);
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        justifyContent: 'center',
        paddingTop: 80,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          maxHeight: 480,
          background: '#0E0F18',
          border: '1px solid var(--av-border)',
          borderRadius: 12,
          boxShadow: '0 16px 48px rgba(0, 0, 0, 0.8)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: '1px solid var(--av-border)' }}>
          <span className="av-mono" style={{ color: 'var(--av-text-muted)', fontSize: 14 }}>⌕</span>
          <input
            autoFocus
            type="text"
            placeholder="Search agents, files, traces, commands..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--av-text-primary)',
              fontFamily: 'var(--av-font-ui)',
              fontSize: 13,
              flex: 1,
            }}
          />
          <span style={{
            fontSize: 11, fontFamily: 'var(--av-font-mono)',
            background: 'var(--av-bg-elevated)', border: '1px solid var(--av-border)',
            padding: '2px 6px', borderRadius: 4, color: 'var(--av-text-muted)'
          }}>⌘K</span>
        </div>

        {/* Results Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {/* RECENT */}
          <div className="av-section-label" style={{ fontSize: 10, padding: '6px 16px 4px' }}>RECENT</div>
          {recentItems.map((item, i) => (
            <div
              key={item.id}
              onClick={() => handleSelect(item.id)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 16px', cursor: 'pointer', fontSize: 12,
                background: selectedIndex === i ? 'var(--av-bg-elevated)' : 'transparent',
                color: 'var(--av-text-primary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{item.icon}</span>
                <span style={{ fontWeight: 500 }}>{item.label}</span>
                <span className="av-dot av-dot-green" />
              </div>
              <span className="av-mono" style={{ fontSize: 11, color: 'var(--av-text-muted)' }}>{item.detail}</span>
            </div>
          ))}

          {/* COMMANDS */}
          <div className="av-section-label" style={{ fontSize: 10, padding: '12px 16px 4px' }}>COMMANDS</div>
          {commandItems.map(item => (
            <div
              key={item.id}
              onClick={() => handleSelect(item.id)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 16px', cursor: 'pointer', fontSize: 12,
                color: 'var(--av-text-primary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>
              {item.shortcut && (
                <span className="av-mono" style={{ fontSize: 11, color: 'var(--av-text-muted)' }}>{item.shortcut}</span>
              )}
            </div>
          ))}

          {/* FILES */}
          <div className="av-section-label" style={{ fontSize: 10, padding: '12px 16px 4px' }}>FILES</div>
          {fileItems.map(item => (
            <div
              key={item.id}
              onClick={() => handleSelect(item.id)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 16px', cursor: 'pointer', fontSize: 12,
                color: 'var(--av-text-primary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>
              <span className="av-mono" style={{ fontSize: 11, color: 'var(--av-text-muted)' }}>{item.detail}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
