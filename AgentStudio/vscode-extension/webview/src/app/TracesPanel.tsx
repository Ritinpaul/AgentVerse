import * as React from 'react';
import { useState } from 'react';
import '../styles/ide-tokens.css';

// ── Types ──────────────────────────────────────────────────────────────────

interface TraceRecord {
  id: string;
  ts: string;
  agent_id: string;
  agent_name: string;
  action: string;
  verdict: 'APPROVED' | 'BLOCKED' | 'ESCALATED';
  policy?: string;
  risk_score: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  duration_ms?: number;
  details?: string;
}

// ── Verdict Color ──────────────────────────────────────────────────────────

const VERDICT_COLORS = {
  APPROVED:  { text: 'var(--av-emerald)', bg: 'var(--av-emerald-alpha)' },
  BLOCKED:   { text: 'var(--av-crimson)', bg: 'var(--av-crimson-alpha)' },
  ESCALATED: { text: 'var(--av-amber)',   bg: 'var(--av-amber-alpha)'   },
};

const RISK_COLORS = {
  LOW:      'var(--av-emerald)',
  MEDIUM:   'var(--av-amber)',
  HIGH:     '#F97316',
  CRITICAL: 'var(--av-crimson)',
};

// ── Trace Row ──────────────────────────────────────────────────────────────

const TraceRow: React.FC<{
  trace: TraceRecord;
  expanded: boolean;
  onToggle: () => void;
}> = ({ trace, expanded, onToggle }) => {
  const vc = VERDICT_COLORS[trace.verdict];
  return (
    <div style={{ borderBottom: '1px solid var(--av-border-subtle)' }}>
      <div
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px', cursor: 'pointer',
          background: expanded ? 'var(--av-bg-elevated)' : 'transparent',
          fontSize: 12,
        }}
      >
        <span style={{ color: 'var(--av-text-muted)', fontSize: 10, minWidth: 50, fontFamily: 'var(--av-font-mono)' }}>
          {trace.ts}
        </span>
        <span style={{ color: 'var(--av-text-secondary)', minWidth: 70, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11 }}>
          {trace.agent_name}
        </span>
        <span style={{ flex: 1, fontFamily: 'var(--av-font-mono)', color: 'var(--av-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {trace.action}
        </span>
        <span style={{ fontSize: 9, letterSpacing: '0.04em', fontWeight: 700, color: RISK_COLORS[trace.risk_score] }}>
          {trace.risk_score}
        </span>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
          padding: '1px 6px', borderRadius: 10,
          color: vc.text, background: vc.bg, flexShrink: 0,
        }}>
          {trace.verdict}
        </span>
        <span style={{ color: 'var(--av-text-muted)', fontSize: 11 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div style={{
          padding: '8px 12px 10px 36px',
          background: 'var(--av-bg-editor)',
          borderTop: '1px solid var(--av-border)',
          fontSize: 12,
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--av-text-muted)', minWidth: 80, textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.06em' }}>Agent ID</span>
              <span style={{ fontFamily: 'var(--av-font-mono)', color: 'var(--av-text-primary)', fontSize: 11 }}>{trace.agent_id}</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--av-text-muted)', minWidth: 80, textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.06em' }}>Policy</span>
              <span style={{ color: 'var(--av-indigo)', fontSize: 11 }}>{trace.policy}</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--av-text-muted)', minWidth: 80, textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.06em' }}>Duration</span>
              <span style={{ fontFamily: 'var(--av-font-mono)', color: 'var(--av-text-primary)', fontSize: 11 }}>{trace.duration_ms}ms</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--av-text-muted)', minWidth: 80, textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.06em' }}>Reason</span>
              <span style={{ color: 'var(--av-text-secondary)', fontSize: 11 }}>{trace.details}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Traces Panel ───────────────────────────────────────────────────────────

export const TracesPanel: React.FC = () => {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterVerdict, setFilterVerdict] = useState<'all' | 'APPROVED' | 'BLOCKED' | 'ESCALATED'>('all');

  React.useEffect(() => {
    // Request initial telemetry stream
    try {
      const vscode = (window as any).acquireVsCodeApi ? (window as any).acquireVsCodeApi() : null;
      if (vscode) {
        vscode.postMessage({ type: 'SUBSCRIBE_RUN_TELEMETRY', runId: 'run-active' });
      }
    } catch (e) {}

    const handleMessage = (e: MessageEvent) => {
      const msg = e.data;
      if (msg?.type === 'RUN_TELEMETRY_UPDATE' && Array.isArray(msg.traces) && msg.traces.length > 0) {
        setTraces((prev) => {
          const combined = [...msg.traces, ...prev];
          const unique = Array.from(new Map(combined.map((t) => [t.id || t.ts, t])).values());
          return unique;
        });
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const filtered = traces
    .filter(t => filterVerdict === 'all' || t.verdict === filterVerdict)
    .filter(t =>
      !search ||
      t.action.toLowerCase().includes(search.toLowerCase()) ||
      t.agent_name.toLowerCase().includes(search.toLowerCase())
    );

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--av-bg-panel)', fontFamily: 'var(--av-font-ui)', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: '1px solid var(--av-border)', flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--av-text-secondary)' }}>
          Governance Traces
        </span>
        <span style={{ fontSize: 11, color: 'var(--av-text-muted)' }}>{traces.length} records</span>
      </div>

      {/* Search */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--av-border)', flexShrink: 0 }}>
        <input
          className="av-input"
          placeholder="Filter traces by action or agent..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ fontSize: 12 }}
        />
      </div>

      {/* Filter tabs */}
      <div style={{
        display: 'flex', borderBottom: '1px solid var(--av-border)', flexShrink: 0,
      }}>
        {(['all', 'APPROVED', 'BLOCKED', 'ESCALATED'] as const).map(f => (
          <button key={f} onClick={() => setFilterVerdict(f)} style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            padding: '5px 10px', fontSize: 10, fontWeight: filterVerdict === f ? 600 : 400,
            color: filterVerdict === f ? 'var(--av-text-primary)' : 'var(--av-text-muted)',
            borderBottom: filterVerdict === f ? '2px solid var(--av-crimson)' : '2px solid transparent',
            textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            {f === 'all' ? 'All' : f}
          </button>
        ))}
      </div>

      {/* Column headers */}
      <div style={{
        display: 'flex', gap: 8, padding: '4px 12px',
        background: 'var(--av-bg-panel)', borderBottom: '1px solid var(--av-border)',
        fontSize: 10, color: 'var(--av-text-muted)', letterSpacing: '0.06em',
        textTransform: 'uppercase', flexShrink: 0,
      }}>
        <span style={{ minWidth: 50 }}>Time</span>
        <span style={{ minWidth: 70 }}>Agent</span>
        <span style={{ flex: 1 }}>Action</span>
        <span style={{ minWidth: 50 }}>Risk</span>
        <span style={{ minWidth: 70 }}>Verdict</span>
        <span style={{ minWidth: 12 }} />
      </div>

      {/* Trace rows */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 && (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--av-text-muted)', fontSize: 12 }}>
            <div style={{ fontWeight: 600, color: 'var(--av-text-secondary)', marginBottom: 4 }}>
              {traces.length === 0 ? 'No audit traces captured' : 'No matching traces'}
            </div>
            <div>
              {traces.length === 0
                ? 'Execution traces, egress checks, and security policy verdicts will appear here in real time as agents execute.'
                : 'Try adjusting your search query or verdict filter.'}
            </div>
          </div>
        )}
        {filtered.map(trace => (
          <TraceRow
            key={trace.id}
            trace={trace}
            expanded={expandedId === trace.id}
            onToggle={() => setExpandedId(id => id === trace.id ? null : trace.id)}
          />
        ))}
      </div>
    </div>
  );
};

export default TracesPanel;
