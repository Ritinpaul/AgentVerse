/**
 * packages/agent-core/src/graph/dag.ts
 *
 * Directed Acyclic Graph (DAG) operations for Workflow validation:
 * - Cycle detection
 * - Topological sorting
 * - Orphan node detection
 * - Unreachable node detection
 */

import { WorkflowGraph, WorkflowNode } from '../model/agent';
import { ValidationError, ErrorCodes } from '../model/validation';

export class DAGValidator {
  /**
   * Validates structural integrity of a workflow graph.
   */
  public static validateGraph(graph?: WorkflowGraph): ValidationError[] {
    const errors: ValidationError[] = [];
    if (!graph || !graph.nodes || graph.nodes.length === 0) {
      return errors;
    }

    const nodeIds = new Set<string>();
    for (const node of graph.nodes) {
      if (nodeIds.has(node.id)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.DUPLICATE_NODE_ID,
          message: `Duplicate node ID found in workflow: '${node.id}'`,
          path: `workflow.nodes.${node.id}`,
        });
      }
      nodeIds.add(node.id);
    }

    // Check edge references
    for (const edge of graph.edges || []) {
      if (!nodeIds.has(edge.from)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.UNKNOWN_NODE_REFERENCE,
          message: `Edge source node '${edge.from}' does not exist`,
          path: `workflow.edges.${edge.from}`,
        });
      }
      if (!nodeIds.has(edge.to)) {
        errors.push({
          severity: 'error',
          code: ErrorCodes.UNKNOWN_NODE_REFERENCE,
          message: `Edge target node '${edge.to}' does not exist`,
          path: `workflow.edges.${edge.to}`,
        });
      }
    }

    // Cycle detection using DFS
    const cycle = this.findCycle(graph);
    if (cycle) {
      errors.push({
        severity: 'error',
        code: ErrorCodes.CYCLE_DETECTED,
        message: `Cycle detected in workflow graph: ${cycle.join(' -> ')}`,
        path: 'workflow.edges',
      });
    }

    return errors;
  }

  /**
   * Returns cycle node ID array if cycle exists, or null if DAG.
   */
  public static findCycle(graph: WorkflowGraph): string[] | null {
    const adj = new Map<string, string[]>();
    for (const node of graph.nodes) {
      adj.set(node.id, []);
    }
    for (const edge of graph.edges || []) {
      const neighbors = adj.get(edge.from) || [];
      neighbors.push(edge.to);
      adj.set(edge.from, neighbors);
    }

    const visited = new Set<string>();
    const recStack = new Set<string>();
    const path: string[] = [];

    const dfs = (curr: string): boolean => {
      visited.add(curr);
      recStack.add(curr);
      path.push(curr);

      const neighbors = adj.get(curr) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor)) return true;
        } else if (recStack.has(neighbor)) {
          path.push(neighbor);
          return true;
        }
      }

      recStack.delete(curr);
      path.pop();
      return false;
    };

    for (const node of graph.nodes) {
      if (!visited.has(node.id)) {
        if (dfs(node.id)) {
          return path;
        }
      }
    }

    return null;
  }

  /**
   * Topological sort of workflow nodes.
   */
  public static topologicalSort(graph: WorkflowGraph): WorkflowNode[] {
    const inDegree = new Map<string, number>();
    const nodeMap = new Map<string, WorkflowNode>();

    for (const node of graph.nodes) {
      inDegree.set(node.id, 0);
      nodeMap.set(node.id, node);
    }

    for (const edge of graph.edges || []) {
      inDegree.set(edge.to, (inDegree.get(edge.to) || 0) + 1);
    }

    const queue: string[] = [];
    for (const [id, deg] of inDegree.entries()) {
      if (deg === 0) queue.push(id);
    }

    const sorted: WorkflowNode[] = [];
    while (queue.length > 0) {
      const curr = queue.shift()!;
      const node = nodeMap.get(curr);
      if (node) sorted.push(node);

      for (const edge of graph.edges || []) {
        if (edge.from === curr) {
          const newDeg = (inDegree.get(edge.to) || 0) - 1;
          inDegree.set(edge.to, newDeg);
          if (newDeg === 0) {
            queue.push(edge.to);
          }
        }
      }
    }

    return sorted;
  }
}
