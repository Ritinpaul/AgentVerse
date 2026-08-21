/**
 * packages/agent-core/src/serializer/yaml-serializer.ts
 *
 * Serializes canonical Agent object back into formatted YAML text.
 */

import * as yaml from 'yaml';
import { Agent } from '../model/agent';

export class YamlSerializer {
  /**
   * Converts Agent object to clean, human-readable YAML string.
   */
  public static serialize(agent: Agent): string {
    const doc = new yaml.Document(agent);
    return doc.toString({
      indent: 2,
      lineWidth: 100,
    });
  }
}
