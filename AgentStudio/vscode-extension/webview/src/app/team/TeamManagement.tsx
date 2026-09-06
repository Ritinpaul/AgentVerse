import * as React from 'react';
import { useState, useEffect } from 'react';
import { useRBAC, UserRole } from '../../contexts/RBACContext';
import { postVsCodeMessage } from '../../services/vscodeApi';

export interface RBACMember {
    email: string;
    role: UserRole;
    name?: string;
}

export interface RBACConfig {
    defaultRole: UserRole;
    members: RBACMember[];
}

export const TeamManagement: React.FC = () => {
    const { can } = useRBAC();
    const [defaultRole, setDefaultRole] = useState<UserRole>('developer');
    const [members, setMembers] = useState<RBACMember[]>([]);
    
    // Add Member form state
    const [newEmail, setNewEmail] = useState<string>('');
    const [newName, setNewName] = useState<string>('');
    const [newRole, setNewRole] = useState<UserRole>('developer');
    const [savedNotice, setSavedNotice] = useState<boolean>(false);

    useEffect(() => {
        postVsCodeMessage({ type: 'GET_RBAC_CONFIG' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'RBAC_CONFIG_RESPONSE' && msg.config) {
                if (msg.config.defaultRole) setDefaultRole(msg.config.defaultRole);
                if (Array.isArray(msg.config.members)) setMembers(msg.config.members);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    if (!can('edit_policy')) {
        return null; // Restricted to Team Lead / CISO
    }

    const handleRoleChange = (email: string, role: UserRole) => {
        setMembers(prev => prev.map(m => m.email === email ? { ...m, role } : m));
    };

    const handleRemoveMember = (email: string) => {
        setMembers(prev => prev.filter(m => m.email !== email));
    };

    const handleAddMember = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newEmail.trim()) return;

        const emailClean = newEmail.trim();
        const existing = members.find(m => m.email.toLowerCase() === emailClean.toLowerCase());

        if (existing) {
            setMembers(prev => prev.map(m => m.email.toLowerCase() === emailClean.toLowerCase() ? { ...m, role: newRole, name: newName || m.name } : m));
        } else {
            setMembers(prev => [...prev, { email: emailClean, role: newRole, name: newName.trim() || undefined }]);
        }

        setNewEmail('');
        setNewName('');
    };

    const handleSave = () => {
        postVsCodeMessage({
            type: 'SAVE_RBAC_CONFIG',
            config: {
                defaultRole,
                members
            }
        });
        setSavedNotice(true);
        setTimeout(() => setSavedNotice(false), 2000);
    };

    return (
        <div className="panel">
            <h2>Team & Governance Roles</h2>
            <p style={{ opacity: 0.8, marginBottom: '10px', fontSize: '11px' }}>
                Assign RBAC roles by user login email. Tracked in workspace Git.
            </p>

            <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0B0C14', padding: '8px 10px', borderRadius: '5px', border: '1px solid #1E2030' }}>
                <label style={{ fontSize: '11px', color: '#CBD5E1' }}><strong>Default Unlisted Role:</strong></label>
                <select 
                    value={defaultRole}
                    onChange={(e) => setDefaultRole(e.target.value as UserRole)}
                    style={{ padding: '3px 8px', background: '#12131C', color: '#FFFFFF', border: '1px solid #282A3A', borderRadius: '4px', fontSize: '11px' }}
                >
                    <option value="developer">Developer</option>
                    <option value="team_lead">Team Lead</option>
                    <option value="ciso">CISO</option>
                    <option value="auditor">Auditor</option>
                </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>Team Members ({members.length})</div>
                {members.length === 0 ? (
                    <div style={{ opacity: 0.7, fontStyle: 'italic', fontSize: '11px', color: '#8B949E' }}>No member overrides. All users receive default role.</div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {members.map(m => (
                            <div key={m.email} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: '#0B0C14', borderRadius: '4px', border: '1px solid #1E2030' }}>
                                <div>
                                    <strong style={{ fontSize: '11px', color: '#FFFFFF' }}>{m.name || m.email.split('@')[0]}</strong>
                                    <div style={{ fontSize: '10px', color: '#8B949E' }}>{m.email}</div>
                                </div>
                                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                    <select 
                                        value={m.role}
                                        onChange={(e) => handleRoleChange(m.email, e.target.value as UserRole)}
                                        style={{ padding: '2px 6px', background: '#12131C', color: '#FFFFFF', border: '1px solid #282A3A', borderRadius: '4px', fontSize: '10px' }}
                                    >
                                        <option value="developer">Developer</option>
                                        <option value="team_lead">Team Lead</option>
                                        <option value="ciso">CISO</option>
                                        <option value="auditor">Auditor</option>
                                    </select>
                                    <button 
                                        onClick={() => handleRemoveMember(m.email)}
                                        style={{ background: '#181926', color: '#EF4444', border: '1px solid #282A3A', padding: '2px 6px', cursor: 'pointer', borderRadius: '3px', fontSize: '10px' }}
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <form onSubmit={handleAddMember} style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                <input 
                    type="email" 
                    placeholder="member@enterprise.com" 
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    required
                    style={{ width: '100%', padding: '5px 8px', background: '#12131C', color: '#FFFFFF', border: '1px solid #282A3A', borderRadius: '4px', fontSize: '11px' }}
                />
                <div style={{ display: 'flex', gap: '6px' }}>
                    <input 
                        type="text" 
                        placeholder="Name (Optional)" 
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        style={{ flex: 1, padding: '5px 8px', background: '#12131C', color: '#FFFFFF', border: '1px solid #282A3A', borderRadius: '4px', fontSize: '11px' }}
                    />
                    <select 
                        value={newRole}
                        onChange={(e) => setNewRole(e.target.value as UserRole)}
                        style={{ padding: '5px 8px', background: '#12131C', color: '#FFFFFF', border: '1px solid #282A3A', borderRadius: '4px', fontSize: '11px' }}
                    >
                        <option value="developer">Dev</option>
                        <option value="team_lead">Lead</option>
                        <option value="ciso">CISO</option>
                        <option value="auditor">Audit</option>
                    </select>
                </div>
                <button 
                    type="submit"
                    style={{ padding: '6px 10px', background: '#181926', color: '#E2E8F0', border: '1px solid #282A3A', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}
                >
                    + Add Member
                </button>
            </form>

            <button 
                onClick={handleSave}
                style={{
                    background: savedNotice ? '#10B981' : '#B22222',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '7px 12px',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                    width: '100%',
                    transition: 'background 0.2s ease'
                }}
            >
                {savedNotice ? '✓ Team Roles Saved!' : 'Save Team Roles'}
            </button>
        </div>
    );
};
