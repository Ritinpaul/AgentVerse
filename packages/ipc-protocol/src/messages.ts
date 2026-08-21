/**
 * packages/ipc-protocol/src/messages.ts
 *
 * Strongly-typed IPC message definitions for Webview <-> Extension Host communication.
 */

import { Agent, ValidationError } from '@agentstudio/agent-core';

export type MessageType =
  // Outgoing (Webview -> Extension Host)
  | 'AGENT_COMMAND'           // Apply a command to the Agent model
  | 'REQUEST_VALIDATE'        // Request local schema/semantic validation
  | 'REQUEST_PLAN'            // Request backend plan & cost estimate
  | 'START_RUN'               // Request execution start
  | 'CANCEL_RUN'              // Request run cancellation
  | 'APPROVE_TOOL'            // Resolve tool approval (user clicked approve)
  | 'REJECT_TOOL'             // Resolve tool approval (user clicked reject)
  | 'COPILOT_PROMPT'          // Send prompt to Copilot
  | 'ACCEPT_COPILOT_PROPOSAL' // Accept proposed commands
  | 'REJECT_COPILOT_PROPOSAL' // Reject proposed commands
  | 'GET_WORKSPACE_AGENTS'
  | 'GET_REMOTE_DEBUG_AGENTS'
  | 'GET_AGENT_TRACE'
  | 'GET_GIT_STATUS'
  | 'GIT_COMMIT'
  | 'GET_POLICIES'
  | 'SAVE_POLICIES'
  | 'GET_AUDIT_LOGS'
  | 'GET_AUTH_STATUS'
  | 'SSO_LOGIN'
  | 'SSO_LOGOUT'
  // Incoming (Extension Host -> Webview)
  | 'AGENT_STATE'             // Full Agent model update
  | 'VALIDATION_RESULT'       // Validation errors list
  | 'PLAN_RESULT'             // Backend plan & estimate response
  | 'RUN_EVENT'               // Real-time run event stream
  | 'TRACE_EVENT'             // Trace event update
  | 'COPILOT_PROPOSAL'        // Proposed commands (not applied yet)
  | 'WORKSPACE_AGENTS_RESPONSE'
  | 'REMOTE_DEBUG_AGENTS_RESPONSE'
  | 'AGENT_TRACE_RESPONSE'
  | 'GIT_STATUS_RESPONSE'
  | 'POLICIES_RESPONSE'
  | 'AUDIT_LOGS_RESPONSE'
  | 'AUTH_STATUS_RESPONSE'
  | 'ERROR';

export interface IPCMessage<T = unknown> {
  id: string;             // UUID or timestamp-based ID
  type: MessageType;
  payload: T;
  timestamp: string;      // ISO string
}

// Payload Specific Interfaces
export interface AgentCommandPayload {
  commandType: string;
  args: Record<string, unknown>;
}

export interface ValidationResultPayload {
  errors: ValidationError[];
  isValid: boolean;
}

export interface RunEventPayload {
  runId: string;
  seq: number;
  eventType: string;
  data: Record<string, unknown>;
}

export interface CopilotPromptPayload {
  prompt: string;
  contextNodeId?: string;
}

export interface CopilotProposalPayload {
  proposalId: string;
  summary: string;
  commands: AgentCommandPayload[];
  diffYaml?: string;
}
