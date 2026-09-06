/**
 * src/core/yamlAssistant.ts
 *
 * YAML Assistant for manifest validation, powered by @agentstudio/agent-core.
 */

import { YamlParser, ValidationError as CoreValidationError } from '@agentstudio/agent-core';

export interface ValidationError {
  path: string;
  message: string;
  severity: 'error' | 'warning';
}

export class YamlAssistant {
  public static validateManifest(yamlContent: string): ValidationError[] {
    const parseResult = YamlParser.parse(yamlContent);

    if (!parseResult.ok) {
      return parseResult.errors.map((e: CoreValidationError) => ({
        path: e.path || 'root',
        message: e.message,
        severity: e.severity === 'error' ? 'error' : 'warning',
      }));
    }

    // Additional UI advisory checks
    const agent = parseResult.value;
    const warnings: ValidationError[] = [];

    if (!agent.budget || (agent.budget.maxCostPerRun === undefined && agent.budget.dailyLimit === undefined)) {
      warnings.push({
        path: 'budget',
        message: 'No cost budget configured in manifest (e.g. maxCostPerRun: 0.25)',
        severity: 'warning',
      });
    }

    if (!agent.policies || !agent.policies.policyBundle) {
      warnings.push({
        path: 'policies',
        message: 'No governance policyBundle linked in manifest',
        severity: 'warning',
      });
    }

    return warnings;
  }
}
