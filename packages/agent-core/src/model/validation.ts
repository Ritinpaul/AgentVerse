/**
 * packages/agent-core/src/model/validation.ts
 *
 * Shared result/error types for validation across parser, validator, and commands.
 */

export type ValidationSeverity = 'error' | 'warning' | 'info';

export interface ValidationError {
  severity: ValidationSeverity;
  code: string;
  message: string;
  path?: string;      // JSON pointer, e.g. "model.temperature"
  value?: unknown;    // the offending value
}

export type Result<T, E = ValidationError[]> =
  | { ok: true; value: T }
  | { ok: false; errors: E };

export function ok<T>(value: T): Result<T> {
  return { ok: true, value };
}

export function err<T>(errors: ValidationError[]): Result<T> {
  return { ok: false, errors };
}

export function isOk<T>(result: Result<T>): result is { ok: true; value: T } {
  return result.ok;
}

// ─── Error Codes ─────────────────────────────────────────────────────────────

export const ErrorCodes = {
  // Schema
  INVALID_YAML: 'INVALID_YAML',
  SCHEMA_VALIDATION_FAILED: 'SCHEMA_VALIDATION_FAILED',
  MISSING_REQUIRED_FIELD: 'MISSING_REQUIRED_FIELD',
  INVALID_FIELD_VALUE: 'INVALID_FIELD_VALUE',
  UNKNOWN_FIELD: 'UNKNOWN_FIELD',

  // Secrets
  SECRET_IN_MANIFEST: 'SECRET_IN_MANIFEST',       // raw secret value detected
  INVALID_SECRET_REF: 'INVALID_SECRET_REF',       // malformed secretRef

  // Semantic
  UNKNOWN_TOOL_REFERENCE: 'UNKNOWN_TOOL_REFERENCE',
  UNKNOWN_NODE_REFERENCE: 'UNKNOWN_NODE_REFERENCE',
  CYCLE_DETECTED: 'CYCLE_DETECTED',
  ORPHANED_NODE: 'ORPHANED_NODE',
  INVALID_EDGE: 'INVALID_EDGE',
  DUPLICATE_NODE_ID: 'DUPLICATE_NODE_ID',
  DUPLICATE_TOOL_ID: 'DUPLICATE_TOOL_ID',

  // Budget
  BUDGET_LIMIT_INVALID: 'BUDGET_LIMIT_INVALID',

  // Security
  EGRESS_NOT_ALLOWED: 'EGRESS_NOT_ALLOWED',
  DANGEROUS_TOOL_REQUIRES_HIGH_SANDBOX: 'DANGEROUS_TOOL_REQUIRES_HIGH_SANDBOX',
  PROMPT_INJECTION_HEURISTIC: 'PROMPT_INJECTION_HEURISTIC',
} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];
