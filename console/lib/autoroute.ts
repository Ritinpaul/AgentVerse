/**
 * autoroute.ts — AgentVerse Smart Model Router
 *
 * Classifies prompt intent and routes to the best available model.
 * V1: Pure keyword/heuristic classifier (zero latency, zero cost).
 * Zero external API calls. Runs entirely client-side.
 */

export type ModelIntent = "code" | "reasoning" | "analysis" | "fast" | "creative";

export type ModelTier = "free" | "byok";

export interface ModelDef {
  id: string;
  label: string;
  provider: "chutes" | "openai" | "anthropic" | "gemini" | "groq" | "openrouter";
  tier: ModelTier;
  contextWindow: number;
  strengths: ModelIntent[];
  costPer1kTokens?: number;
  badge?: string;
}

export interface RouteDecision {
  intent: ModelIntent;
  model: ModelDef;
  reason: string;
  confidence: "high" | "medium" | "low";
  estimatedInputTokens: number;
}

// ─── Model Registry ─────────────────────────────────────────────────────────

export const FREE_MODELS: ModelDef[] = [
  {
    id: "deepseek/deepseek-r1",
    label: "DeepSeek-R1 (Reasoning)",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["reasoning"],
    badge: "Free",
  },
  {
    id: "deepseek/deepseek-v3",
    label: "DeepSeek-V3 (General)",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["code", "reasoning"],
    badge: "Free",
  },
  {
    id: "glm/glm-5.3-flash",
    label: "GLM-5.3 Flash",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["analysis", "fast"],
    badge: "Free",
  },
  {
    id: "deepseek/deepseek-coder-v2",
    label: "DeepSeek-Coder-V2",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["code"],
    badge: "Free",
  },
  {
    id: "meta-llama/llama-3.3-70b-instruct",
    label: "Llama 3.3 70B",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["reasoning", "analysis", "creative"],
    badge: "Free",
  },
  {
    id: "qwen/qwen2.5-72b-instruct",
    label: "Qwen 2.5 72B",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["analysis", "reasoning", "code"],
    badge: "Free",
  },
  {
    id: "mistralai/mistral-7b-instruct",
    label: "Mistral 7B",
    provider: "chutes",
    tier: "free",
    contextWindow: 32000,
    strengths: ["fast", "creative"],
    badge: "Free",
  },
  {
    id: "meta-llama/llama-3.1-8b-instruct",
    label: "Llama 3.1 8B",
    provider: "chutes",
    tier: "free",
    contextWindow: 128000,
    strengths: ["fast"],
    badge: "Free",
  },
];

export const BYOK_MODELS: ModelDef[] = [
  {
    id: "claude-3-5-sonnet-20241022",
    label: "Claude 3.5 Sonnet",
    provider: "anthropic",
    tier: "byok",
    contextWindow: 200000,
    strengths: ["code", "reasoning", "analysis"],
    costPer1kTokens: 0.003,
    badge: "Best",
  },
  {
    id: "gpt-4o",
    label: "GPT-4o",
    provider: "openai",
    tier: "byok",
    contextWindow: 128000,
    strengths: ["reasoning", "creative", "analysis"],
    costPer1kTokens: 0.005,
  },
  {
    id: "gpt-4o-mini",
    label: "GPT-4o Mini",
    provider: "openai",
    tier: "byok",
    contextWindow: 128000,
    strengths: ["fast", "code"],
    costPer1kTokens: 0.00015,
    badge: "Fast",
  },
  {
    id: "gemini-1.5-pro",
    label: "Gemini 1.5 Pro",
    provider: "gemini",
    tier: "byok",
    contextWindow: 1000000,
    strengths: ["analysis", "reasoning"],
    costPer1kTokens: 0.00125,
  },
  {
    id: "gemini-2.0-flash",
    label: "Gemini 2.0 Flash",
    provider: "gemini",
    tier: "byok",
    contextWindow: 1000000,
    strengths: ["fast", "code"],
    costPer1kTokens: 0.0001,
    badge: "Fast",
  },
  {
    id: "llama3-70b-8192",
    label: "Llama 3 70B (Groq)",
    provider: "groq",
    tier: "byok",
    contextWindow: 8192,
    strengths: ["fast", "reasoning"],
    costPer1kTokens: 0.00059,
    badge: "Ultra-Fast",
  },
];

export const ALL_MODELS = [...FREE_MODELS, ...BYOK_MODELS];

// ─── Intent Classifier ───────────────────────────────────────────────────────

const CODE_KEYWORDS = [
  "code", "function", "debug", "error", "bug", "implement", "fix", "refactor",
  "typescript", "python", "javascript", "class", "method", "algorithm",
  "compile", "syntax", "import", "module", "api", "endpoint", "schema",
  "sql", "query", "regex", "test", "unit test", "lint", "type error",
  "console.log", "def ", "async ", "await ", "interface ", "component",
];

const REASONING_KEYWORDS = [
  "plan", "strategy", "architecture", "design", "evaluate", "decide",
  "compare", "tradeoff", "best approach", "how should", "what would",
  "multi-step", "workflow", "pipeline", "orchestrate", "agent", "chain",
  "think through", "reason", "analyze step", "break down",
];

const ANALYSIS_KEYWORDS = [
  "summarize", "summary", "analyze", "analyse", "document", "report",
  "review", "explain", "describe", "what does this", "read this",
  "translate", "paragraph", "article", "long", "transcript",
  "content", "extract", "insight", "overview",
];

const CREATIVE_KEYWORDS = [
  "write", "generate", "create", "draft", "story", "creative", "blog",
  "email", "marketing", "copy", "tagline", "description", "post",
  "social media", "tweet", "linkedin", "brainstorm", "ideas",
];

function countMatches(text: string, keywords: string[]): number {
  const lower = text.toLowerCase();
  return keywords.filter((k) => lower.includes(k)).length;
}

export function classifyIntent(prompt: string): { intent: ModelIntent; confidence: "high" | "medium" | "low" } {
  const scores: Record<ModelIntent, number> = {
    code: countMatches(prompt, CODE_KEYWORDS),
    reasoning: countMatches(prompt, REASONING_KEYWORDS),
    analysis: countMatches(prompt, ANALYSIS_KEYWORDS),
    creative: countMatches(prompt, CREATIVE_KEYWORDS),
    fast: 0,
  };

  if (prompt.length > 1000) scores.analysis += 2;
  if (prompt.length < 80 && Object.values(scores).every((s) => s === 0)) {
    scores.fast = 3;
  }

  const entries = Object.entries(scores).sort(([, a], [, b]) => b - a) as [ModelIntent, number][];
  const [topIntent, topScore] = entries[0];

  const confidence: "high" | "medium" | "low" =
    topScore >= 3 ? "high" : topScore >= 1 ? "medium" : "low";

  return { intent: topIntent, confidence };
}

// ─── Routing Matrix ──────────────────────────────────────────────────────────

const FREE_ROUTING: Record<ModelIntent, string> = {
  code: "deepseek/deepseek-v3",
  reasoning: "deepseek/deepseek-r1",
  analysis: "glm/glm-5.3-flash",
  creative: "mistralai/mistral-7b-instruct",
  fast: "meta-llama/llama-3.1-8b-instruct",
};

const BYOK_ROUTING: Record<ModelIntent, string> = {
  code: "claude-3-5-sonnet-20241022",
  reasoning: "claude-3-5-sonnet-20241022",
  analysis: "gemini-1.5-pro",
  creative: "gpt-4o",
  fast: "gpt-4o-mini",
};

const INTENT_REASONS: Record<ModelIntent, string> = {
  code: "Code & debugging task detected — DeepSeek-V3",
  reasoning: "Multi-step reasoning task detected — DeepSeek-R1",
  analysis: "Analysis task detected — GLM-5.3 Flash",
  creative: "Creative generation task detected — Mistral 7B",
  fast: "Quick query — Llama 3.1 8B",
};

// ─── Main Router ─────────────────────────────────────────────────────────────

export function autoRoute(
  prompt: string,
  activeBYOKProviders: string[] = [],
  overrideModelId?: string
): RouteDecision {
  const { intent, confidence } = classifyIntent(prompt);
  const estimatedInputTokens = Math.ceil(prompt.length / 4);

  if (overrideModelId) {
    const model = ALL_MODELS.find((m) => m.id === overrideModelId);
    if (model) {
      return {
        intent,
        model,
        reason: `Manually selected: ${model.label}`,
        confidence,
        estimatedInputTokens,
      };
    }
  }

  const preferredByokId = BYOK_ROUTING[intent];
  const preferredByokModel = BYOK_MODELS.find((m) => m.id === preferredByokId);
  if (preferredByokModel && activeBYOKProviders.includes(preferredByokModel.provider)) {
    return {
      intent,
      model: preferredByokModel,
      reason: `${INTENT_REASONS[intent]} — using your ${preferredByokModel.provider} key`,
      confidence,
      estimatedInputTokens,
    };
  }

  const freeModelId = FREE_ROUTING[intent];
  const freeModel = FREE_MODELS.find((m) => m.id === freeModelId) ?? FREE_MODELS[0];

  return {
    intent,
    model: freeModel,
    reason: `${INTENT_REASONS[intent]} — free tier`,
    confidence,
    estimatedInputTokens,
  };
}

// ─── Daily Quota Helpers ─────────────────────────────────────────────────────

const DAILY_LIMIT_FREE = 50_000;
const STORAGE_KEY_USAGE = "av_daily_usage";
const STORAGE_KEY_DATE = "av_usage_date";

export interface DailyUsage {
  tokensUsed: number;
  limit: number;
  date: string;
  pct: number;
  remaining: number;
  exhausted: boolean;
}

function todayUTC(): string {
  return new Date().toISOString().split("T")[0];
}

export function getDailyUsage(): DailyUsage {
  if (typeof window === "undefined") {
    return { tokensUsed: 0, limit: DAILY_LIMIT_FREE, date: todayUTC(), pct: 0, remaining: DAILY_LIMIT_FREE, exhausted: false };
  }

  const storedDate = localStorage.getItem(STORAGE_KEY_DATE);
  const today = todayUTC();

  if (storedDate !== today) {
    localStorage.setItem(STORAGE_KEY_DATE, today);
    localStorage.setItem(STORAGE_KEY_USAGE, "0");
  }

  const tokensUsed = parseInt(localStorage.getItem(STORAGE_KEY_USAGE) ?? "0", 10);
  const pct = Math.min(100, Math.round((tokensUsed / DAILY_LIMIT_FREE) * 100));

  return {
    tokensUsed,
    limit: DAILY_LIMIT_FREE,
    date: today,
    pct,
    remaining: Math.max(0, DAILY_LIMIT_FREE - tokensUsed),
    exhausted: tokensUsed >= DAILY_LIMIT_FREE,
  };
}

export function recordTokenUsage(tokens: number): void {
  if (typeof window === "undefined") return;
  const current = getDailyUsage();
  localStorage.setItem(STORAGE_KEY_USAGE, String(current.tokensUsed + tokens));
}
