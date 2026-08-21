/**
 * packages/agent-core/src/model/agent.ts
 *
 * The canonical Agent domain model — the spine of AgentStudio.
 * Every layer (YAML editor, Graph, Inspector, Copilot, backend, runner)
 * operates on this typed representation. YAML is persistence only.
 */

// ─── Primitives ─────────────────────────────────────────────────────────────

export type SandboxProfile = 'none' | 'docker' | 'gvisor' | 'firecracker';
export type TraceLevel = 'minimal' | 'standard' | 'debug';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type EgressPolicy = 'open' | 'restricted' | 'none';
export type ApprovalPolicy = 'required' | 'log' | 'auto';
export type BlockPolicy = 'block' | 'required';
export type MemoryType = 'ephemeral' | 'persistent' | 'semantic';
export type TriggerType = 'webhook' | 'schedule';
export type ToolType = 'mcp' | 'http' | 'native';
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

// ─── Secret References ───────────────────────────────────────────────────────

/** Never a raw value. Always a reference pointer. */
export interface SecretRef {
  secretRef: string; // e.g. "secret://org/github/token"
}

export type EnvValue = string | SecretRef;

export function isSecretRef(value: unknown): value is SecretRef {
  return (
    typeof value === 'object' &&
    value !== null &&
    'secretRef' in value &&
    typeof (value as SecretRef).secretRef === 'string'
  );
}

// ─── Model Configuration ─────────────────────────────────────────────────────

export interface ModelFallback {
  provider: string;
  name: string;
}

export interface ModelRouting {
  maxCostPerRun?: number;
  maxLatencyMs?: number;
  dataResidency?: string;
}

export interface ModelConfig {
  provider: 'openai' | 'anthropic' | 'google' | 'ollama' | 'openrouter';
  name: string;
  temperature?: number;
  maxTokens?: number;
  fallbacks?: ModelFallback[];
  routing?: ModelRouting;
}

// ─── Tools ───────────────────────────────────────────────────────────────────

export interface ToolPermissions {
  egress?: string[];
}

export interface ToolReference {
  id: string;
  type: ToolType;
  server?: string;   // MCP server name
  tool?: string;     // specific tool within MCP server
  url?: string;      // HTTP tool endpoint
  version?: string;
  risk?: RiskLevel;
  permissions?: ToolPermissions;
}

// ─── Workflow ─────────────────────────────────────────────────────────────────

export interface WorkflowNode {
  id: string;
  type: NodeType;
  label?: string;
  toolRef?: string;   // references ToolReference.id (for 'tool' nodes)
  config?: Record<string, unknown>;
}

export interface WorkflowEdge {
  from: string;
  to: string;
  condition?: string; // for conditional edges
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

// ─── Policy ──────────────────────────────────────────────────────────────────

export interface ApprovalConfig {
  highRiskToolCalls: ApprovalPolicy;
  criticalRiskToolCalls: BlockPolicy;
}

export interface PolicyConfig {
  policyBundle?: string; // e.g. "nuuvixx-standard-2026.09"
  approval?: ApprovalConfig;
}

// ─── Budget ──────────────────────────────────────────────────────────────────

export interface BudgetConfig {
  maxCostPerRun?: number;
  maxTokensPerRun?: number;
  maxRunsPerDay?: number;
  dailyLimit?: number;
}

// ─── Runtime ─────────────────────────────────────────────────────────────────

export interface RuntimeConfig {
  sandbox: SandboxProfile;
  egress: EgressPolicy;
  timeoutSeconds?: number;
  maxToolCalls?: number;
  maxDepth?: number;
  maxOutputBytes?: number;
  maxConcurrentRuns?: number;
}

// ─── Memory ──────────────────────────────────────────────────────────────────

export interface MemoryConfig {
  type: MemoryType;
  maxTokens?: number;
}

// ─── Observability ───────────────────────────────────────────────────────────

export interface ObservabilityConfig {
  traceLevel: TraceLevel;
  redactPrompts?: boolean;
}

// ─── Triggers ────────────────────────────────────────────────────────────────

export interface Trigger {
  type: TriggerType;
  cron?: string; // for schedule triggers
}

// ─── Sandbox Tests ───────────────────────────────────────────────────────────

export interface SandboxTest {
  name: string;
  input: string;
  expectedBehavior: string;
}

// ─── Agent Metadata ──────────────────────────────────────────────────────────

export interface AgentMetadata {
  apiVersion: 'agentstudio/v1';
  kind: 'Agent';
  name: string;
  version: string;
  description?: string;
  framework?: string;
  labels?: Record<string, string>;
}

// ─── The Agent — Single Source of Truth ─────────────────────────────────────

/**
 * The canonical Agent domain model.
 *
 * Rules:
 * 1. This is the internal representation — never serialized directly to the UI.
 * 2. YAML is derived from this model via the serializer.
 * 3. The graph is derived from this model via a graph adapter.
 * 4. The inspector form is derived from this model.
 * 5. All mutations go through the Command system, not direct mutation.
 */
export interface Agent {
  metadata: AgentMetadata;
  model: ModelConfig;
  instructions: string;
  tools: ToolReference[];
  workflow?: WorkflowGraph;
  policies: PolicyConfig;
  budget: BudgetConfig;
  runtime: RuntimeConfig;
  memory?: MemoryConfig;
  observability: ObservabilityConfig;
  env?: Record<string, EnvValue>;
  triggers?: Trigger[];
  sandboxTests?: SandboxTest[];
}

// ─── Factory / Default ───────────────────────────────────────────────────────

export function createDefaultAgent(name: string): Agent {
  return {
    metadata: {
      apiVersion: 'agentstudio/v1',
      kind: 'Agent',
      name,
      version: '0.1.0',
    },
    model: {
      provider: 'openai',
      name: 'gpt-4o',
      temperature: 0.7,
    },
    instructions: 'You are a helpful assistant.',
    tools: [],
    policies: {
      approval: {
        highRiskToolCalls: 'required',
        criticalRiskToolCalls: 'block',
      },
    },
    budget: {
      maxCostPerRun: 0.25,
    },
    runtime: {
      sandbox: 'docker',
      egress: 'restricted',
      timeoutSeconds: 120,
      maxToolCalls: 20,
      maxDepth: 4,
    },
    observability: {
      traceLevel: 'standard',
      redactPrompts: true,
    },
  };
}
