import * as assert from 'assert';
import { AgentStateManager } from '../core/agentStateManager';
import { LocalPolicyAdvisor } from '../core/embeddedPolicyEngine';
import { LocalRBACHint } from '../core/embeddedRBACEngine';
import { YamlAssistant } from '../core/yamlAssistant';
import { UpdateModelConfigCommand } from '@agentstudio/agent-core';

describe('Phase 2 Extension Host Refactor Test Suite', () => {
  const validYaml = `
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: phase2-test-agent
  version: 1.0.0
model:
  provider: openai
  name: gpt-4o
  temperature: 0.7
instructions: "Test instructions"
tools: []
policies:
  policyBundle: "test-bundle"
budget:
  maxCostPerRun: 0.25
runtime:
  sandbox: docker
  egress: restricted
observability:
  traceLevel: standard
  redactPrompts: true
`;

  it('AgentStateManager should load YAML and manage AST state & commands', () => {
    const manager = AgentStateManager.instance;
    const res = manager.loadFromYaml(validYaml);

    assert.strictEqual(res.ok, true);
    assert.notStrictEqual(manager.currentAgent, null);
    assert.strictEqual(manager.currentAgent?.metadata.name, 'phase2-test-agent');

    const hashBefore = manager.computeHash();
    assert.notStrictEqual(hashBefore, null);
    assert.strictEqual(hashBefore?.startsWith('sha256:'), true);

    // Apply command
    const updated = manager.applyCommand(new UpdateModelConfigCommand({ temperature: 0.1 }));
    assert.strictEqual(updated?.model.temperature, 0.1);
    assert.strictEqual(manager.history.canUndo(), true);

    // Undo command
    const undone = manager.undo();
    assert.strictEqual(undone?.model.temperature, 0.7);
  });

  it('YamlAssistant should validate manifests using @agentstudio/agent-core', () => {
    const warnings = YamlAssistant.validateManifest(validYaml);
    assert.strictEqual(Array.isArray(warnings), true);
    const errors = warnings.filter((w) => w.severity === 'error');
    assert.strictEqual(errors.length, 0);
  });

  it('LocalPolicyAdvisor and LocalRBACHint should be explicitly advisory (not authoritative)', () => {
    const policyAdvisor = new LocalPolicyAdvisor();
    const rbacHint = new LocalRBACHint();

    assert.strictEqual(policyAdvisor.isAuthoritative, false);
    assert.strictEqual(rbacHint.isAuthoritative, false);

    const policy = policyAdvisor.getPolicy();
    assert.strictEqual(policy.isAdvisoryOnly, true);
  });
});
