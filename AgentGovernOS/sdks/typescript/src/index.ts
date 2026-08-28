import axios, { AxiosInstance } from 'axios';
import {
  ActionRequest,
  EvaluationResult,
  LogRequest,
  DelegationRequest,
  DelegationResult,
  TrustScoreResult
} from './types';

export class AgentGovernClient {
  private client: AxiosInstance;

  constructor(baseURL: string = "http://127.0.0.1:8000", apiKey?: string) {
    this.client = axios.create({
      baseURL,
      headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}
    });
  }

  async evaluateAction(request: ActionRequest): Promise<EvaluationResult> {
    const response = await this.client.post('/api/v1/sentinel/evaluate', request);
    return response.data;
  }

  async logDecision(request: LogRequest): Promise<any> {
    const response = await this.client.post('/api/v1/audit/log', request);
    return response.data;
  }

  async requestDelegation(request: DelegationRequest): Promise<DelegationResult> {
    const response = await this.client.post('/api/v1/a2a/attest', request);
    return response.data;
  }

  async getTrustScore(agentId: string): Promise<TrustScoreResult> {
    const response = await this.client.get(`/api/v1/pulse/trust/${agentId}`);
    return response.data;
  }
}

export * from './types';
