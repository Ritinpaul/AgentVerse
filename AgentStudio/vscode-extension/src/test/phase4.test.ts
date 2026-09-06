import * as assert from 'assert';
import { YamlParser, UpdateModelConfigCommand, AddToolCommand } from '@agentstudio/agent-core';
import { AgentStateManager } from '../core/agentStateManager';

describe('Phase 4 Copilot & Local Validation Test Suite', () => {
  const invalidYaml = `
apiVersion: agentstudio/v1
kind: Agent
metadata:
  name: Invalid_Name_Format
  version: 1.0.0
model:
  provider: invalid_provider
`;

  it('Local Validation should report schema validation errors for invalid manifest', () => {
    const res = YamlParser.parse(invalidYaml);
    assert.strictEqual(res.ok, false);
    if (!res.ok) {
      assert.strictEqual(res.errors.length > 0, true);
    }
  });

  it('Copilot Proposal execution should apply commands safely through AgentStateManager', () => {
    const manager = AgentStateManager.instance;
    manager.createDefault('copilot-test-agent');

    // Simulate proposed commands from Copilot LLM
    const proposedCommands = [
      new UpdateModelConfigCommand({ provider: 'anthropic', name: 'claude-3-5-sonnet' }),
      new AddToolCommand({ id: 'web-search', type: 'mcp', server: 'mcp-search', tool: 'search', risk: 'medium' }),
    ];

    for (const cmd of proposedCommands) {
      manager.applyCommand(cmd);
    }

    const current = manager.currentAgent;
    assert.notStrictEqual(current, null);
    assert.strictEqual(current?.model.provider, 'anthropic');
    assert.strictEqual(current?.model.name, 'claude-3-5-sonnet');
    assert.strictEqual(current?.tools.length, 1);
    assert.strictEqual(current?.tools[0].id, 'web-search');

    // Verify sha256 manifest hash calculation after proposal application
    const hash = manager.computeHash();
    assert.notStrictEqual(hash, null);
    assert.strictEqual(hash?.startsWith('sha256:'), true);
  });
});
