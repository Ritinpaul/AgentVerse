import * as React from 'react';

export interface AgentHealth {
    id: string;
    name: string;
    uptime: string;
    errorRate: number;
    avgCostPerRun: number;
    trustScore: number;
    lastDeploy: string;
}

export const AgentHealthCard: React.FC<{ agent: AgentHealth }> = ({ agent }) => {
    return (
        <div style={{ 
            border: '1px solid #1E2030', 
            padding: '10px 12px', 
            borderRadius: '5px',
            background: '#0B0C14'
        }}>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '12px', color: '#FFFFFF' }}>{agent.name}</h3>
            <div style={{ opacity: 0.6, fontSize: '10px', marginBottom: '10px', fontFamily: 'var(--av-font-mono, monospace)', color: '#8B949E' }}>ID: {agent.id}</div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                    <div style={{ fontSize: '10px', color: '#8B949E' }}>Uptime</div>
                    <div style={{ color: '#10B981', fontWeight: 'bold', fontSize: '11px', fontFamily: 'var(--av-font-mono, monospace)' }}>{agent.uptime}</div>
                </div>
                <div>
                    <div style={{ fontSize: '10px', color: '#8B949E' }}>Error Rate</div>
                    <div style={{ color: agent.errorRate > 5 ? '#EF4444' : '#10B981', fontWeight: 'bold', fontSize: '11px', fontFamily: 'var(--av-font-mono, monospace)' }}>
                        {agent.errorRate}%
                    </div>
                </div>
                <div>
                    <div style={{ fontSize: '10px', color: '#8B949E' }}>Avg Cost/Run</div>
                    <div style={{ fontWeight: 'bold', fontSize: '11px', color: '#FFFFFF', fontFamily: 'var(--av-font-mono, monospace)' }}>${agent.avgCostPerRun.toFixed(2)}</div>
                </div>
                <div>
                    <div style={{ fontSize: '10px', color: '#8B949E' }}>Trust Score</div>
                    <div style={{ color: agent.trustScore >= 90 ? '#10B981' : '#F59E0B', fontWeight: 'bold', fontSize: '11px', fontFamily: 'var(--av-font-mono, monospace)' }}>
                        {agent.trustScore}/100
                    </div>
                </div>
            </div>
            
            <div style={{ marginTop: '10px', borderTop: '1px solid #1E2030', paddingTop: '6px', fontSize: '10px', color: '#6B7280' }}>
                Last Deploy: {new Date(agent.lastDeploy).toLocaleString()}
            </div>
        </div>
    );
};
