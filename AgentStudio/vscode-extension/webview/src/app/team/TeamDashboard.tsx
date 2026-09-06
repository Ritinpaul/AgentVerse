import * as React from 'react';
import { useState, useEffect } from 'react';
import { AgentHealthCard, AgentHealth } from './AgentHealthCard';
import { useRBAC } from '../../contexts/RBACContext';
import { postVsCodeMessage } from '../../services/vscodeApi';

export const TeamDashboard: React.FC = () => {
    const { can } = useRBAC();
    const [agents, setAgents] = useState<AgentHealth[]>([]);

    useEffect(() => {
        // Request discovered workspace agents
        postVsCodeMessage({ type: 'GET_WORKSPACE_AGENTS' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'WORKSPACE_AGENTS_RESPONSE' && Array.isArray(msg.agents)) {
                setAgents(msg.agents);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    if (!can('view_dashboard')) {
        return <div className="panel">You do not have permission to view the Team Dashboard.</div>;
    }

    return (
        <div className="panel" style={{ marginTop: '20px' }}>
            <h2>Shared Team Dashboard</h2>
            <p style={{ opacity: 0.8, marginBottom: '20px' }}>
                Overview of all agents owned by your team in the current workspace.
            </p>
            
            {agents.length === 0 ? (
                <div style={{ padding: '24px 0', textAlign: 'center', opacity: 0.7, fontStyle: 'italic' }}>
                    No agents found in this workspace. Create or configure an agent to see its telemetry here.
                </div>
            ) : (
                <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', 
                    gap: '20px' 
                }}>
                    {agents.map(agent => (
                        <AgentHealthCard key={agent.id} agent={agent} />
                    ))}
                </div>
            )}
        </div>
    );
};
