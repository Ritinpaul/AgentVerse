import * as React from 'react';
import { useState, useEffect, useRef } from 'react';
import '../styles/ide-tokens.css';
import { postVsCodeMessage } from '../services/vscodeApi';

// ── Types ──────────────────────────────────────────────────────────────────

export type NodeType =
  | 'llm'
  | 'tool'
  | 'condition'
  | 'parallel'
  | 'loop'
  | 'retry'
  | 'human_approval'
  | 'subagent'
  | 'input'
  | 'output';

export interface GraphVisualNode {
  id: string;
  label: string;
  sublabel?: string;
  type: NodeType;
  status?: 'ready' | 'running' | 'idle' | 'blocked';
  toolRef?: string;
}

export interface GraphVisualEdge {
  from: string;
  to: string;
  condition?: string;
  animated?: boolean;
}

export interface AgentGraphProps {
  nodes?: GraphVisualNode[];
  edges?: GraphVisualEdge[];
  agentName?: string;
}

// ── Layout Constants ───────────────────────────────────────────────────────

const NODE_W = 160;
const NODE_H = 52;
const H_GAP = 50;
const V_GAP = 55;

const TYPE_COLORS: Record<NodeType, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  llm:            { bg: '#0D0E1A', border: '#6366F1', text: '#A5B4FC', icon: <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" fill="#A5B4FC"/> },
  tool:           { bg: '#0D0E14', border: '#374151', text: '#9CA3AF', icon: <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" fill="none" stroke="#9CA3AF" strokeWidth="2"/> },
  condition:      { bg: '#1A180D', border: '#F59E0B', text: '#FDE68A', icon: <path d="M6 3v12s0 3 3 3h6m0 0l-3-3m3 3l-3 3" fill="none" stroke="#FDE68A" strokeWidth="2"/> },
  parallel:       { bg: '#0D1A1A', border: '#06B6D4', text: '#A5F3FC', icon: <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="none" stroke="#A5F3FC" strokeWidth="2"/> },
  loop:           { bg: '#1A0D18', border: '#EC4899', text: '#FBCFE8', icon: <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" fill="none" stroke="#FBCFE8" strokeWidth="2"/> },
  retry:          { bg: '#1A120D', border: '#F97316', text: '#FFEDD5', icon: <path d="M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" fill="none" stroke="#FFEDD5" strokeWidth="2"/> },
  human_approval: { bg: '#1A0D0D', border: '#EF4444', text: '#FCA5A5', icon: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="none" stroke="#FCA5A5" strokeWidth="2"/> },
  subagent:       { bg: '#120D1A', border: '#8B5CF6', text: '#C4B5FD', icon: <path d="M12 2a2 2 0 0 1 2 2v2h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2V4a2 2 0 0 1 2-2z" fill="none" stroke="#C4B5FD" strokeWidth="2"/> },
  input:          { bg: '#0D1610', border: '#10B981', text: '#6EE7B7', icon: <path d="M12 5v14M5 12l7 7 7-7" fill="none" stroke="#6EE7B7" strokeWidth="2"/> },
  output:         { bg: '#0D1610', border: '#10B981', text: '#6EE7B7', icon: <path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke="#6EE7B7" strokeWidth="2"/> },
};

// ── Layout Calculator (Topological Rank DAG Layout) ─────────────────────────

function computeLayout(nodes: GraphVisualNode[], edges: GraphVisualEdge[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  if (nodes.length === 0) return positions;

  const centerX = 360;

  // In-degree tracking
  const inDegree = new Map<string, number>();
  nodes.forEach((n) => inDegree.set(n.id, 0));
  edges.forEach((e) => {
    if (inDegree.has(e.to)) {
      inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
    }
  });

  // Rank assignment
  const rankMap = new Map<string, number>();
  nodes.forEach((n) => {
    if (inDegree.get(n.id) === 0) {
      rankMap.set(n.id, 0);
    }
  });

  let changed = true;
  let iterations = 0;
  while (changed && iterations < 20) {
    changed = false;
    iterations++;
    edges.forEach((e) => {
      const fromRank = rankMap.get(e.from);
      if (fromRank !== undefined) {
        const currentToRank = rankMap.get(e.to) ?? 0;
        const targetRank = fromRank + 1;
        if (targetRank > currentToRank) {
          rankMap.set(e.to, targetRank);
          changed = true;
        }
      }
    });
  }

  // Fallback for unranked
  nodes.forEach((n, idx) => {
    if (!rankMap.has(n.id)) {
      rankMap.set(n.id, idx);
    }
  });

  // Group by rank
  const rankGroups = new Map<number, GraphVisualNode[]>();
  nodes.forEach((n) => {
    const r = rankMap.get(n.id) || 0;
    if (!rankGroups.has(r)) rankGroups.set(r, []);
    rankGroups.get(r)!.push(n);
  });

  const sortedRanks = Array.from(rankGroups.keys()).sort((a, b) => a - b);
  const vSpacing = Math.max(65, Math.min(85, Math.floor(320 / Math.max(1, sortedRanks.length))));

  sortedRanks.forEach((r, rankIdx) => {
    const group = rankGroups.get(r)!;
    const rowSize = group.length;
    const totalRowW = rowSize * NODE_W + (rowSize - 1) * H_GAP;

    group.forEach((node, colIdx) => {
      positions.set(node.id, {
        x: centerX - totalRowW / 2 + colIdx * (NODE_W + H_GAP),
        y: 35 + rankIdx * vSpacing,
      });
    });
  });

  return positions;
}

// ── SVG Node Component ─────────────────────────────────────────────────────

const GraphNodeComponent: React.FC<{
  node: GraphVisualNode;
  x: number;
  y: number;
  selected: boolean;
  onClick: () => void;
}> = ({ node, x, y, selected, onClick }) => {
  const colors = TYPE_COLORS[node.type] || TYPE_COLORS.tool;
  const isRunning = node.status === 'running';

  return (
    <g transform={`translate(${x}, ${y})`} onClick={onClick} style={{ cursor: 'pointer' }}>
      {(selected || isRunning) && (
        <rect
          x={-2}
          y={-2}
          width={NODE_W + 4}
          height={NODE_H + 4}
          rx={6}
          fill="none"
          stroke={isRunning ? '#10B981' : '#B22222'}
          strokeWidth={1.5}
          opacity={0.5}
          style={isRunning ? { animation: 'av-pulse 2s ease-in-out infinite' } : {}}
        />
      )}

      <rect
        x={0}
        y={0}
        width={NODE_W}
        height={NODE_H}
        rx={4}
        fill={colors.bg}
        stroke={selected ? '#B22222' : colors.border}
        strokeWidth={selected ? 1.5 : 1}
      />

      <g transform="translate(10, 16) scale(0.65)">
        <svg width="24" height="24" viewBox="0 0 24 24">
          {colors.icon}
        </svg>
      </g>

      <text
        x={32}
        y={21}
        fontSize={11}
        fontWeight={600}
        fill={colors.text}
        fontFamily="Inter, system-ui, sans-serif"
      >
        {node.label.length > 18 ? node.label.slice(0, 17) + '…' : node.label}
      </text>

      {node.sublabel && (
        <text
          x={32}
          y={36}
          fontSize={9}
          fill="#4A5568"
          fontFamily="Inter, system-ui, sans-serif"
        >
          {node.sublabel.length > 22 ? node.sublabel.slice(0, 21) + '…' : node.sublabel}
        </text>
      )}

      <circle
        cx={NODE_W - 10}
        cy={10}
        r={4}
        fill={
          node.status === 'running'
            ? '#10B981'
            : node.status === 'ready'
            ? '#10B981'
            : node.status === 'blocked'
            ? '#E11D48'
            : '#4A5568'
        }
      />
    </g>
  );
};

// ── SVG Edge Component ─────────────────────────────────────────────────────

const GraphEdgeComponent: React.FC<{
  fromPos: { x: number; y: number };
  toPos: { x: number; y: number };
  animated: boolean;
}> = ({ fromPos, toPos, animated }) => {
  const x1 = fromPos.x + NODE_W / 2;
  const y1 = fromPos.y + NODE_H;
  const x2 = toPos.x + NODE_W / 2;
  const y2 = toPos.y;
  const cy = (y1 + y2) / 2;
  const d = `M ${x1} ${y1} C ${x1} ${cy} ${x2} ${cy} ${x2} ${y2}`;

  return (
    <path
      d={d}
      fill="none"
      stroke={animated ? '#6366F1' : '#1E2030'}
      strokeWidth={animated ? 1.5 : 1}
      strokeDasharray={animated ? '4 3' : undefined}
      opacity={animated ? 0.8 : 0.5}
    />
  );
};

// ── Main Graph Component ───────────────────────────────────────────────────

export const AgentGraph: React.FC<AgentGraphProps> = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [nodes, setNodes] = useState<GraphVisualNode[]>([]);
  const [edges, setEdges] = useState<GraphVisualEdge[]>([]);
  const [manifestHash, setManifestHash] = useState<string>('');
  const [agentName, setAgentName] = useState<string>('');
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [newNodeType, setNewNodeType] = useState<NodeType>('tool');

  // Listen to AGENT_STATE messages from Extension Host and request state on mount
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'AGENT_STATE') {
        if (msg.agent) {
          if (msg.agent.metadata && msg.agent.metadata.name) {
            setAgentName(msg.agent.metadata.name);
          }
          if (msg.manifestHash) setManifestHash(msg.manifestHash);
          if (msg.canUndo !== undefined) setCanUndo(msg.canUndo);
          if (msg.canRedo !== undefined) setCanRedo(msg.canRedo);

          // Convert agent AST workflow to GraphVisualNodes
          if (msg.agent.workflow && msg.agent.workflow.nodes && msg.agent.workflow.nodes.length > 0) {
            const mappedNodes: GraphVisualNode[] = msg.agent.workflow.nodes.map((n: any) => ({
              id: n.id,
              label: n.label || n.id,
              type: (n.type as NodeType) || 'tool',
              sublabel: n.toolRef ? `Tool: ${n.toolRef}` : n.type,
              status: 'ready',
            }));
            const mappedEdges: GraphVisualEdge[] = (msg.agent.workflow.edges || []).map((e: any) => ({
              from: e.from,
              to: e.to,
              animated: true,
            }));
            setNodes(mappedNodes);
            setEdges(mappedEdges);
          }
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Request active document state from Extension Host immediately on mount
    postVsCodeMessage({ type: 'GET_AGENT_STATE' });

    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const layout = computeLayout(nodes, edges);

  const handleAddNode = () => {
    const nodeId = `${newNodeType}-${Date.now().toString().slice(-4)}`;
    const newNode: GraphVisualNode = {
      id: nodeId,
      label: `${newNodeType.toUpperCase()} Step`,
      type: newNodeType,
      status: 'ready',
    };

    // Emit AGENT_COMMAND to Extension Host to mutate canonical AST
    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'AddWorkflowNode',
        args: { node: { id: nodeId, type: newNodeType, label: newNode.label } },
      },
    });

    setNodes((prev) => [...prev, newNode]);
  };

  const handleRemoveSelectedNode = () => {
    if (!selectedId) return;

    postVsCodeMessage({
      type: 'AGENT_COMMAND',
      command: {
        commandType: 'RemoveWorkflowNode',
        args: { nodeId: selectedId },
      },
    });

    setNodes((prev) => prev.filter((n) => n.id !== selectedId));
    setEdges((prev) => prev.filter((e) => e.from !== selectedId && e.to !== selectedId));
    setSelectedId(null);
  };

  const handleUndo = () => {
    postVsCodeMessage({ type: 'UNDO_COMMAND' });
  };

  const handleRedo = () => {
    postVsCodeMessage({ type: 'REDO_COMMAND' });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--av-bg-editor)' }}>
      {/* Control Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          borderBottom: '1px solid var(--av-border)',
          background: 'var(--av-bg-panel)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--av-text-secondary)' }}>
            Agent Workflow Graph
          </span>
          {agentName && (
            <span style={{ fontSize: 10, color: 'var(--av-accent-blue)', background: 'rgba(59, 130, 246, 0.1)', padding: '2px 6px', borderRadius: 4 }}>
              {agentName}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select
            value={newNodeType}
            onChange={(e) => setNewNodeType(e.target.value as NodeType)}
            style={{
              background: 'var(--av-bg-elevated)',
              color: 'var(--av-text-primary)',
              border: '1px solid var(--av-border)',
              borderRadius: 3,
              fontSize: 11,
              padding: '2px 4px',
            }}
          >
            <option value="llm">LLM</option>
            <option value="tool">Tool</option>
            <option value="condition">Condition</option>
            <option value="parallel">Parallel</option>
            <option value="loop">Loop</option>
            <option value="retry">Retry</option>
            <option value="human_approval">Human Approval</option>
            <option value="subagent">SubAgent</option>
          </select>

          <button className="av-btn av-btn-primary" onClick={handleAddNode} style={{ fontSize: 11, padding: '2px 8px' }}>
            + Add Node
          </button>

          {selectedId && (
            <button className="av-btn av-btn-ghost" onClick={handleRemoveSelectedNode} style={{ fontSize: 11, padding: '2px 8px', color: '#EF4444' }}>
              Delete Selected
            </button>
          )}

          <button className="av-btn av-btn-ghost" onClick={handleUndo} disabled={!canUndo} style={{ fontSize: 11, padding: '2px 6px' }}>
            ↩ Undo
          </button>
          <button className="av-btn av-btn-ghost" onClick={handleRedo} disabled={!canRedo} style={{ fontSize: 11, padding: '2px 6px' }}>
            ↪ Redo
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {nodes.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--av-text-muted)', fontSize: 12 }}>
            <span>No workflow nodes loaded</span>
            <span style={{ fontSize: 11, opacity: 0.7, marginTop: 4 }}>Open an agent.yaml file in the editor to visualize its graph</span>
          </div>
        ) : (
          <svg width="100%" height="100%" viewBox="0 0 720 420">
            <g transform={`scale(${zoom})`}>
              {edges.map((edge, i) => {
                const fp = layout.get(edge.from);
                const tp = layout.get(edge.to);
                if (!fp || !tp) return null;
                return <GraphEdgeComponent key={i} fromPos={fp} toPos={tp} animated={!!edge.animated} />;
              })}

              {nodes.map((node) => {
                const pos = layout.get(node.id);
                if (!pos) return null;
                return (
                  <GraphNodeComponent
                    key={node.id}
                    node={node}
                    x={pos.x}
                    y={pos.y}
                    selected={selectedId === node.id}
                    onClick={() => setSelectedId(node.id === selectedId ? null : node.id)}
                  />
                );
              })}
            </g>
          </svg>
        )}
      </div>

      {/* Footer / Hash Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '5px 12px',
          borderTop: '1px solid var(--av-border)',
          background: 'var(--av-bg-panel)',
          fontSize: 10,
          fontFamily: 'monospace',
          color: 'var(--av-text-muted)',
        }}
      >
        <span>Nodes: {nodes.length} | Edges: {edges.length}</span>
        {manifestHash && <span>Hash: {manifestHash.slice(0, 18)}...</span>}
      </div>
    </div>
  );
};

export default AgentGraph;

