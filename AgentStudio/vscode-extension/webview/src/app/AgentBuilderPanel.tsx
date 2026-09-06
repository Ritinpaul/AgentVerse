import * as React from 'react';
import { useState, useEffect } from 'react';
import { postVsCodeMessage } from '../services/vscodeApi';

export interface AgentBlueprint {
    id: string;
    name: string;
    category: string;
    description: string;
    icon: string;
    yamlManifest: string;
    systemPrompt: string;
}

export interface OwnedAgent {
    id: string;
    slug: string;
    name: string;
    description: string;
    category: string;
    version: string;
    trustScore: number;
    status: 'verified' | 'published' | 'draft';
    runsCount: number;
    yamlManifest: string;
    systemPrompt: string;
}

export const AgentBuilderPanel: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'owned' | 'blueprints'>('owned');
    const [ownedAgents, setOwnedAgents] = useState<OwnedAgent[]>([]);
    const [blueprints, setBlueprints] = useState<AgentBlueprint[]>([]);
    const [selectedBlueprint, setSelectedBlueprint] = useState<string | null>(null);

    const [manifestYaml, setManifestYaml] = useState<string>('');
    const [systemPrompt, setSystemPrompt] = useState<string>('');
    const [activePreviewTab, setActivePreviewTab] = useState<'yaml' | 'prompt'>('yaml');
    const [targetDir, setTargetDir] = useState<string>('');

    const [importingSlug, setImportingSlug] = useState<string | null>(null);
    const [importedSlugs, setImportedSlugs] = useState<Record<string, boolean>>({});
    const [scaffoldNotice, setScaffoldNotice] = useState<boolean>(false);

    useEffect(() => {
        postVsCodeMessage({ type: 'GET_OWNED_AGENTS' });
        postVsCodeMessage({ type: 'GET_AGENT_BLUEPRINTS' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'OWNED_AGENTS_RESPONSE' && Array.isArray(msg.agents)) {
                setOwnedAgents(msg.agents);
            } else if (msg.type === 'AGENT_BLUEPRINTS_RESPONSE' && Array.isArray(msg.blueprints)) {
                setBlueprints(msg.blueprints);
                if (msg.blueprints.length > 0 && !selectedBlueprint) {
                    setSelectedBlueprint(msg.blueprints[0].id);
                    setManifestYaml(msg.blueprints[0].yamlManifest);
                    setSystemPrompt(msg.blueprints[0].systemPrompt);
                }
            } else if (msg.type === 'IMPORT_AGENT_RESPONSE') {
                setImportingSlug(null);
                if (msg.success && msg.slug) {
                    setImportedSlugs(prev => ({ ...prev, [msg.slug]: true }));
                    setTimeout(() => {
                        setImportedSlugs(prev => ({ ...prev, [msg.slug]: false }));
                    }, 3000);
                }
            } else if (msg.type === 'SAVE_AGENT_RESPONSE' && msg.success) {
                setScaffoldNotice(true);
                setTimeout(() => setScaffoldNotice(false), 2500);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, [selectedBlueprint]);

    const handleSelectBlueprint = (bp: AgentBlueprint) => {
        setSelectedBlueprint(bp.id);
        setManifestYaml(bp.yamlManifest);
        setSystemPrompt(bp.systemPrompt);
    };

    const handleImportAgent = (agent: OwnedAgent) => {
        setImportingSlug(agent.slug);
        postVsCodeMessage({
            type: 'IMPORT_AGENT_TO_WORKSPACE',
            slug: agent.slug,
            id: agent.id
        });
    };

    const handleScaffoldBlueprint = () => {
        if (!manifestYaml.trim()) return;
        postVsCodeMessage({
            type: 'SAVE_GENERATED_AGENT',
            manifestYaml,
            systemPrompt,
            targetDir: targetDir.trim() || undefined
        });
    };

    return (
        <div style={{
            padding: '16px',
            background: '#090A0E',
            minHeight: '100vh',
            color: '#E8EAF0',
            fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
            boxSizing: 'border-box'
        }}>
            {/* Header */}
            <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                        AgentStore & Catalog
                    </h2>
                </div>
                <p style={{ margin: 0, fontSize: '11px', color: '#8B919D', lineHeight: 1.5 }}>
                    Manage your published agents and import verified enterprise blueprints directly into your workspace.
                </p>
            </div>

            {/* Top Navigation Tabs */}
            <div style={{
                display: 'flex',
                gap: '8px',
                borderBottom: '1px solid #1E2028',
                paddingBottom: '10px',
                marginBottom: '16px'
            }}>
                <button
                    onClick={() => setActiveTab('owned')}
                    style={{
                        background: activeTab === 'owned' ? '#10B981' : '#14161E',
                        color: activeTab === 'owned' ? '#000000' : '#8B919D',
                        fontWeight: 700,
                        fontSize: '11px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid ' + (activeTab === 'owned' ? '#10B981' : '#2A2C38'),
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}
                >
                    <span>My Agents ({ownedAgents.length})</span>
                </button>
                <button
                    onClick={() => setActiveTab('blueprints')}
                    style={{
                        background: activeTab === 'blueprints' ? '#10B981' : '#14161E',
                        color: activeTab === 'blueprints' ? '#000000' : '#8B919D',
                        fontWeight: 700,
                        fontSize: '11px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid ' + (activeTab === 'blueprints' ? '#10B981' : '#2A2C38'),
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}
                >
                    <span>1-Click Blueprints</span>
                </button>
            </div>

            {/* TAB 1: OWNED AGENTS */}
            {activeTab === 'owned' && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: '#A0A8B8', letterSpacing: '0.04em' }}>
                            PUBLISHED & DRAFT AGENTS
                        </span>
                        <span style={{ fontSize: '10px', color: '#10B981', background: 'rgba(16,185,129,0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                            Connected to Store
                        </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {ownedAgents.map(agent => {
                            const isImporting = importingSlug === agent.slug;
                            const isImported = !!importedSlugs[agent.slug];

                            return (
                                <div
                                    key={agent.id}
                                    style={{
                                        background: '#12141C',
                                        border: '1px solid #20222E',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        transition: 'border-color 0.15s, background 0.15s'
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                                        <div>
                                            <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF' }}>
                                                {agent.name}
                                            </div>
                                            <div style={{ fontSize: '10px', color: '#8B919D', fontFamily: 'monospace', marginTop: '2px' }}>
                                                {agent.slug}
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', gap: '4px' }}>
                                            <span style={{
                                                fontSize: '9px',
                                                fontWeight: 700,
                                                background: 'rgba(16,185,129,0.15)',
                                                color: '#10B981',
                                                padding: '2px 5px',
                                                borderRadius: '3px'
                                            }}>
                                                Trust: {agent.trustScore}%
                                            </span>
                                            <span style={{
                                                fontSize: '9px',
                                                fontWeight: 700,
                                                background: '#1F222F',
                                                color: '#A0A8B8',
                                                padding: '2px 5px',
                                                borderRadius: '3px'
                                            }}>
                                                v{agent.version}
                                            </span>
                                        </div>
                                    </div>

                                    <p style={{ margin: '0 0 10px 0', fontSize: '11px', color: '#9CA3AF', lineHeight: 1.4 }}>
                                        {agent.description}
                                    </p>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '8px', borderTop: '1px solid #1C1E2A' }}>
                                        <span style={{ fontSize: '10px', color: '#6B7280' }}>
                                            {agent.category} • {agent.runsCount} runs
                                        </span>
                                        <button
                                            onClick={() => handleImportAgent(agent)}
                                            disabled={isImporting}
                                            style={{
                                                background: isImported ? '#10B981' : '#1A1D28',
                                                color: isImported ? '#000000' : '#E8EAF0',
                                                border: '1px solid ' + (isImported ? '#10B981' : '#2F3244'),
                                                fontSize: '10px',
                                                fontWeight: 700,
                                                padding: '5px 10px',
                                                borderRadius: '5px',
                                                cursor: isImporting ? 'wait' : 'pointer',
                                                transition: 'all 0.15s ease'
                                            }}
                                        >
                                            {isImported ? '✓ Imported' : isImporting ? 'Importing...' : 'Import to Workspace'}
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* TAB 2: 1-CLICK ENTERPRISE BLUEPRINTS */}
            {activeTab === 'blueprints' && (
                <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#A0A8B8', letterSpacing: '0.04em', marginBottom: '10px' }}>
                        SELECT A PRODUCTION BLUEPRINT
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px', marginBottom: '16px' }}>
                        {blueprints.map(bp => {
                            const isSelected = selectedBlueprint === bp.id;
                            return (
                                <div
                                    key={bp.id}
                                    onClick={() => handleSelectBlueprint(bp)}
                                    style={{
                                        padding: '10px 12px',
                                        background: isSelected ? '#161924' : '#10121A',
                                        border: '1px solid ' + (isSelected ? '#10B981' : '#1E202C'),
                                        borderRadius: '7px',
                                        cursor: 'pointer',
                                        transition: 'all 0.12s ease'
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <span style={{ fontSize: '12px', fontWeight: 700, color: isSelected ? '#FFFFFF' : '#D1D5DB' }}>
                                                {bp.name}
                                            </span>
                                        </div>
                                        <span style={{ fontSize: '9px', color: '#9CA3AF', background: '#1D202D', padding: '2px 5px', borderRadius: '3px' }}>
                                            {bp.category}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '10px', color: '#8B919D', lineHeight: 1.4 }}>
                                        {bp.description}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Preview of selected blueprint */}
                    {manifestYaml && (
                        <div style={{ background: '#10121A', border: '1px solid #1E202C', borderRadius: '8px', padding: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                <div style={{ fontSize: '11px', fontWeight: 700, color: '#FFFFFF' }}>
                                    Blueprint Manifest Preview
                                </div>
                                <div style={{ display: 'flex', gap: '4px' }}>
                                    <button
                                        onClick={() => setActivePreviewTab('yaml')}
                                        style={{
                                            fontSize: '9px',
                                            fontWeight: 700,
                                            padding: '3px 8px',
                                            borderRadius: '4px',
                                            border: 'none',
                                            background: activePreviewTab === 'yaml' ? '#10B981' : '#1E202C',
                                            color: activePreviewTab === 'yaml' ? '#000000' : '#8B919D',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        agent.yaml
                                    </button>
                                    <button
                                        onClick={() => setActivePreviewTab('prompt')}
                                        style={{
                                            fontSize: '9px',
                                            fontWeight: 700,
                                            padding: '3px 8px',
                                            borderRadius: '4px',
                                            border: 'none',
                                            background: activePreviewTab === 'prompt' ? '#10B981' : '#1E202C',
                                            color: activePreviewTab === 'prompt' ? '#000000' : '#8B919D',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        system.md
                                    </button>
                                </div>
                            </div>

                            <textarea
                                readOnly
                                value={activePreviewTab === 'yaml' ? manifestYaml : systemPrompt}
                                style={{
                                    width: '100%',
                                    height: '130px',
                                    fontFamily: "'JetBrains Mono', monospace",
                                    fontSize: '10px',
                                    lineHeight: 1.5,
                                    background: '#08090C',
                                    color: '#A0A8B8',
                                    border: '1px solid #1B1D27',
                                    borderRadius: '5px',
                                    padding: '8px',
                                    boxSizing: 'border-box',
                                    resize: 'none'
                                }}
                            />

                            <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                                <input
                                    type="text"
                                    placeholder="Folder (e.g. agents/my-agent)"
                                    value={targetDir}
                                    onChange={(e) => setTargetDir(e.target.value)}
                                    style={{
                                        flex: 1,
                                        padding: '6px 8px',
                                        fontSize: '10px',
                                        background: '#08090C',
                                        color: '#FFFFFF',
                                        border: '1px solid #1E202C',
                                        borderRadius: '5px'
                                    }}
                                />
                                <button
                                    onClick={handleScaffoldBlueprint}
                                    style={{
                                        background: scaffoldNotice ? '#10B981' : '#1F2332',
                                        color: scaffoldNotice ? '#000000' : '#FFFFFF',
                                        border: '1px solid ' + (scaffoldNotice ? '#10B981' : '#31374C'),
                                        fontSize: '10px',
                                        fontWeight: 700,
                                        padding: '6px 12px',
                                        borderRadius: '5px',
                                        cursor: 'pointer',
                                        whiteSpace: 'nowrap',
                                        transition: 'all 0.15s ease'
                                    }}
                                >
                                    {scaffoldNotice ? '✓ Scaffolding Created!' : 'Scaffold Blueprint'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

