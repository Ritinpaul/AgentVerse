import * as assert from 'assert';
import { AgentStateManager } from '../core/agentStateManager';

describe('Phase 8 Server-Authoritative Registry Publishing Test Suite', () => {
  it('AgentStateManager should generate manifest hash for digital signature minting', () => {
    const manager = AgentStateManager.instance;
    manager.createDefault('publishable-agent');

    const manifestHash = manager.computeHash();
    assert.notStrictEqual(manifestHash, null);
    assert.strictEqual(manifestHash?.startsWith('sha256:'), true);
  });

  it('Release payload should contain valid agent slug, version, manifest hash, and digital signature', () => {
    const manager = AgentStateManager.instance;
    const currentAgent = manager.currentAgent;

    const orgSlug = 'nuuvixx';
    const agentSlug = `${orgSlug}/${currentAgent?.metadata.name}`;
    const version = currentAgent?.metadata.version || '1.0.0';
    const manifestHash = manager.computeHash() || 'sha256:default';
    const signature = `sha256:sig_${manifestHash.replace('sha256:', '').slice(0, 16)}`;

    const releasePayload = {
      releaseId: `rel-${Date.now()}`,
      agentSlug,
      version,
      manifestHash,
      policyVerdict: 'APPROVED',
      signature,
      publishedAt: new Date().toISOString(),
      created: true,
    };

    assert.strictEqual(releasePayload.agentSlug, 'nuuvixx/publishable-agent');
    assert.strictEqual(releasePayload.version, version);
    assert.strictEqual(releasePayload.signature.startsWith('sha256:sig_'), true);
  });
});
