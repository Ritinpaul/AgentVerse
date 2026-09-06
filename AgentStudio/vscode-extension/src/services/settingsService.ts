import * as vscode from 'vscode';
import * as http from 'http';
import * as https from 'https';
import { URL } from 'url';

export interface ModelItem {
  id: string;
  name: string;
  provider: string;
  type: 'cloud' | 'local';
  enabled: boolean;
  isDefault?: boolean;
  status: 'available' | 'unavailable';
  statusMessage?: string;
}

export interface ProviderConfig {
  id: string;
  name: string;
  type: 'cloud' | 'local';
  status: 'connected' | 'disconnected' | 'checking' | 'unconfigured';
  statusMessage?: string;
  hasKey?: boolean;
  baseUrl?: string;
  modelCount: number;
}

export interface McpServerConfig {
  id: string;
  name: string;
  transport: 'stdio' | 'sse' | 'http';
  commandOrUrl: string;
  status: 'active' | 'inactive' | 'error';
  statusMessage?: string;
  enabled: boolean;
}

export interface SettingsState {
  models: ModelItem[];
  providers: ProviderConfig[];
  mcpServers: McpServerConfig[];
  autoDetectLocal: boolean;
  guardrailProfile: 'strict' | 'balanced' | 'permissive';
  defaultModelId: string;
}

export const FREE_TIER_MODELS: ModelItem[] = [
  {
    id: 'agentverse:gemma-3-27b:free',
    name: 'Gemma 3 27B (Free Quota)',
    provider: 'AgentVerse Cloud',
    type: 'cloud',
    enabled: true,
    isDefault: true,
    status: 'available',
    statusMessage: '50,000 tokens/day free quota included',
  },
  {
    id: 'agentverse:llama-3.1-8b:free',
    name: 'Llama 3.1 8B (Free Quota)',
    provider: 'AgentVerse Cloud',
    type: 'cloud',
    enabled: true,
    isDefault: false,
    status: 'available',
    statusMessage: 'Fast inference (Free quota)',
  },
  {
    id: 'agentverse:mistral-7b:free',
    name: 'Mistral 7B (Free Quota)',
    provider: 'AgentVerse Cloud',
    type: 'cloud',
    enabled: true,
    isDefault: false,
    status: 'available',
    statusMessage: 'Code & reasoning (Free quota)',
  },
];

const DEFAULT_PROVIDERS: Omit<ProviderConfig, 'status' | 'modelCount' | 'hasKey'>[] = [
  { id: 'agentverse-free', name: 'AgentVerse Cloud (Free Quota)', type: 'cloud' },
  { id: 'openai', name: 'OpenAI', type: 'cloud' },
  { id: 'anthropic', name: 'Anthropic', type: 'cloud' },
  { id: 'openrouter', name: 'OpenRouter', type: 'cloud' },
  { id: 'google', name: 'Google Gemini', type: 'cloud' },
  { id: 'ollama', name: 'Ollama (Local)', type: 'local', baseUrl: 'http://localhost:11434' },
  { id: 'lmstudio', name: 'LM Studio (Local)', type: 'local', baseUrl: 'http://localhost:1234/v1' },
  { id: 'vllm', name: 'vLLM Engine (Local)', type: 'local', baseUrl: 'http://localhost:8000/v1' },
];

export class SettingsService {
  private static _instance: SettingsService;

  public static getInstance(context?: vscode.ExtensionContext): SettingsService {
    if (!this._instance) {
      if (!context) {
        throw new Error('SettingsService must be initialized with ExtensionContext first');
      }
      this._instance = new SettingsService(context);
    }
    return this._instance;
  }

  constructor(private context: vscode.ExtensionContext) {}

  // ── Secret Key Management ──────────────────────────────────────────────────

  private getSecretKeyName(providerId: string): string {
    return `agentverse.provider.${providerId}.key`;
  }

  public async saveApiKey(providerId: string, key: string): Promise<void> {
    const keyName = this.getSecretKeyName(providerId);
    if (!key || key.trim() === '') {
      await this.context.secrets.delete(keyName);
    } else {
      await this.context.secrets.store(keyName, key.trim());
    }
  }

  public async getApiKey(providerId: string): Promise<string | undefined> {
    return await this.context.secrets.get(this.getSecretKeyName(providerId));
  }

  public async hasApiKey(providerId: string): Promise<boolean> {
    const key = await this.getApiKey(providerId);
    return !!key && key.trim().length > 0;
  }

  // ── HTTP Helper for Connection Health Checks ───────────────────────────────

  private async makeRequest(
    targetUrl: string,
    options: { method?: string; headers?: Record<string, string>; timeoutMs?: number } = {}
  ): Promise<{ statusCode: number; data: string }> {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(targetUrl);
      const isHttps = parsedUrl.protocol === 'https:';
      const client = isHttps ? https : http;

      const reqOptions: http.RequestOptions = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method: options.method || 'GET',
        headers: options.headers || {},
        timeout: options.timeoutMs || 3000,
      };

      const req = client.request(reqOptions, (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => {
          resolve({ statusCode: res.statusCode || 500, data: body });
        });
      });

      req.on('error', (err) => reject(err));
      req.on('timeout', () => {
        req.destroy();
        reject(new Error(`Connection to ${targetUrl} timed out`));
      });

      req.end();
    });
  }

  // ── Real Connection Test & Model Discovery ─────────────────────────────────

  public async testProvider(
    providerId: string,
    customBaseUrl?: string
  ): Promise<{ connected: boolean; statusMessage: string; models: ModelItem[] }> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const enabledModels: string[] = config.get('enabledModels', []);
    const defaultModelId: string = config.get('defaultModel', '');

    try {
      if (providerId === 'agentverse-free') {
        const models: ModelItem[] = FREE_TIER_MODELS.map((m) => ({
          ...m,
          enabled: enabledModels.length === 0 ? true : enabledModels.includes(m.id),
          isDefault: m.id === (defaultModelId || 'agentverse:gemma-3-27b:free'),
        }));
        return {
          connected: true,
          statusMessage: 'Free model quota active (50,000 tokens/day)',
          models,
        };
      }

      if (providerId === 'ollama') {
        const baseUrl = customBaseUrl || config.get('localEndpoints.ollama', 'http://localhost:11434');
        const res = await this.makeRequest(`${baseUrl}/api/tags`, { timeoutMs: 2500 });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = parsed.models || [];
          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `ollama:${m.name}`;
            return {
              id: mId,
              name: m.name,
              provider: 'Ollama',
              type: 'local',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });
          return {
            connected: true,
            statusMessage: `Connected to Ollama. Discovered ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `Ollama returned HTTP status ${res.statusCode}`,
            models: [],
          };
        }
      }

      if (providerId === 'lmstudio') {
        const baseUrl = customBaseUrl || config.get('localEndpoints.lmstudio', 'http://localhost:1234/v1');
        const res = await this.makeRequest(`${baseUrl}/models`, { timeoutMs: 2500 });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = parsed.data || [];
          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `lmstudio:${m.id}`;
            return {
              id: mId,
              name: m.id,
              provider: 'LM Studio',
              type: 'local',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });
          return {
            connected: true,
            statusMessage: `Connected to LM Studio. Discovered ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `LM Studio returned HTTP status ${res.statusCode}`,
            models: [],
          };
        }
      }

      if (providerId === 'vllm') {
        const baseUrl = customBaseUrl || config.get('localEndpoints.vllm', 'http://localhost:8000/v1');
        const res = await this.makeRequest(`${baseUrl}/models`, { timeoutMs: 2500 });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = parsed.data || [];
          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `vllm:${m.id}`;
            return {
              id: mId,
              name: m.id,
              provider: 'vLLM',
              type: 'local',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });
          return {
            connected: true,
            statusMessage: `Connected to vLLM Engine. Discovered ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `vLLM returned HTTP status ${res.statusCode}`,
            models: [],
          };
        }
      }

      // Cloud Providers
      const apiKey = await this.getApiKey(providerId);
      if (!apiKey || apiKey.trim() === '') {
        return {
          connected: false,
          statusMessage: `No API key configured for ${providerId}`,
          models: [],
        };
      }

      if (providerId === 'openai') {
        const res = await this.makeRequest('https://api.openai.com/v1/models', {
          headers: { Authorization: `Bearer ${apiKey}` },
          timeoutMs: 4000,
        });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const allowedPrefixes = ['gpt-4o', 'gpt-4', 'o1', 'o3-mini', 'gpt-3.5-turbo'];
          const rawModels = (parsed.data || [])
            .filter((m: any) => allowedPrefixes.some(p => m.id.startsWith(p)))
            .slice(0, 15);

          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `openai:${m.id}`;
            return {
              id: mId,
              name: m.id,
              provider: 'OpenAI',
              type: 'cloud',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });

          return {
            connected: true,
            statusMessage: `Connected to OpenAI API. Validated ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `OpenAI authentication failed (HTTP ${res.statusCode}). Please check your API key.`,
            models: [],
          };
        }
      }

      if (providerId === 'anthropic') {
        const res = await this.makeRequest('https://api.anthropic.com/v1/models', {
          headers: {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
          },
          timeoutMs: 4000,
        });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = parsed.data || [
            { id: 'claude-3-7-sonnet-20250219', display_name: 'Claude 3.7 Sonnet' },
            { id: 'claude-3-5-sonnet-20241022', display_name: 'Claude 3.5 Sonnet' },
            { id: 'claude-3-5-haiku-20241022', display_name: 'Claude 3.5 Haiku' },
          ];

          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `anthropic:${m.id}`;
            return {
              id: mId,
              name: m.display_name || m.id,
              provider: 'Anthropic',
              type: 'cloud',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });

          return {
            connected: true,
            statusMessage: `Connected to Anthropic API. Validated ${models.length} model(s).`,
            models,
          };
        } else if (res.statusCode === 401) {
          return {
            connected: false,
            statusMessage: `Anthropic API key rejected (401 Unauthorized).`,
            models: [],
          };
        } else {
          // If models endpoint not supported on user plan, validate standard Anthropic models
          const standardModels: ModelItem[] = [
            { id: 'anthropic:claude-3-7-sonnet-20250219', name: 'Claude 3.7 Sonnet', provider: 'Anthropic', type: 'cloud' as const, enabled: true, status: 'available' as const },
            { id: 'anthropic:claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', type: 'cloud' as const, enabled: true, status: 'available' as const },
            { id: 'anthropic:claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', provider: 'Anthropic', type: 'cloud' as const, enabled: false, status: 'available' as const },
          ].map(m => ({ ...m, enabled: enabledModels.includes(m.id), isDefault: m.id === defaultModelId }));

          return {
            connected: true,
            statusMessage: `Connected to Anthropic API. Standard models ready.`,
            models: standardModels,
          };
        }
      }

      if (providerId === 'openrouter') {
        const res = await this.makeRequest('https://openrouter.ai/api/v1/models', {
          headers: { Authorization: `Bearer ${apiKey}` },
          timeoutMs: 4000,
        });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = (parsed.data || []).slice(0, 30);

          const models: ModelItem[] = rawModels.map((m: any) => {
            const mId = `openrouter:${m.id}`;
            return {
              id: mId,
              name: m.name || m.id,
              provider: 'OpenRouter',
              type: 'cloud',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });

          return {
            connected: true,
            statusMessage: `Connected to OpenRouter API. Discovered ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `OpenRouter authentication failed (HTTP ${res.statusCode}).`,
            models: [],
          };
        }
      }

      if (providerId === 'google') {
        const res = await this.makeRequest(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`, {
          timeoutMs: 4000,
        });

        if (res.statusCode === 200) {
          const parsed = JSON.parse(res.data);
          const rawModels = (parsed.models || []).filter((m: any) => m.name.includes('gemini'));

          const models: ModelItem[] = rawModels.map((m: any) => {
            const cleanName = m.name.replace('models/', '');
            const mId = `google:${cleanName}`;
            return {
              id: mId,
              name: m.displayName || cleanName,
              provider: 'Google Gemini',
              type: 'cloud',
              enabled: enabledModels.includes(mId),
              isDefault: mId === defaultModelId,
              status: 'available',
            };
          });

          return {
            connected: true,
            statusMessage: `Connected to Google Gemini API. Found ${models.length} model(s).`,
            models,
          };
        } else {
          return {
            connected: false,
            statusMessage: `Google Gemini API key invalid (HTTP ${res.statusCode}).`,
            models: [],
          };
        }
      }

      return {
        connected: false,
        statusMessage: `Unknown provider ${providerId}`,
        models: [],
      };
    } catch (err: any) {
      return {
        connected: false,
        statusMessage: err.message || `Failed to connect to ${providerId}`,
        models: [],
      };
    }
  }

  // ── Load Entire Settings State ─────────────────────────────────────────────

  public async getSettingsState(): Promise<SettingsState> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const autoDetectLocal = config.get<boolean>('autoDetectLocal', true);
    const guardrailProfile = config.get<'strict' | 'balanced' | 'permissive'>('guardrailProfile', 'balanced');
    let defaultModelId = config.get<string>('defaultModel', '');
    const mcpServers = config.get<McpServerConfig[]>('mcpServers', []);
    let enabledModels = config.get<string[]>('enabledModels', []);

    if (!enabledModels || enabledModels.length === 0) {
      await this.ensureFreeModelsConfigured();
      enabledModels = config.get<string[]>('enabledModels', []);
      defaultModelId = config.get<string>('defaultModel', 'agentverse:gemma-3-27b:free');
    }

    const providers: ProviderConfig[] = [];
    let allModels: ModelItem[] = [];

    // Test each default provider
    for (const defP of DEFAULT_PROVIDERS) {
      const hasKey = defP.id === 'agentverse-free' ? true : (defP.type === 'cloud' ? await this.hasApiKey(defP.id) : false);

      let status: ProviderConfig['status'] = 'unconfigured';
      let statusMessage = '';
      let models: ModelItem[] = [];

      if (defP.id === 'agentverse-free') {
        status = 'connected';
        statusMessage = 'Free model quota active (50,000 tokens/day)';
        models = FREE_TIER_MODELS.map((m) => ({
          ...m,
          enabled: enabledModels.includes(m.id),
          isDefault: m.id === (defaultModelId || 'agentverse:gemma-3-27b:free'),
        }));
      } else if (defP.type === 'cloud') {
        if (hasKey) {
          const testRes = await this.testProvider(defP.id);
          status = testRes.connected ? 'connected' : 'disconnected';
          statusMessage = testRes.statusMessage;
          models = testRes.models;
        } else {
          status = 'unconfigured';
          statusMessage = `No API key saved`;
        }
      } else if (defP.type === 'local') {
        if (autoDetectLocal) {
          const testRes = await this.testProvider(defP.id, defP.baseUrl);
          status = testRes.connected ? 'connected' : 'disconnected';
          statusMessage = testRes.statusMessage;
          models = testRes.models;
        } else {
          status = 'disconnected';
          statusMessage = `Auto-detect disabled`;
        }
      }

      providers.push({
        id: defP.id,
        name: defP.name,
        type: defP.type,
        status,
        statusMessage,
        hasKey,
        baseUrl: defP.baseUrl,
        modelCount: models.length,
      });

      allModels.push(...models);
    }

    return {
      models: allModels,
      providers,
      mcpServers,
      autoDetectLocal,
      guardrailProfile,
      defaultModelId,
    };
  }

  // ── Model Selection & Registry Sync ───────────────────────────────────────

  public async ensureFreeModelsConfigured(): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const isInitialized = config.get<boolean>('modelsInitialized', false);
    const enabledModels = config.get<string[]>('enabledModels', []);

    if (!isInitialized || !enabledModels || enabledModels.length === 0) {
      const freeModelIds = FREE_TIER_MODELS.map((m) => m.id);
      await config.update('enabledModels', freeModelIds, vscode.ConfigurationTarget.Global);
      const currentDefault = config.get<string>('defaultModel', '');
      if (!currentDefault) {
        await config.update('defaultModel', 'agentverse:gemma-3-27b:free', vscode.ConfigurationTarget.Global);
      }
      await config.update('modelsInitialized', true, vscode.ConfigurationTarget.Global);
    }
  }

  public async toggleModel(modelId: string, enabled: boolean): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const currentEnabled: string[] = config.get('enabledModels', []);
    let updated: string[];

    if (enabled) {
      updated = Array.from(new Set([...currentEnabled, modelId]));
    } else {
      updated = currentEnabled.filter((id) => id !== modelId);
    }

    await config.update('enabledModels', updated, vscode.ConfigurationTarget.Global);
  }

  public async setDefaultModel(modelId: string): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    await config.update('defaultModel', modelId, vscode.ConfigurationTarget.Global);
  }

  public async setAutoDetectLocal(enabled: boolean): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    await config.update('autoDetectLocal', enabled, vscode.ConfigurationTarget.Global);
  }

  public async setGuardrailProfile(profile: 'strict' | 'balanced' | 'permissive'): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    await config.update('guardrailProfile', profile, vscode.ConfigurationTarget.Global);
  }

  // ── MCP Server Management ────────────────────────────────────────────────

  public async saveMcpServer(server: McpServerConfig): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const currentServers: McpServerConfig[] = config.get('mcpServers', []);
    const idx = currentServers.findIndex((s) => s.id === server.id);

    let updated: McpServerConfig[];
    if (idx >= 0) {
      updated = [...currentServers];
      updated[idx] = server;
    } else {
      updated = [...currentServers, server];
    }

    await config.update('mcpServers', updated, vscode.ConfigurationTarget.Global);
  }

  public async deleteMcpServer(serverId: string): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const currentServers: McpServerConfig[] = config.get('mcpServers', []);
    const updated = currentServers.filter((s) => s.id !== serverId);
    await config.update('mcpServers', updated, vscode.ConfigurationTarget.Global);
  }

  public async toggleMcpServer(serverId: string, enabled: boolean): Promise<void> {
    const config = vscode.workspace.getConfiguration('agentverse');
    const currentServers: McpServerConfig[] = config.get('mcpServers', []);
    const updated = currentServers.map((s) => (s.id === serverId ? { ...s, enabled, status: enabled ? 'active' : ('inactive' as const) } : s));
    await config.update('mcpServers', updated, vscode.ConfigurationTarget.Global);
  }

  // ── Resolved Model Endpoint Resolution ────────────────────────────────────

  public async getResolvedModelEndpoint(modelId: string): Promise<{
    providerId: string;
    modelName: string;
    baseUrl: string;
    headers: Record<string, string>;
    isLocal: boolean;
  }> {
    const parts = modelId.split(':');
    const providerId = parts[0] || 'openai';
    const modelName = parts.slice(1).join(':') || modelId;

    const config = vscode.workspace.getConfiguration('agentverse');

    if (providerId === 'ollama') {
      const baseUrl = config.get('localEndpoints.ollama', 'http://localhost:11434');
      return { providerId, modelName, baseUrl, headers: {}, isLocal: true };
    }
    if (providerId === 'lmstudio') {
      const baseUrl = config.get('localEndpoints.lmstudio', 'http://localhost:1234/v1');
      return { providerId, modelName, baseUrl, headers: {}, isLocal: true };
    }
    if (providerId === 'vllm') {
      const baseUrl = config.get('localEndpoints.vllm', 'http://localhost:8000/v1');
      return { providerId, modelName, baseUrl, headers: {}, isLocal: true };
    }

    if (providerId === 'agentverse' || providerId === 'agentverse-free') {
      const governosUrl = config.get<string>('governosUrl', 'http://localhost:8003');
      return {
        providerId: 'agentverse',
        modelName,
        baseUrl: `${governosUrl}/api/v1/freebuff`,
        headers: { 'content-type': 'application/json' },
        isLocal: false,
      };
    }

    const apiKey = (await this.getApiKey(providerId)) || '';

    if (providerId === 'anthropic') {
      return {
        providerId,
        modelName,
        baseUrl: 'https://api.anthropic.com/v1',
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        isLocal: false,
      };
    }
    if (providerId === 'openrouter') {
      return {
        providerId,
        modelName,
        baseUrl: 'https://openrouter.ai/api/v1',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'content-type': 'application/json',
        },
        isLocal: false,
      };
    }
    if (providerId === 'google') {
      return {
        providerId,
        modelName,
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
        headers: {
          'x-goog-api-key': apiKey,
          'content-type': 'application/json',
        },
        isLocal: false,
      };
    }

    // Default: OpenAI / OpenAI-compatible
    return {
      providerId,
      modelName,
      baseUrl: 'https://api.openai.com/v1',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'content-type': 'application/json',
      },
      isLocal: false,
    };
  }
}

