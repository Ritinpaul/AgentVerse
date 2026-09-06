import * as React from 'react';
import { useState, useEffect, useRef } from 'react';
import '../styles/ide-tokens.css';

// ── Types ──────────────────────────────────────────────────────────────────

interface TelemetryEvent {
  id: string;
  ts: string;
  agent_id: string;
  event_type: 'tool_call' | 'policy_verdict' | 'egress_check' | 'llm_step';
  action_name: string;
  verdict: 'ALLOW' | 'BLOCK' | 'ESCALATE';
  details?: Record<string, unknown>;
}

interface ActiveAgent {
  id: string;
  name: string;
  status: 'running' | 'idle' | 'blocked';
  model: string;
  stepsDone: number;
  stepsTotal: number;
}

// ── Event Row ──────────────────────────────────────────────────────────────

const VERDICT_COLORS = {
  ALLOW:    { text: 'var(--av-emerald)', bg: 'var(--av-emerald-alpha)' },
  BLOCK:    { text: 'var(--av-crimson)', bg: 'var(--av-crimson-alpha)' },
  ESCALATE: { text: 'var(--av-amber)',   bg: 'var(--av-amber-alpha)'   },
};

const EVENT_ICONS: Record<TelemetryEvent['event_type'], React.ReactNode> = {
  tool_call: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
    </svg>
  ),
  policy_verdict: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  egress_check: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <circle cx="12" cy="12" r="10"/>
      <line x1="2" y1="12" x2="22" y2="12"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  ),
  llm_step: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#EC4899" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <rect x="4" y="4" width="16" height="16" rx="2"/>
      <rect x="9" y="9" width="6" height="6"/>
      <line x1="9" y1="1" x2="9" y2="4"/>
      <line x1="15" y1="1" x2="15" y2="4"/>
      <line x1="9" y1="20" x2="9" y2="23"/>
      <line x1="15" y1="20" x2="15" y2="23"/>
      <line x1="20" y1="9" x2="23" y2="9"/>
      <line x1="20" y1="15" x2="23" y2="15"/>
      <line x1="1" y1="9" x2="4" y2="9"/>
      <line x1="1" y1="15" x2="4" y2="15"/>
    </svg>
  ),
};

const EventRow: React.FC<{ event: TelemetryEvent; isNew?: boolean }> = ({ event, isNew }) => {
  const vc = VERDICT_COLORS[event.verdict];
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 12px',
      borderBottom: '1px solid var(--av-border-subtle)',
      background: isNew ? 'rgba(99,102,241,0.05)' : 'transparent',
      transition: 'background 0.5s ease',
      fontSize: 12,
    }}>
      <span style={{ fontFamily: 'var(--av-font-mono)', color: 'var(--av-text-muted)', minWidth: 52, fontSize: 11 }}>
        {event.ts}
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16 }}>{EVENT_ICONS[event.event_type]}</span>
      <span style={{ color: 'var(--av-text-secondary)', minWidth: 60, flexShrink: 0, fontSize: 11, letterSpacing: '0.02em' }}>
        {event.agent_id.slice(0, 12)}
      </span>
      <span style={{ fontFamily: 'var(--av-font-mono)', color: 'var(--av-text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {event.action_name}
      </span>
      <span style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
        padding: '1px 6px', borderRadius: 10,
        color: vc.text, background: vc.bg,
      }}>
        {event.verdict}
      </span>
    </div>
  );
};

// ── Agent Card ─────────────────────────────────────────────────────────────

const AgentCard: React.FC<{ agent: ActiveAgent }> = ({ agent }) => {
  const total = Math.max(1, agent.stepsTotal);
  const pct = Math.min(100, Math.round((agent.stepsDone / total) * 100));
  return (
    <div style={{
      padding: '10px 12px',
      borderBottom: '1px solid var(--av-border)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--av-text-primary)' }}>{agent.name}</div>
          <div style={{ fontSize: 11, color: 'var(--av-text-muted)', fontFamily: 'var(--av-font-mono)' }}>{agent.id}</div>
        </div>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', padding: '2px 7px', borderRadius: 10,
          color: agent.status === 'running' ? 'var(--av-emerald)' : agent.status === 'blocked' ? 'var(--av-crimson)' : 'var(--av-text-muted)',
          background: agent.status === 'running' ? 'var(--av-emerald-alpha)' : agent.status === 'blocked' ? 'var(--av-crimson-alpha)' : 'var(--av-bg-elevated)',
          textTransform: 'uppercase',
        }}>
          {agent.status}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1, height: 2, background: 'var(--av-bg-elevated)', borderRadius: 1 }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: agent.status === 'blocked' ? 'var(--av-crimson)' : 'var(--av-emerald)',
            borderRadius: 1, transition: 'width 0.5s ease',
          }} />
        </div>
        <span style={{ fontSize: 10, color: 'var(--av-text-muted)', minWidth: 55, textAlign: 'right', fontFamily: 'var(--av-font-mono)' }}>
          {agent.stepsDone}/{agent.stepsTotal} steps
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--av-text-muted)', marginTop: 3 }}>
        Model: {agent.model}
      </div>
    </div>
  );
};

// ── Monitor Panel ──────────────────────────────────────────────────────────

export const MonitorPanel: React.FC = () => {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [agents, setAgents] = useState<ActiveAgent[]>([]);
  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'ALLOW' | 'BLOCK'>('all');
  const [wsStatus, setWsStatus] = useState<'connected' | 'idle'>('idle');
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Request initial monitor state from VS Code extension host
    try {
      const vscode = (window as any).acquireVsCodeApi ? (window as any).acquireVsCodeApi() : null;
      if (vscode) {
        vscode.postMessage({ type: 'GET_MONITOR_STATE' });
      }
    } catch {
      // Running standalone or within embedded webview
    }

    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (!msg) return;

      if (msg.type === 'SWARM_TELEMETRY_EVENT' && msg.event) {
        const newEvt: TelemetryEvent = msg.event;
        setEvents(prev => [newEvt, ...prev].slice(0, 100));
        setNewEventIds(ids => new Set([...ids, newEvt.id]));
        setTimeout(() => setNewEventIds(ids => { const n = new Set(ids); n.delete(newEvt.id); return n; }), 800);
      } else if (msg.type === 'MONITOR_STATE_UPDATE') {
        if (Array.isArray(msg.events)) setEvents(msg.events);
        if (Array.isArray(msg.agents)) setAgents(msg.agents);
        if (msg.status === 'connected' || msg.status === 'idle') setWsStatus(msg.status);
      } else if (msg.type === 'RUN_AGENT_START') {
        setWsStatus('connected');
        setAgents(prev => {
          const exists = prev.find(a => a.id === msg.agentId);
          if (exists) return prev.map(a => a.id === msg.agentId ? { ...a, status: 'running' } : a);
          return [...prev, {
            id: msg.agentId,
            name: msg.agentName || msg.agentId,
            status: 'running',
            model: msg.model || 'Default Router',
            stepsDone: 0,
            stepsTotal: msg.stepsTotal || 10,
          }];
        });
      } else if (msg.type === 'RUN_AGENT_COMPLETE') {
        setAgents(prev => prev.map(a => a.id === msg.agentId ? { ...a, status: 'idle', stepsDone: a.stepsTotal } : a));
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const filteredEvents = filter === 'all' ? events : events.filter(e => e.verdict === filter);

  const stats = {
    allow: events.filter(e => e.verdict === 'ALLOW').length,
    block: events.filter(e => e.verdict === 'BLOCK').length,
    total: events.length,
  };

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
          Live Monitor
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            fontSize: 10, display: 'flex', alignItems: 'center', gap: 4,
            color: wsStatus === 'connected' ? 'var(--av-emerald)' : 'var(--av-text-muted)',
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: 'currentColor',
              ...(wsStatus === 'connected' ? { animation: 'av-pulse 2s infinite' } : {}),
            }} />
            {wsStatus === 'connected' ? '● WS Live' : 'Standby (Idle)'}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div style={{
        display: 'flex', gap: 0,
        borderBottom: '1px solid var(--av-border)', flexShrink: 0,
      }}>
        {[
          { label: 'Total',   value: stats.total, color: 'var(--av-text-secondary)' },
          { label: 'Allowed', value: stats.allow,  color: 'var(--av-emerald)' },
          { label: 'Blocked', value: stats.block,  color: 'var(--av-crimson)' },
        ].map((s, i) => (
          <div key={i} style={{
            flex: 1, textAlign: 'center', padding: '8px 4px',
            borderRight: i < 2 ? '1px solid var(--av-border)' : 'none',
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: s.color, fontFamily: 'var(--av-font-mono)' }}>
              {s.value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--av-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Active Agents */}
      <div style={{ flexShrink: 0, borderBottom: '1px solid var(--av-border)' }}>
        <div style={{ padding: '6px 12px 4px', fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--av-text-muted)' }}>
          Active Agents
        </div>
        {agents.length === 0 ? (
          <div style={{ padding: '14px 12px', textAlign: 'center', color: 'var(--av-text-muted)', fontSize: 11 }}>
            <div style={{ fontWeight: 600, color: 'var(--av-text-secondary)', marginBottom: 2 }}>No active agents</div>
            <div>Swarm is idle. Run an agent task to monitor execution in real time.</div>
          </div>
        ) : (
          agents.map(a => <AgentCard key={a.id} agent={a} />)
        )}
      </div>

      {/* Event Filter Tabs */}
      <div style={{
        display: 'flex', gap: 0, borderBottom: '1px solid var(--av-border)',
        flexShrink: 0,
      }}>
        {(['all', 'ALLOW', 'BLOCK'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            padding: '5px 12px', fontSize: 11, fontWeight: filter === f ? 600 : 400,
            color: filter === f ? 'var(--av-text-primary)' : 'var(--av-text-muted)',
            borderBottom: filter === f ? '2px solid var(--av-crimson)' : '2px solid transparent',
            textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            {f === 'all' ? 'All' : f}
          </button>
        ))}
      </div>

      {/* Live Event Stream */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {filteredEvents.length === 0 ? (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--av-text-muted)', fontSize: 11 }}>
            <div style={{ fontWeight: 600, color: 'var(--av-text-secondary)', marginBottom: 3 }}>No telemetry captured</div>
            <div>Real-time policy checks, egress events, and tool steps will stream here as agents run.</div>
          </div>
        ) : (
          filteredEvents.map(evt => (
            <EventRow key={evt.id} event={evt} isNew={newEventIds.has(evt.id)} />
          ))
        )}
        <div ref={eventsEndRef} />
      </div>
    </div>
  );
};

export default MonitorPanel;
