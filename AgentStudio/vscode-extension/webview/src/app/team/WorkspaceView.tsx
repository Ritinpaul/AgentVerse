import * as React from 'react';
import { useState, useEffect } from 'react';
import { postVsCodeMessage } from '../../services/vscodeApi';

interface GitStatus {
    branch: string;
    modifiedFiles: string[];
    untrackedFiles: string[];
    isClean: boolean;
}

export const WorkspaceView: React.FC = () => {
    const [gitStatus, setGitStatus] = useState<GitStatus>({
        branch: 'main',
        modifiedFiles: [],
        untrackedFiles: [],
        isClean: true
    });
    
    const [commitMessage, setCommitMessage] = useState<string>('');
    const [isCommitting, setIsCommitting] = useState<boolean>(false);
    const [committedNotice, setCommittedNotice] = useState<boolean>(false);

    useEffect(() => {
        postVsCodeMessage({ type: 'GET_GIT_STATUS' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'GIT_STATUS_RESPONSE' && msg.status) {
                setGitStatus(msg.status);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const handleCommit = () => {
        if (commitMessage.trim() === '') return;
        
        setIsCommitting(true);
        postVsCodeMessage({ type: 'GIT_COMMIT', message: commitMessage });
        setCommitMessage('');

        setCommittedNotice(true);
        setTimeout(() => {
            setIsCommitting(false);
            setCommittedNotice(false);
            // Refresh git status
            postVsCodeMessage({ type: 'GET_GIT_STATUS' });
        }, 1500);
    };

    return (
        <div className="panel">
            <h2>Git-Native Workspace</h2>
            <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '11px', color: '#8B949E' }}>Branch:</span>
                <span style={{ 
                    background: '#12131C', 
                    color: '#10B981',
                    border: '1px solid #1E2030',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontFamily: 'var(--av-font-mono, monospace)',
                    fontWeight: 600
                }}>
                    {gitStatus.branch}
                </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ border: '1px solid #1E2030', borderRadius: '4px', padding: '8px 10px', background: '#0B0C14' }}>
                    <h3 style={{ margin: '0 0 6px 0', fontSize: '11px', color: '#CBD5E1' }}>Changes</h3>
                    {gitStatus.isClean ? (
                        <div style={{ opacity: 0.7, fontStyle: 'italic', fontSize: '11px', color: '#8B949E' }}>Workspace is clean.</div>
                    ) : (
                        <ul style={{ listStyleType: 'none', padding: 0, margin: 0, fontSize: '11px', fontFamily: 'var(--av-font-mono, monospace)' }}>
                            {gitStatus.modifiedFiles.map(file => (
                                <li key={file} style={{ color: '#F59E0B', marginBottom: '2px' }}>
                                    <span style={{ marginRight: '6px', fontWeight: 700 }}>M</span> {file}
                                </li>
                            ))}
                            {gitStatus.untrackedFiles.map(file => (
                                <li key={file} style={{ color: '#10B981', marginBottom: '2px' }}>
                                    <span style={{ marginRight: '6px', fontWeight: 700 }}>U</span> {file}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '11px', color: '#CBD5E1' }}>Commit</h3>
                    <textarea 
                        value={commitMessage}
                        onChange={(e) => setCommitMessage(e.target.value)}
                        placeholder="Commit message (e.g., Update agent prompt)"
                        style={{
                            width: '100%',
                            minHeight: '60px',
                            background: '#12131C',
                            color: '#FFFFFF',
                            border: '1px solid #282A3A',
                            borderRadius: '4px',
                            padding: '6px 8px',
                            fontSize: '11px'
                        }}
                    />
                    <button 
                        disabled={gitStatus.isClean || commitMessage.trim() === '' || isCommitting}
                        onClick={handleCommit}
                        style={{
                            background: committedNotice ? '#10B981' : '#B22222',
                            color: '#FFFFFF',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '7px 12px',
                            cursor: (gitStatus.isClean || commitMessage.trim() === '' || isCommitting) ? 'not-allowed' : 'pointer',
                            opacity: (gitStatus.isClean || commitMessage.trim() === '' || isCommitting) ? 0.4 : 1,
                            fontSize: '11px',
                            fontWeight: 600,
                            transition: 'background 0.2s ease',
                            width: '100%'
                        }}
                    >
                        {isCommitting ? 'Committing...' : committedNotice ? '✓ Committed & Synced!' : 'Commit & Sync'}
                    </button>
                </div>
            </div>
        </div>
    );
};
