import * as React from 'react';
import { useState } from 'react';
import { useRBAC } from '../../contexts/RBACContext';

interface ApprovalRequest {
    id: string;
    agentName: string;
    developer: string;
    evalScore: number;
    costPerRun: number;
    status: 'pending' | 'approved' | 'rejected';
}

import { postVsCodeMessage } from '../../services/vscodeApi';

export const DeploymentApproval: React.FC = () => {
    const { can } = useRBAC();
    
    const [requests, setRequests] = useState<ApprovalRequest[]>([]);

    if (!can('approve_production') && !can('approve_staging')) {
        return null; // Only show for Team Leads or CISOs
    }

    const handleAction = (id: string, action: 'approved' | 'rejected') => {
        setRequests(prev => prev.map(req => 
            req.id === id ? { ...req, status: action } : req
        ));
        
        // Send message to VS Code extension backend
        postVsCodeMessage({ type: 'DEPLOYMENT_APPROVAL', requestId: id, action });
    };

    const pendingRequests = requests.filter(r => r.status === 'pending');

    return (
        <div className="panel">
            <h2>Deployment Approval Inbox</h2>
            {pendingRequests.length === 0 ? (
                <div style={{ padding: '12px 0', textAlign: 'center', color: '#8B949E', fontSize: '11px' }}>
                    No pending deployment approval requests.
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {pendingRequests.map(req => (
                        <div key={req.id} style={{ 
                            border: '1px solid #1E2030', 
                            padding: '10px 12px', 
                            borderRadius: '5px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '6px',
                            background: '#0B0C14'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ margin: 0, fontSize: '12px', color: '#FFFFFF' }}>{req.agentName}</h3>
                                <span style={{ fontSize: '10px', color: '#8B949E' }}>by {req.developer}</span>
                            </div>
                            <div style={{ fontSize: '11px', display: 'flex', gap: '12px' }}>
                                <span style={{ color: req.evalScore >= 90 ? '#10B981' : '#EF4444' }}>
                                    Eval: {req.evalScore}%
                                </span>
                                <span style={{ color: req.costPerRun <= 0.50 ? '#10B981' : '#EF4444' }}>
                                    Cost: ${req.costPerRun}/run
                                </span>
                            </div>
                            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                                <button 
                                    onClick={() => handleAction(req.id, 'approved')}
                                    style={{ flex: 1, background: '#10B981', color: '#000000', border: 'none', padding: '5px 10px', cursor: 'pointer', borderRadius: '4px', fontWeight: 700, fontSize: '11px' }}
                                >
                                    Approve
                                </button>
                                <button 
                                    onClick={() => handleAction(req.id, 'rejected')}
                                    style={{ flex: 1, background: '#181926', color: '#EF4444', border: '1px solid #282A3A', padding: '5px 10px', cursor: 'pointer', borderRadius: '4px', fontWeight: 600, fontSize: '11px' }}
                                >
                                    Reject
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
