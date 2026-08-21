/**
 * packages/agent-core/src/validator/secret-detector.ts
 *
 * Scans Agent manifest objects and raw YAML strings for accidental inclusion
 * of hardcoded secrets or API keys.
 */

import { ValidationError, ErrorCodes } from '../model/validation';
import { isSecretRef } from '../model/agent';

const SECRET_PATTERNS = [
  { name: 'OpenAI API Key', regex: /sk-[a-zA-Z0-9]{32,}/ },
  { name: 'Anthropic API Key', regex: /sk-ant-[a-zA-Z0-9\-_]{32,}/ },
  { name: 'GitHub Personal Access Token', regex: /ghp_[a-zA-Z0-9]{36}/ },
  { name: 'GitHub OAuth Token', regex: /gho_[a-zA-Z0-9]{36}/ },
  { name: 'AWS Access Key ID', regex: /(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}/ },
  { name: 'Generic Private Key', regex: /-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----/ },
  { name: 'Slack Bot Token', regex: /xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}/ },
  { name: 'Stripe Secret Key', regex: /sk_live_[0-9a-zA-Z]{24}/ },
];

export class SecretDetector {
  /**
   * Scans a raw YAML string for hardcoded secret patterns.
   */
  public static scanRawText(text: string): ValidationError[] {
    const errors: ValidationError[] = [];

    for (const pattern of SECRET_PATTERNS) {
      if (pattern.regex.test(text)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.SECRET_IN_MANIFEST,
          message: `Raw secret detected in manifest text: ${pattern.name}. Use secretRef format instead (e.g. secret://org/key).`,
        });
      }
    }

    return errors;
  }

  /**
   * Scans env object of parsed Agent manifest to ensure all values are either secretRef objects
   * or non-sensitive plain configuration strings.
   */
  public static scanEnvObject(envObj?: Record<string, unknown>): ValidationError[] {
    const errors: ValidationError[] = [];
    if (!envObj) return errors;

    for (const [key, value] of Object.entries(envObj)) {
      if (typeof value === 'string') {
        // If string value matches known secret keys or contains token pattern
        if (
          key.toUpperCase().includes('TOKEN') ||
          key.toUpperCase().includes('SECRET') ||
          key.toUpperCase().includes('PASSWORD') ||
          key.toUpperCase().includes('API_KEY')
        ) {
          if (!value.startsWith('secret://')) {
            errors.push({
              severity: 'error',
              code: ErrorCodes.SECRET_IN_MANIFEST,
              path: `env.${key}`,
              message: `Environment variable '${key}' appears sensitive. Store values using secretRef pointer: { secretRef: "secret://org/..." }`,
              value,
            });
          }
        }
      } else if (isSecretRef(value)) {
        if (!value.secretRef.startsWith('secret://')) {
          errors.push({
            severity: 'error',
            code: ErrorCodes.INVALID_SECRET_REF,
            path: `env.${key}.secretRef`,
            message: `Secret reference '${value.secretRef}' must start with 'secret://'`,
            value: value.secretRef,
          });
        }
      }
    }

    return errors;
  }
}
