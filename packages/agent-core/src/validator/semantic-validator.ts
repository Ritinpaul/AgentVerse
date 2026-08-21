/**
 * packages/agent-core/src/validator/semantic-validator.ts
 *
 * Semantic validation of Agent objects (cross-field logic, referential integrity).
 */

import { Agent } from '../model/agent';
import { ValidationError, ErrorCodes } from '../model/validation';
import { DAGValidator } from '../graph/dag';
import { SecretDetector } from './secret-detector';

export class SemanticValidator {
  /**
   * Performs full semantic validation on an Agent object.
   */
  public static validate(agent: Agent): ValidationError[] {
    const errors: ValidationError[] = [];

    // 1. Tool ID duplicates & references
    const toolIds = new Set<string>();
    for (const tool of agent.tools || []) {
      if (toolIds.has(tool.id)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.DUPLICATE_TOOL_ID,
          message: `Duplicate tool ID '${tool.id}' in tools array`,
          path: `tools.${tool.id}`,
        });
      }
      toolIds.add(tool.id);

      // Check MCP server/tool specification
      if (tool.type === 'mcp' && (!tool.server || !tool.tool)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.MISSING_REQUIRED_FIELD,
          message: `MCP tool '${tool.id}' requires both 'server' and 'tool' parameters`,
          path: `tools.${tool.id}`,
        });
      }

      // Check HTTP URL specification
      if (tool.type === 'http' && !tool.url) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.MISSING_REQUIRED_FIELD,
          message: `HTTP tool '${tool.id}' requires 'url' parameter`,
          path: `tools.${tool.id}`,
        });
      }
    }

    // 2. Workflow node references
    if (agent.workflow) {
      for (const node of agent.workflow.nodes || []) {
        if (node.type === 'tool') {
          if (!node.toolRef) {
            errors.push({
              severity: 'error',
              code: ErrorCodes.MISSING_REQUIRED_FIELD,
              message: `Workflow node '${node.id}' of type 'tool' requires 'toolRef' parameter`,
              path: `workflow.nodes.${node.id}`,
            });
          } else if (!toolIds.has(node.toolRef)) {
            errors.push({
              severity: 'error',
              code: ErrorCodes.UNKNOWN_TOOL_REFERENCE,
              message: `Workflow node '${node.id}' references unknown tool '${node.toolRef}'`,
              path: `workflow.nodes.${node.id}.toolRef`,
              value: node.toolRef,
            });
          }
        }
      }

      // Graph structural integrity & DAG check
      const graphErrors = DAGValidator.validateGraph(agent.workflow);
      errors.push(...graphErrors);
    }

    // 3. Secret leaks in env
    const secretErrors = SecretDetector.scanEnvObject(agent.env as Record<string, unknown>);
    errors.push(...secretErrors);

    // 4. Secret leaks in instructions
    const promptSecretErrors = SecretDetector.scanRawText(agent.instructions || '');
    errors.push(...promptSecretErrors);

    // 5. Budget limits check
    if (agent.budget) {
      if (agent.budget.maxCostPerRun !== undefined && agent.budget.maxCostPerRun <= 0) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.BUDGET_LIMIT_INVALID,
          message: `maxCostPerRun must be greater than 0`,
          path: 'budget.maxCostPerRun',
          value: agent.budget.maxCostPerRun,
        });
      }
    }

    // 6. Security rule: High/Critical risk tools require approval or block
    for (const tool of agent.tools || []) {
      if (tool.risk === 'critical') {
        const policy = agent.policies?.approval?.criticalRiskToolCalls;
        if (policy !== 'block' && policy !== 'required') {
          errors.push({
            severity: 'warning',
            code: ErrorCodes.EGRESS_NOT_ALLOWED,
            message: `Tool '${tool.id}' has critical risk. Policy should require approval or block execution.`,
            path: `policies.approval.criticalRiskToolCalls`,
          });
        }
      }
    }

    return errors;
  }
}
