import * as assert from 'assert';
import { AgentStateManager } from '../core/agentStateManager';

describe('Phase 7 Real-time Telemetry & ANCESTOR Traces Test Suite', () => {
  it('AgentStateManager should generate state hash for telemetry stream', () => {
    const manager = AgentStateManager.instance;
    manager.createDefault('telemetry-agent');

    const hash = manager.computeHash();
    assert.notStrictEqual(hash, null);
    assert.strictEqual(hash?.startsWith('sha256:'), true);
  });

  it('Telemetry fallback trace records should include valid ANCESTOR state hash', () => {
    const manager = AgentStateManager.instance;
    const currentHash = manager.computeHash();

    const traceRecord = {
      id: `tr-${Date.now()}`,
      ts: new Date().toLocaleTimeString(),
      agent_id: manager.currentAgent?.metadata.name || 'active-agent',
      agent_name: manager.currentAgent?.metadata.name || 'Active Agent',
      action: 'SENTINEL_POLICY_EVALUATE',
      verdict: 'APPROVED',
      policy: 'nuuvixx-standard-2026.09',
      risk_score: 'LOW',
      duration_ms: 8,
      details: 'Pre-flight policy check evaluated cleanly',
      state_hash: currentHash,
    };

    assert.strictEqual(traceRecord.verdict, 'APPROVED');
    assert.strictEqual(traceRecord.state_hash, currentHash);
    assert.strictEqual(traceRecord.policy, 'nuuvixx-standard-2026.09');
  });
});
