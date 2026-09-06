import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import { URL } from 'url';
import { SettingsService } from './settingsService';
import { AuthService } from './authService';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export type KeySource = 'byok' | 'freebuff';

export interface StreamChunk {
  type: 'text_delta' | 'done' | 'error' | 'budget_update';
  delta?: string;
  tokensUsed?: number;
  error?: string;
  /** Only present on type='budget_update' */
  budget?: { used: number; remaining: number; limit: number };
}

// ── GovernOS FreeBuff proxy endpoint ──────────────────────────────────────
const GOVERNOS_BASE = vscode.workspace
  .getConfiguration('agentverse')
  .get<string>('governosUrl', 'http://localhost:8003');

const FREEBUFF_ENDPOINT = `${GOVERNOS_BASE}/api/v1/freebuff/chat`;

// ── Free model hints for FreeBuff tier ─────────────────────────────────────
const FREE_MODEL_HINTS: Record<string, string> = {
  default: 'google/gemma-3-27b-it:free',
  fast: 'meta-llama/llama-3.1-8b-instruct:free',
  code: 'mistralai/mistral-7b-instruct:free',
  reasoning: 'google/gemma-3-27b-it:free',
};

function toFreeHint(modelId: string): string {
  if (modelId.includes('llama')) { return FREE_MODEL_HINTS.fast; }
  if (modelId.includes('code') || modelId.includes('starcoder') || modelId.includes('mistral')) { return FREE_MODEL_HINTS.code; }
  return FREE_MODEL_HINTS.default;
}

// ── ModelRouter ────────────────────────────────────────────────────────────

export class ModelRouter {
  private static _instance: ModelRouter;

  private constructor(private readonly context: vscode.ExtensionContext) {}

  public static getInstance(context: vscode.ExtensionContext): ModelRouter {
    if (!ModelRouter._instance) {
      ModelRouter._instance = new ModelRouter(context);
    }
    return ModelRouter._instance;
  }

  /** Returns 'byok' if the user has a key for this model's provider, else 'freebuff'. */
  public async getKeySource(modelId: string): Promise<KeySource> {
    const settings = SettingsService.getInstance();
    const providerId = modelId.split(':')[0] ?? 'openai';

    // Local providers never use FreeBuff
    if (['ollama', 'lmstudio', 'vllm'].includes(providerId)) {
      return 'byok';
    }

    const hasKey = await settings.hasApiKey(providerId);
    return hasKey ? 'byok' : 'freebuff';
  }

  /**
   * Routes a chat completion request and returns an async generator of StreamChunks.
   * BYOK: calls the provider API directly from extension host (key never leaves the machine).
   * FreeBuff: calls GovernOS proxy (our key, our budget enforcement).
   */
  public async *route(
    modelId: string,
    messages: ChatMessage[],
  ): AsyncGenerator<StreamChunk> {
    const source = await this.getKeySource(modelId);

    if (source === 'byok') {
      yield* this._directCall(modelId, messages);
    } else {
      yield* this._freebuffCall(modelId, messages);
    }
  }

  // ── BYOK: direct provider call ─────────────────────────────────────────

  private async *_directCall(
    modelId: string,
    messages: ChatMessage[],
  ): AsyncGenerator<StreamChunk> {
    const settings = SettingsService.getInstance();
    let endpoint: Awaited<ReturnType<SettingsService['getResolvedModelEndpoint']>>;

    try {
      endpoint = await settings.getResolvedModelEndpoint(modelId);
    } catch (err: any) {
      yield { type: 'error', error: `Cannot resolve endpoint for ${modelId}: ${err.message}` };
      return;
    }

    const providerId = endpoint.providerId;
    const isAnthropic = providerId === 'anthropic';

    // Build request body
    const body = isAnthropic
      ? {
          model: endpoint.modelName,
          messages,
          max_tokens: 4096,
          stream: true,
        }
      : {
          model: endpoint.modelName,
          messages,
          stream: true,
        };

    const chatPath = isAnthropic ? '/messages' : '/chat/completions';
    const requestUrl = `${endpoint.baseUrl}${chatPath}`;

    yield* this._streamRequest(requestUrl, endpoint.headers, body, isAnthropic);
  }

  // ── FreeBuff: GovernOS proxy call ─────────────────────────────────────

  private async *_freebuffCall(
    modelId: string,
    messages: ChatMessage[],
  ): AsyncGenerator<StreamChunk> {
    const auth = AuthService.getInstance(this.context);
    const session = await auth.getSession();

    if (!session) {
      yield {
        type: 'error',
        error: 'Not signed in. Sign in to use free models, or add a BYOK API key in Settings.',
      };
      return;
    }

    const body = {
      model_hint: toFreeHint(modelId),
      messages,
    };

    const headers: Record<string, string> = {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    };

    yield* this._streamRequest(FREEBUFF_ENDPOINT, headers, body, false, true);
  }

  // ── Shared SSE streaming helper ────────────────────────────────────────

  private _streamRequest(
    targetUrl: string,
    headers: Record<string, string>,
    body: object,
    isAnthropic: boolean,
    isFreeBuff: boolean = false,
  ): AsyncGenerator<StreamChunk> {
    return this._doStreamRequest(targetUrl, headers, body, isAnthropic, isFreeBuff);
  }

  private async *_doStreamRequest(
    targetUrl: string,
    headers: Record<string, string>,
    body: object,
    isAnthropic: boolean,
    isFreeBuff: boolean,
  ): AsyncGenerator<StreamChunk> {
    const payload = JSON.stringify(body);
    const parsed = new URL(targetUrl);
    const isHttps = parsed.protocol === 'https:';
    const client = isHttps ? https : http;

    const chunks: Buffer[] = [];
    let resolve: ((v: void) => void) | undefined;
    let reject: ((e: Error) => void) | undefined;
    const pending: StreamChunk[] = [];
    let done = false;
    let waitPromise: Promise<void> | undefined;
    let leftover = '';

    const enqueue = (chunk: StreamChunk) => {
      pending.push(chunk);
      resolve?.();
    };

    const req = client.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || (isHttps ? 443 : 80),
        path: parsed.pathname + parsed.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload),
          Accept: 'text/event-stream',
          ...headers,
        },
      },
      (res) => {
        if (res.statusCode === 429) {
          // Budget exceeded
          let body = '';
          res.on('data', (d: Buffer) => (body += d.toString()));
          res.on('end', () => {
            try {
              const parsed = JSON.parse(body);
              const detail = parsed.detail ?? {};
              enqueue({
                type: 'error',
                error: `Daily free token limit reached (${detail.used ?? '?'} / ${detail.limit ?? 50000}). Add a BYOK API key in Settings to continue.`,
              });
            } catch {
              enqueue({ type: 'error', error: 'Daily free token limit reached.' });
            }
            done = true;
            resolve?.();
          });
          return;
        }

        if ((res.statusCode ?? 500) >= 400) {
          enqueue({ type: 'error', error: `Provider returned HTTP ${res.statusCode}` });
          done = true;
          resolve?.();
          return;
        }

        res.on('data', (chunk: Buffer) => {
          const text = leftover + chunk.toString();
          const lines = text.split('\n');
          leftover = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) { continue; }
            const jsonStr = line.slice(6).trim();
            if (jsonStr === '[DONE]') { continue; }

            try {
              const obj = JSON.parse(jsonStr);

              // FreeBuff budget update
              if (isFreeBuff && obj.type === 'budget_update') {
                enqueue({ type: 'budget_update', budget: obj.budget });
                continue;
              }

              // Anthropic streaming format
              if (isAnthropic) {
                if (obj.type === 'content_block_delta' && obj.delta?.type === 'text_delta') {
                  enqueue({ type: 'text_delta', delta: obj.delta.text });
                }
                continue;
              }

              // OpenAI streaming format
              const delta = obj.choices?.[0]?.delta?.content;
              if (delta) {
                enqueue({ type: 'text_delta', delta });
              }
            } catch { /* malformed SSE chunk — skip */ }
          }
        });

        res.on('end', () => {
          enqueue({ type: 'done' });
          done = true;
          resolve?.();
        });
      },
    );

    req.on('error', (err: Error) => {
      enqueue({ type: 'error', error: err.message });
      done = true;
      resolve?.();
    });

    req.write(payload);
    req.end();

    // Yield chunks as they arrive
    while (!done || pending.length > 0) {
      if (pending.length === 0 && !done) {
        waitPromise = new Promise<void>((res, rej) => {
          resolve = res;
          reject = rej;
        });
        await waitPromise;
        resolve = undefined;
      }

      while (pending.length > 0) {
        yield pending.shift()!;
      }
    }
  }
}
