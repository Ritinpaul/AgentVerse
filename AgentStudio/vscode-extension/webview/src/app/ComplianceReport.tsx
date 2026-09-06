import * as React from 'react';

export const ComplianceReport: React.FC = () => {
    return (
        <div className="panel" style={{ marginTop: '20px' }}>
            <h2>Compliance Evidence Package</h2>
            <p>This report serves as proof of compliance before deployment to the AgentOS production cluster.</p>
            
            <div style={{ padding: '15px', border: '1px solid var(--vscode-panel-border)', borderRadius: '4px', background: 'var(--vscode-editor-background)' }}>
                <h3>Checklist</h3>
                <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
                    <li style={{ marginBottom: '10px' }}>
                        <span style={{ color: 'var(--vscode-testing-iconPassed)', marginRight: '10px' }}>✔</span> 
                        <strong>Governance Sandbox:</strong> All critical policy checks passed.
                    </li>
                    <li style={{ marginBottom: '10px' }}>
                        <span style={{ color: 'var(--vscode-testing-iconPassed)', marginRight: '10px' }}>✔</span> 
                        <strong>Cost Regression:</strong> Within 15% of historical baseline.
                    </li>
                    <li style={{ marginBottom: '10px' }}>
                        <span style={{ color: 'var(--vscode-testing-iconPassed)', marginRight: '10px' }}>✔</span> 
                        <strong>Dependency Check:</strong> All MCP servers verified and signed.
                    </li>
                </ul>

                <button style={{ marginTop: '15px', padding: '6px 12px', background: 'var(--vscode-button-background)', color: 'var(--vscode-button-foreground)', border: 'none', cursor: 'pointer' }}>
                    Generate PDF Report
                </button>
            </div>
        </div>
    );
};
