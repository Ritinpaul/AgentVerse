import { YamlParser } from '../src/parser/yaml-parser';
import { YamlSerializer } from '../src/serializer/yaml-serializer';
import { ManifestHasher } from '../src/versioning/manifest-hash';
import { DAGValidator } from '../src/graph/dag';
import { SecretDetector } from '../src/validator/secret-detector';
import {
  CommandHistory,
  UpdateModelConfigCommand,
  AddToolCommand,
  AddWorkflowNodeCommand,
} from '../src/commands/Command';
import { createDefaultAgent } from '../src/model/agent';

describe('AgentCore Test Suite', () => {
  const sampleValidYaml = `
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: test-research-agent
  version: 1.0.0
  description: "Test research agent"
model:
  provider: anthropic
  name: claude-3-5-sonnet
  temperature: 0.5
instructions: "You are a test assistant."
tools:
  - id: web-search
    type: mcp
    server: search-server
    tool: google_search
    risk: low
workflow:
  nodes:
    - id: node-1
      type: llm
    - id: node-2
      type: tool
      toolRef: web-search
  edges:
    - from: node-1
      to: node-2
policies:
  policyBundle: "standard-v1"
budget:
  maxCostPerRun: 0.50
runtime:
  sandbox: docker
  egress: restricted
observability:
  traceLevel: standard
  redactPrompts: true
env:
  API_KEY:
    secretRef: "secret://org/api_key"
`;

  test('YamlParser should successfully parse and validate a canonical manifest', () => {
    const res = YamlParser.parse(sampleValidYaml);
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.value.metadata.name).toBe('test-research-agent');
      expect(res.value.model.provider).toBe('anthropic');
      expect(res.value.tools.length).toBe(1);
    }
  });

  test('SecretDetector should catch raw API keys in text', () => {
    const leakedYaml = sampleValidYaml + '\n  RAW_KEY: sk-12345678901234567890123456789012';
    const errors = SecretDetector.scanRawText(leakedYaml);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0].code).toBe('SECRET_IN_MANIFEST');
  });

  test('DAGValidator should detect cycles in workflow edges', () => {
    const cyclicGraph = {
      nodes: [
        { id: 'a', type: 'llm' as const },
        { id: 'b', type: 'llm' as const },
      ],
      edges: [
        { from: 'a', to: 'b' },
        { from: 'b', to: 'a' },
      ],
    };
    const errors = DAGValidator.validateGraph(cyclicGraph);
    expect(errors.some((e) => e.code === 'CYCLE_DETECTED')).toBe(true);
  });

  test('ManifestHasher should produce deterministic sha256 hashes', () => {
    const agent = createDefaultAgent('my-agent');
    const hash1 = ManifestHasher.computeHash(agent);
    const hash2 = ManifestHasher.computeHash(agent);
    expect(hash1).toBe(hash2);
    expect(hash1.startsWith('sha256:')).toBe(true);
  });

  test('CommandHistory should execute commands and support undo/redo', () => {
    const agent = createDefaultAgent('history-agent');
    const history = new CommandHistory();

    expect(agent.model.temperature).toBe(0.7);

    // Apply update model temperature command
    const updated = history.apply(new UpdateModelConfigCommand({ temperature: 0.2 }), agent);
    expect(updated.model.temperature).toBe(0.2);
    expect(history.canUndo()).toBe(true);

    // Undo command
    const undone = history.undo(updated);
    expect(undone).not.toBeNull();
    if (undone) {
      expect(undone.model.temperature).toBe(0.7);
    }
  });
});
