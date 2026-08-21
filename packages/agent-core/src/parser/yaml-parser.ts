/**
 * packages/agent-core/src/parser/yaml-parser.ts
 *
 * Parses raw YAML manifest string into a validated canonical Agent object.
 */

import * as yaml from 'yaml';
import { Agent } from '../model/agent';
import { Result, ok, err, ValidationError, ErrorCodes } from '../model/validation';
import { SchemaValidator } from '../validator/schema-validator';
import { SemanticValidator } from '../validator/semantic-validator';
import { SecretDetector } from '../validator/secret-detector';

export class YamlParser {
  private static schemaValidator = new SchemaValidator();

  /**
   * Parses raw YAML into canonical Agent object.
   */
  public static parse(yamlContent: string): Result<Agent, ValidationError[]> {
    const errors: ValidationError[] = [];

    // 1. Scan raw text for secret patterns
    const secretTextErrors = SecretDetector.scanRawText(yamlContent);
    errors.push(...secretTextErrors);

    // 2. Parse YAML syntax
    let parsed: unknown;
    try {
      parsed = yaml.parse(yamlContent);
    } catch (e: any) {
      errors.push({
        severity: 'error',
        code: ErrorCodes.INVALID_YAML,
        message: `YAML syntax error: ${e.message || e}`,
      });
      return err(errors);
    }

    if (!parsed || typeof parsed !== 'object') {
      errors.push({
        severity: 'error',
        code: ErrorCodes.INVALID_YAML,
        message: 'YAML manifest must evaluate to an object',
      });
      return err(errors);
    }

    // 3. Normalize legacy flat schema fields to canonical v1 structure if needed
    const normalized = this.normalizeLegacySchema(parsed as Record<string, unknown>);

    // 4. Schema validation
    const schemaErrors = this.schemaValidator.validate(normalized);
    errors.push(...schemaErrors);

    if (errors.some((e) => e.severity === 'error')) {
      return err(errors);
    }

    const agent = (normalized as unknown) as Agent;

    // 5. Semantic validation
    const semanticErrors = SemanticValidator.validate(agent);
    errors.push(...semanticErrors);

    if (errors.some((e) => e.severity === 'error')) {
      return err(errors);
    }

    return ok(agent);
  }

  /**
   * Normalizes older flat v0 manifests (which missed apiVersion/kind/metadata wrapper) into canonical v1 schema.
   */
  private static normalizeLegacySchema(raw: Record<string, unknown>): Record<string, unknown> {
    const copy = { ...raw };

    if (copy.metadata && typeof copy.metadata === 'object') {
      const metaObj = { ...(copy.metadata as Record<string, unknown>) };
      if (metaObj.apiVersion && !copy.apiVersion) {
        copy.apiVersion = metaObj.apiVersion;
        delete metaObj.apiVersion;
      }
      if (metaObj.kind && !copy.kind) {
        copy.kind = metaObj.kind;
        delete metaObj.kind;
      }
      copy.metadata = metaObj;
    }

    if (!copy.apiVersion) {
      copy.apiVersion = 'agentstudio/v1';
    }
    if (!copy.kind) {
      copy.kind = 'Agent';
    }

    if (!copy.metadata && (copy.name || copy.version)) {
      copy.metadata = {
        apiVersion: 'agentstudio/v1',
        kind: 'Agent',
        name: copy.name || 'unnamed-agent',
        version: copy.version || '1.0.0',
        description: copy.description || '',
        framework: copy.framework || 'native_agentos',
      };
      delete copy.name;
      delete copy.version;
      delete copy.description;
      delete copy.framework;
    }

    if (!copy.instructions && copy.systemPrompt) {
      copy.instructions = copy.systemPrompt;
      delete copy.systemPrompt;
    }

    return copy;
  }
}
