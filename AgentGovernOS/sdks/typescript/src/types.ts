export interface ActionRequest {
  agent_id: string;
  intent: string;
  context?: Record<string, any>;
  caller_id?: string;
}

export interface EvaluationResult {
  verdict: "ALLOW" | "BLOCK" | "ESCALATE";
  reason: string;
  risk_score: number;
}

export interface LogRequest {
  agent_id: string;
  intent: string;
  verdict: string;
  context?: Record<string, any>;
}

export interface DelegationRequest {
  source_agent: string;
  target_agent: string;
  intent: string;
}

export interface DelegationResult {
  allowed: boolean;
  reason: string;
}

export interface TrustScoreResult {
  agent_id: string;
  score: number;
  status: string;
}
