/**
 * packages/agent-core/src/validator/schema-validator.ts
 *
 * Validates parsed JavaScript objects against the canonical agent.yaml.schema.json using Ajv.
 */

import Ajv, { ValidateFunction } from 'ajv';
import addFormats from 'ajv-formats';
import { ValidationError, ErrorCodes } from '../model/validation';

// Load embedded canonical schema directly to avoid runtime IO dependency
import canonicalSchema from '../../../agent-schema/agent.yaml.schema.json';

export class SchemaValidator {
  private ajv: Ajv;
  private validatorFunc: ValidateFunction;

  constructor() {
    this.ajv = new Ajv({ allErrors: true, useDefaults: true, strict: false });
    addFormats(this.ajv);
    this.validatorFunc = this.ajv.compile(canonicalSchema);
  }

  /**
   * Validates a parsed object against canonical JSON Schema v1.
   */
  public validate(data: unknown): ValidationError[] {
    const valid = this.validatorFunc(data);
    if (valid || !this.validatorFunc.errors) {
      return [];
    }

    return this.validatorFunc.errors.map((ajvErr: any) => {
      const instancePath = ajvErr.instancePath
        ? ajvErr.instancePath.replace(/^\//, '').replace(/\//g, '.')
        : 'root';

      return {
        severity: 'error',
        code: ErrorCodes.SCHEMA_VALIDATION_FAILED,
        message: `${instancePath}: ${ajvErr.message}`,
        path: instancePath,
        value: ajvErr.data,
      };
    });
  }
}
