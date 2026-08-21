/**
 * packages/agent-core/src/versioning/manifest-hash.ts
 *
 * Computes deterministic content-addressed sha256 hash of an Agent object.
 */

import { createHash } from 'crypto';
import { Agent } from '../model/agent';

export class ManifestHasher {
  /**
   * Serializes an Agent object into canonical JSON (sorted keys, compact separators)
   * and returns its sha256 hash string prefixed with "sha256:".
   */
  public static computeHash(agent: Agent): string {
    const canonicalJson = this.toCanonicalJson(agent);
    const hashHex = createHash('sha256').update(canonicalJson, 'utf8').digest('hex');
    return `sha256:${hashHex}`;
  }

  /**
   * Deterministic recursive canonical JSON stringifier (sorts dictionary keys alphabetically).
   */
  public static toCanonicalJson(obj: unknown): string {
    if (obj === null || typeof obj !== 'object') {
      return JSON.stringify(obj);
    }

    if (Array.isArray(obj)) {
      const items = obj.map((item) => this.toCanonicalJson(item));
      return `[${items.join(',')}]`;
    }

    const record = obj as Record<string, unknown>;
    const sortedKeys = Object.keys(record).sort();
    const pairs: string[] = [];

    for (const key of sortedKeys) {
      const val = record[key];
      if (val !== undefined) {
        pairs.push(`${JSON.stringify(key)}:${this.toCanonicalJson(val)}`);
      }
    }

    return `{${pairs.join(',')}}`;
  }
}
