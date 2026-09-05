/**
 * modelKeys.ts — Zero-Trust BYOK Key Manager
 *
 * Stores user-provided API keys in localStorage only.
 * Keys are never sent to AgentVerse servers — only forwarded
 * directly to the respective provider in request headers.
 */

export type ProviderKey =
  | "openai"
  | "anthropic"
  | "gemini"
  | "groq"
  | "chutes"
  | "openrouter"
  | "mistral";

export interface KeyEntry {
  provider: ProviderKey;
  key: string;       // the raw API key (never logged/persisted server-side)
  label: string;     // human label, e.g. "OpenAI"
  addedAt: string;   // ISO timestamp
  masked: string;    // e.g. "sk-...XY3z"
}

export interface ProviderMeta {
  id: ProviderKey;
  label: string;
  keyPrefix: string;
  placeholder: string;
  docsUrl: string;
  color: string;
}

const STORAGE_KEY = "av_byok_keys";

export const PROVIDER_META: ProviderMeta[] = [
  {
    id: "openai",
    label: "OpenAI",
    keyPrefix: "sk-",
    placeholder: "sk-...",
    docsUrl: "https://platform.openai.com/api-keys",
    color: "#10A37F",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    keyPrefix: "sk-ant-",
    placeholder: "sk-ant-...",
    docsUrl: "https://console.anthropic.com/settings/keys",
    color: "#CC785C",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    keyPrefix: "AIza",
    placeholder: "AIzaSy...",
    docsUrl: "https://aistudio.google.com/app/apikey",
    color: "#4285F4",
  },
  {
    id: "groq",
    label: "Groq",
    keyPrefix: "gsk_",
    placeholder: "gsk_...",
    docsUrl: "https://console.groq.com/keys",
    color: "#F55036",
  },
  {
    id: "chutes",
    label: "Chutes.ai",
    keyPrefix: "cpk-",
    placeholder: "cpk-...",
    docsUrl: "https://chutes.ai/app/api",
    color: "#7C3AED",
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    keyPrefix: "sk-or-",
    placeholder: "sk-or-...",
    docsUrl: "https://openrouter.ai/keys",
    color: "#6366F1",
  },
  {
    id: "mistral",
    label: "Mistral",
    keyPrefix: "",
    placeholder: "Your Mistral API key...",
    docsUrl: "https://console.mistral.ai/api-keys",
    color: "#FF7000",
  },
];

function maskKey(key: string): string {
  if (key.length < 8) return "***";
  return key.slice(0, 6) + "..." + key.slice(-4);
}

function loadKeys(): Record<ProviderKey, KeyEntry | undefined> {
  if (typeof window === "undefined") return {} as Record<ProviderKey, KeyEntry | undefined>;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : ({} as Record<ProviderKey, KeyEntry | undefined>);
  } catch {
    return {} as Record<ProviderKey, KeyEntry | undefined>;
  }
}

function saveKeys(keys: Record<ProviderKey, KeyEntry | undefined>): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}

export function getStoredKeys(): KeyEntry[] {
  const keys = loadKeys();
  return Object.values(keys).filter((k): k is KeyEntry => !!k);
}

export function getKey(provider: ProviderKey): string | null {
  const keys = loadKeys();
  return keys[provider]?.key ?? null;
}

export function hasKey(provider: ProviderKey): boolean {
  return !!getKey(provider);
}

export function getActiveProviders(): ProviderKey[] {
  return getStoredKeys().map((k) => k.provider);
}

export function addKey(provider: ProviderKey, key: string): void {
  const keys = loadKeys();
  keys[provider] = {
    provider,
    key: key.trim(),
    label: PROVIDER_META.find((p) => p.id === provider)?.label ?? provider,
    addedAt: new Date().toISOString(),
    masked: maskKey(key.trim()),
  };
  saveKeys(keys);
}

export function removeKey(provider: ProviderKey): void {
  const keys = loadKeys();
  delete keys[provider];
  saveKeys(keys);
}

export function clearAllKeys(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

/** Returns headers to inject into a chat request for a given provider */
export function getProviderHeaders(provider: ProviderKey): Record<string, string> {
  const key = getKey(provider);
  if (!key) return {};
  switch (provider) {
    case "openai":
      return { "x-byok-openai": key };
    case "anthropic":
      return { "x-byok-anthropic": key };
    case "gemini":
      return { "x-byok-gemini": key };
    case "groq":
      return { "x-byok-groq": key };
    case "chutes":
      return { "x-byok-chutes": key };
    case "openrouter":
      return { "x-byok-openrouter": key };
    case "mistral":
      return { "x-byok-mistral": key };
    default:
      return {};
  }
}
