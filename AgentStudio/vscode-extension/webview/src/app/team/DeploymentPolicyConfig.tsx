import * as React from 'react';
import { useState, useEffect } from 'react';
import { useRBAC } from '../../contexts/RBACContext';
import { postVsCodeMessage } from '../../services/vscodeApi';

export const DeploymentPolicyConfig: React.FC = () => {
    const { can } = useRBAC();
    const [minEvalScore, setMinEvalScore] = useState<number>(90);
    const [maxCost, setMaxCost] = useState<number>(0.50);
    const [requireCiso, setRequireCiso] = useState<boolean>(true);
    const [savedNotice, setSavedNotice] = useState<boolean>(false);

    useEffect(() => {
        // Fetch saved policies from local workspace .agentstudio/policies.json
        postVsCodeMessage({ type: 'GET_POLICIES' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'POLICIES_RESPONSE' && msg.policy) {
                if (typeof msg.policy.minEvalScore === 'number') {
                    setMinEvalScore(msg.policy.minEvalScore);
                }
                if (typeof msg.policy.maxCostPerRun === 'number') {
                    setMaxCost(msg.policy.maxCostPerRun);
                }
                if (typeof msg.policy.requiresCISOApproval === 'boolean') {
                    setRequireCiso(msg.policy.requiresCISOApproval);
                }
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    if (!can('edit_policy')) {
        return null;
    }

    const handleSavePolicies = () => {
        postVsCodeMessage({
            type: 'SAVE_POLICIES',
            policy: {
                minEvalScore,
                maxCostPerRun: maxCost,
                requiresCISOApproval: requireCiso
            }
        });
        setSavedNotice(true);
        setTimeout(() => setSavedNotice(false), 2000);
    };

    return (
        <div className="panel">
            <h2>Deployment Policies (Automated Gates)</h2>
            <p style={{ opacity: 0.8, marginBottom: '12px', fontSize: '11px', lineHeight: 1.4 }}>
                Configure automated gates that agents must pass before deploying to production.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    background: '#0B0C14',
                    padding: '8px 10px',
                    borderRadius: '5px',
                    border: '1px solid #1E2030'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <label style={{ fontSize: '11px', fontWeight: 600, color: '#FFFFFF' }}>Min Eval Pass Rate</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <input 
                                type="number" 
                                value={minEvalScore} 
                                onChange={(e) => setMinEvalScore(Number(e.target.value))}
                                style={{
                                    width: '60px',
                                    padding: '3px 6px',
                                    background: '#12131C',
                                    color: '#FFFFFF',
                                    border: '1px solid #282A3A',
                                    borderRadius: '4px',
                                    fontFamily: 'var(--av-font-mono, monospace)',
                                    fontSize: '11px',
                                    textAlign: 'right'
                                }}
                            />
                            <span style={{ fontSize: '11px', color: '#8B949E' }}>%</span>
                        </div>
                    </div>
                    <div style={{ fontSize: '10px', color: '#6B7280' }}>Minimum benchmark accuracy to approve release.</div>
                </div>
                
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    background: '#0B0C14',
                    padding: '8px 10px',
                    borderRadius: '5px',
                    border: '1px solid #1E2030'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <label style={{ fontSize: '11px', fontWeight: 600, color: '#FFFFFF' }}>Max Cost per Run</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ fontSize: '11px', color: '#8B949E' }}>$</span>
                            <input 
                                type="number" 
                                step="0.01"
                                value={maxCost} 
                                onChange={(e) => setMaxCost(Number(e.target.value))}
                                style={{
                                    width: '60px',
                                    padding: '3px 6px',
                                    background: '#12131C',
                                    color: '#FFFFFF',
                                    border: '1px solid #282A3A',
                                    borderRadius: '4px',
                                    fontFamily: 'var(--av-font-mono, monospace)',
                                    fontSize: '11px',
                                    textAlign: 'right'
                                }}
                            />
                        </div>
                    </div>
                    <div style={{ fontSize: '10px', color: '#6B7280' }}>Maximum allowable token spend per task execution.</div>
                </div>
                
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#0B0C14',
                    padding: '8px 10px',
                    borderRadius: '5px',
                    border: '1px solid #1E2030'
                }}>
                    <div>
                        <div style={{ fontSize: '11px', fontWeight: 600, color: '#FFFFFF' }}>Require CISO Approval</div>
                        <div style={{ fontSize: '10px', color: '#6B7280' }}>Mandatory sign-off for prod gates</div>
                    </div>
                    <input 
                        type="checkbox" 
                        checked={requireCiso} 
                        onChange={(e) => setRequireCiso(e.target.checked)}
                        style={{ width: '15px', height: '15px', accentColor: '#E11D48', cursor: 'pointer' }}
                    />
                </div>
                
                <button 
                    onClick={handleSavePolicies}
                    style={{
                        background: savedNotice ? '#10B981' : '#B22222',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '7px 12px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        marginTop: '6px',
                        transition: 'background 0.2s ease',
                        width: '100%'
                    }}
                >
                    {savedNotice ? '✓ Policies Saved!' : 'Save Policies'}
                </button>
            </div>
        </div>
    );
};
