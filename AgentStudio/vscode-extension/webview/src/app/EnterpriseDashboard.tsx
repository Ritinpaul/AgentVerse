import * as React from 'react';
import { useState } from 'react';
import { RBACProvider, useRBAC } from '../contexts/RBACContext';
import { WorkspaceView } from './team/WorkspaceView';
import { TeamDashboard } from './team/TeamDashboard';
import { DeploymentPolicyConfig } from './team/DeploymentPolicyConfig';
import { DeploymentApproval } from './team/DeploymentApproval';
import { TeamManagement } from './team/TeamManagement';

import { postVsCodeMessage } from '../services/vscodeApi';

const DashboardContent: React.FC = () => {
    const { user, setUserRole } = useRBAC();
    const handleSsoLogin = (provider: string) => {
        postVsCodeMessage({ type: 'SSO_LOGIN', provider });
    };

    const handleSsoLogout = () => {
        postVsCodeMessage({ type: 'SSO_LOGOUT' });
    };

    return (
        <div className="swarm-container">
            <div style={{
                fontSize: '12px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: '#FFFFFF',
                paddingBottom: '6px',
                borderBottom: '1px solid #1A1B26'
            }}>
                Enterprise Governance
            </div>
            
            {/* User & RBAC status bar */}
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                padding: '10px 12px',
                background: '#0D0E16',
                borderRadius: '6px',
                border: '1px solid #1A1B26'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <span style={{ fontSize: '11px', color: '#8B949E' }}>User: </span>
                        <strong style={{ fontSize: '12px', color: '#FFFFFF' }}>{user?.username}</strong>
                    </div>
                    <span style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        padding: '1px 6px',
                        borderRadius: '10px',
                        background: user?.isAuthenticated ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: user?.isAuthenticated ? '#10B981' : '#F59E0B'
                    }}>
                        {user?.isAuthenticated ? `SSO (${user?.provider})` : 'Local Auth'}
                    </span>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#8B949E' }}>Role:</span>
                    <select 
                        value={user?.role}
                        onChange={(e) => setUserRole(e.target.value as any)}
                        style={{
                            padding: '3px 8px',
                            background: '#12131C',
                            color: '#FFFFFF',
                            border: '1px solid #232738',
                            borderRadius: '4px',
                            fontSize: '11px'
                        }}
                    >
                        <option value="developer">Developer</option>
                        <option value="team_lead">Team Lead</option>
                        <option value="ciso">CISO</option>
                        <option value="auditor">Auditor</option>
                    </select>
                </div>
            </div>

            <TeamDashboard />
            <WorkspaceView />
            <TeamManagement />
            
            {/* Policies & Approvals - stacked vertically to fit sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <DeploymentPolicyConfig />
                <DeploymentApproval />
            </div>

            {/* SIEM Export */}
            <div className="panel">
                <h2>Audit Log Export (SIEM)</h2>
                <div style={{ opacity: 0.8, marginBottom: '8px', fontSize: '11px', color: '#94A3B8' }}>
                    Export audit trail and policy evaluation logs to your enterprise SIEM.
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button style={{
                        flex: 1,
                        background: '#B22222',
                        color: '#FFFFFF',
                        border: 'none',
                        padding: '6px 10px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer'
                    }}>
                        Export Splunk
                    </button>
                    <button style={{
                        flex: 1,
                        background: '#181926',
                        color: '#E2E8F0',
                        border: '1px solid #282A3A',
                        padding: '6px 10px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer'
                    }}>
                        Export Datadog
                    </button>
                </div>
            </div>
        </div>
    );
};

export const EnterpriseDashboard: React.FC = () => {
    return (
        <RBACProvider>
            <DashboardContent />
        </RBACProvider>
    );
};
