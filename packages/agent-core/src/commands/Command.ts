/**
 * packages/agent-core/src/commands/Command.ts
 *
 * Command pattern implementation for state mutation, Undo/Redo history,
 * and Copilot proposal preview diffing.
 */

import { Agent, ModelConfig, ToolReference, WorkflowNode, WorkflowEdge, BudgetConfig, RuntimeConfig } from '../model/agent';

export interface Command {
  execute(agent: Agent): Agent;
  undo(agent: Agent): Agent;
  describe(): string;
}

export class CommandHistory {
  private past: Command[] = [];
  private future: Command[] = [];

  public apply(cmd: Command, current: Agent): Agent {
    const next = cmd.execute(current);
    this.past.push(cmd);
    this.future = []; // Clear redo stack on new command
    return next;
  }

  public undo(current: Agent): Agent | null {
    const cmd = this.past.pop();
    if (!cmd) return null;
    this.future.push(cmd);
    return cmd.undo(current);
  }

  public redo(current: Agent): Agent | null {
    const cmd = this.future.pop();
    if (!cmd) return null;
    this.past.push(cmd);
    return cmd.execute(current);
  }

  public canUndo(): boolean {
    return this.past.length > 0;
  }

  public canRedo(): boolean {
    return this.future.length > 0;
  }

  public getHistoryDescriptions(): string[] {
    return this.past.map((c) => c.describe());
  }

  public clear(): void {
    this.past = [];
    this.future = [];
  }
}

// ─── Concrete Commands ───────────────────────────────────────────────────────

export class UpdateModelConfigCommand implements Command {
  private prevConfig!: ModelConfig;

  constructor(private readonly newConfig: Partial<ModelConfig>) {}

  execute(agent: Agent): Agent {
    this.prevConfig = { ...agent.model };
    return {
      ...agent,
      model: {
        ...agent.model,
        ...this.newConfig,
      },
    };
  }

  undo(agent: Agent): Agent {
    return {
      ...agent,
      model: this.prevConfig,
    };
  }

  describe(): string {
    return `Update Model Configuration (${Object.keys(this.newConfig).join(', ')})`;
  }
}

export class UpdateInstructionsCommand implements Command {
  private prevInstructions!: string;

  constructor(private readonly newInstructions: string) {}

  execute(agent: Agent): Agent {
    this.prevInstructions = agent.instructions;
    return {
      ...agent,
      instructions: this.newInstructions,
    };
  }

  undo(agent: Agent): Agent {
    return {
      ...agent,
      instructions: this.prevInstructions,
    };
  }

  describe(): string {
    return `Update System Prompt Instructions`;
  }
}

export class AddToolCommand implements Command {
  constructor(private readonly tool: ToolReference) {}

  execute(agent: Agent): Agent {
    const existing = agent.tools || [];
    if (existing.some((t) => t.id === this.tool.id)) {
      return agent;
    }
    return {
      ...agent,
      tools: [...existing, this.tool],
    };
  }

  undo(agent: Agent): Agent {
    return {
      ...agent,
      tools: (agent.tools || []).filter((t) => t.id !== this.tool.id),
    };
  }

  describe(): string {
    return `Add Tool '${this.tool.id}' (${this.tool.type})`;
  }
}

export class RemoveToolCommand implements Command {
  private removedTool?: ToolReference;

  constructor(private readonly toolId: string) {}

  execute(agent: Agent): Agent {
    this.removedTool = (agent.tools || []).find((t) => t.id === this.toolId);
    return {
      ...agent,
      tools: (agent.tools || []).filter((t) => t.id !== this.toolId),
    };
  }

  undo(agent: Agent): Agent {
    if (!this.removedTool) return agent;
    return {
      ...agent,
      tools: [...(agent.tools || []), this.removedTool],
    };
  }

  describe(): string {
    return `Remove Tool '${this.toolId}'`;
  }
}

export class AddWorkflowNodeCommand implements Command {
  constructor(private readonly node: WorkflowNode) {}

  execute(agent: Agent): Agent {
    const currentGraph = agent.workflow || { nodes: [], edges: [] };
    if (currentGraph.nodes.some((n) => n.id === this.node.id)) {
      return agent;
    }
    return {
      ...agent,
      workflow: {
        ...currentGraph,
        nodes: [...currentGraph.nodes, this.node],
      },
    };
  }

  undo(agent: Agent): Agent {
    if (!agent.workflow) return agent;
    return {
      ...agent,
      workflow: {
        ...agent.workflow,
        nodes: agent.workflow.nodes.filter((n) => n.id !== this.node.id),
      },
    };
  }

  describe(): string {
    return `Add Workflow Node '${this.node.id}' (${this.node.type})`;
  }
}

export class RemoveWorkflowNodeCommand implements Command {
  private removedNode?: WorkflowNode;
  private removedEdges: WorkflowEdge[] = [];

  constructor(private readonly nodeId: string) {}

  execute(agent: Agent): Agent {
    if (!agent.workflow) return agent;
    this.removedNode = agent.workflow.nodes.find((n) => n.id === this.nodeId);
    this.removedEdges = agent.workflow.edges.filter(
      (e) => e.from === this.nodeId || e.to === this.nodeId
    );

    return {
      ...agent,
      workflow: {
        nodes: agent.workflow.nodes.filter((n) => n.id !== this.nodeId),
        edges: agent.workflow.edges.filter(
          (e) => e.from !== this.nodeId && e.to !== this.nodeId
        ),
      },
    };
  }

  undo(agent: Agent): Agent {
    if (!agent.workflow || !this.removedNode) return agent;
    return {
      ...agent,
      workflow: {
        nodes: [...agent.workflow.nodes, this.removedNode],
        edges: [...agent.workflow.edges, ...this.removedEdges],
      },
    };
  }

  describe(): string {
    return `Remove Workflow Node '${this.nodeId}'`;
  }
}

export class UpdateBudgetCommand implements Command {
  private prevBudget!: BudgetConfig;

  constructor(private readonly newBudget: Partial<BudgetConfig>) {}

  execute(agent: Agent): Agent {
    this.prevBudget = { ...agent.budget };
    return {
      ...agent,
      budget: {
        ...agent.budget,
        ...this.newBudget,
      },
    };
  }

  undo(agent: Agent): Agent {
    return {
      ...agent,
      budget: this.prevBudget,
    };
  }

  describe(): string {
    return `Update Budget Limits`;
  }
}
