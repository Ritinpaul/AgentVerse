"use client";

import React, { useState, useEffect, useRef } from "react";
import { Copy, Check, Info, Lightbulb, AlertTriangle, AlertCircle } from "lucide-react";
import { useTOC } from "@/app/docs/layout";

// ── Copy-able Code Block ──────────────────────────────────────────────────────
interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
}

export function CodeBlock({ code, language = "bash", filename }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Simple token colorizer
  const colorize = (line: string): React.ReactNode[] => {
    const patterns: [RegExp, string][] = [
      [/(".*?"|'.*?')/g, "text-yellow-300"],
      [/(#.*)$/gm, "text-white/30"],
      [/\b(import|from|export|const|let|var|function|return|async|await|if|else|true|false|null|undefined|class|extends|interface|type|def|class|import|from|for|while|in|not|and|or|is|None|True|False)\b/g, "text-[#C586C0]"],
      [/\b(curl|npm|npx|pip|docker|python|node|cd|git|cp|mkdir|echo)\b/g, "text-[#569CD6]"],
      [/(https?:\/\/[^\s"']+)/g, "text-[#4EC9B0]"],
      [/\b(\d+(?:\.\d+)?)\b/g, "text-[#B5CEA8]"],
    ];

    // For simplicity, return the whole line colored based on language type
    if (language === "bash" || language === "sh") {
      return [<span key={0} className="text-emerald-300">{line}</span>];
    }
    if (language === "yaml" || language === "yml") {
      const parts = line.split(/(:)/);
      if (parts.length >= 2) {
        return [
          <span key={0} className="text-[#4EC9B0]">{parts[0]}</span>,
          <span key={1} className="text-white/60">{parts[1]}</span>,
          <span key={2} className="text-yellow-200">{parts.slice(2).join("")}</span>
        ];
      }
      return [<span key={0} className="text-white/80">{line}</span>];
    }
    if (language === "json") {
      if (line.includes('"') && line.includes(':')) {
        const colonIdx = line.indexOf(':');
        return [
          <span key={0} className="text-[#9CDCFE]">{line.slice(0, colonIdx)}</span>,
          <span key={1} className="text-white/50">:</span>,
          <span key={2} className="text-yellow-200">{line.slice(colonIdx + 1)}</span>
        ];
      }
    }
    return [<span key={0} className="text-white/85">{line}</span>];
  };

  return (
    <div className="relative rounded-xl overflow-hidden border border-white/10 my-4 group">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#E5252A]/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
          {filename && <span className="ml-2 text-[11px] text-white/40 font-mono">{filename}</span>}
          {!filename && language && <span className="ml-2 text-[10px] text-white/30 uppercase tracking-wider">{language}</span>}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] text-white/40 hover:text-white/70 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {/* Code */}
      <pre className="bg-[#070910] overflow-x-auto p-4 text-[12px] leading-relaxed">
        {code.trim().split("\n").map((line, i) => (
          <div key={i} className="flex">
            <span className="select-none text-white/20 w-8 shrink-0 text-right mr-4">{i + 1}</span>
            <span>{colorize(line)}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}

// ── Inline Code ───────────────────────────────────────────────────────────────
export function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 rounded bg-white/8 text-[#4EC9B0] text-[0.85em] font-mono border border-white/10">
      {children}
    </code>
  );
}

// ── Callout / Alert Box ───────────────────────────────────────────────────────
type CalloutType = "note" | "tip" | "warning" | "important";

const CALLOUT_STYLES: Record<CalloutType, { border: string; bg: string; icon: React.ReactNode; label: string; textColor: string }> = {
  note:      { border: "border-[#569CD6]/40", bg: "bg-[#569CD6]/8",  icon: <Info className="w-3.5 h-3.5" />, label: "NOTE",      textColor: "text-[#569CD6]" },
  tip:       { border: "border-emerald-500/40", bg: "bg-emerald-500/8",icon: <Lightbulb className="w-3.5 h-3.5" />, label: "TIP",       textColor: "text-emerald-400" },
  warning:   { border: "border-yellow-500/40", bg: "bg-yellow-500/8", icon: <AlertTriangle className="w-3.5 h-3.5" />, label: "WARNING",   textColor: "text-yellow-400" },
  important: { border: "border-[#E5252A]/40",  bg: "bg-[#E5252A]/8", icon: <AlertCircle className="w-3.5 h-3.5" />, label: "IMPORTANT", textColor: "text-[#E5252A]" },
};

export function Callout({ type = "note", children }: { type?: CalloutType; children: React.ReactNode }) {
  const s = CALLOUT_STYLES[type];
  return (
    <div className={`my-4 p-4 rounded-xl border ${s.border} ${s.bg}`}>
      <div className={`text-[10px] font-bold tracking-widest mb-1.5 flex items-center gap-1.5 ${s.textColor}`}>
        {s.icon} <span>{s.label}</span>
      </div>
      <div className="text-sm text-white/75 leading-relaxed font-sans">{children}</div>
    </div>
  );
}

// ── Section Heading (auto-registers in TOC) ────────────────────────────────────
export function DocH2({ children }: { children: string }) {
  const { setHeadings, headings } = useTOC();
  const id = children.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  useEffect(() => {
    setHeadings(prev => {
      if (prev.find(h => h.id === id)) return prev;
      return [...prev, { id, text: children, level: 2 }];
    });
    return () => {
      setHeadings(prev => prev.filter(h => h.id !== id));
    };
  }, [id, children, setHeadings]);

  return (
    <h2 id={id} className="group text-xl font-bold text-white mt-10 mb-4 flex items-center gap-2 scroll-mt-20">
      {children}
      <a href={`#${id}`} className="opacity-0 group-hover:opacity-40 text-white text-sm">#</a>
    </h2>
  );
}

export function DocH3({ children }: { children: string }) {
  const { setHeadings } = useTOC();
  const id = children.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  useEffect(() => {
    setHeadings(prev => {
      if (prev.find(h => h.id === id)) return prev;
      return [...prev, { id, text: children, level: 3 }];
    });
    return () => {
      setHeadings(prev => prev.filter(h => h.id !== id));
    };
  }, [id, children, setHeadings]);

  return (
    <h3 id={id} className="group text-base font-semibold text-white/90 mt-7 mb-3 flex items-center gap-2 scroll-mt-20">
      <span className="text-[#E5252A] mr-0.5">›</span>
      {children}
      <a href={`#${id}`} className="opacity-0 group-hover:opacity-40 text-white text-sm">#</a>
    </h3>
  );
}

// ── Service Port Badge ─────────────────────────────────────────────────────────
export function PortBadge({ port, label, desc }: { port: string; label: string; desc: string }) {
  return (
    <div className="p-4 rounded-xl bg-white/4 border border-white/10 hover:border-white/20 transition-colors">
      <div className="text-[10px] text-white/30 uppercase tracking-wider font-bold mb-1">Port {port}</div>
      <div className="text-white font-bold text-sm mb-1">{label}</div>
      <div className="text-white/50 text-xs font-sans leading-relaxed">{desc}</div>
    </div>
  );
}

// ── Live API Playground ───────────────────────────────────────────────────────
interface PlaygroundProps {
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  baseUrl: string;
  defaultBody?: string;
}

export function ApiPlayground({ method, endpoint, baseUrl, defaultBody }: PlaygroundProps) {
  const [body, setBody] = useState(defaultBody || "");
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<number | null>(null);

  const methodColors: Record<string, string> = {
    GET: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
    POST: "text-[#E5252A] bg-[#E5252A]/10 border-[#E5252A]/30",
    PUT: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
    DELETE: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  };

  const handleRun = async () => {
    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${baseUrl}${endpoint}`, {
        method,
        headers: { "Content-Type": "application/json" },
        ...(method !== "GET" && body ? { body } : {}),
      });
      setStatus(res.status);
      const data = await res.json().catch(() => res.text());
      setResponse(typeof data === "string" ? data : JSON.stringify(data, null, 2));
    } catch (e: any) {
      setStatus(0);
      setResponse(`Connection error: ${e.message}\n\nMake sure the service is running at ${baseUrl}`);
    }
    setLoading(false);
  };

  return (
    <div className="rounded-xl border border-white/10 overflow-hidden my-4">
      {/* Endpoint bar */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white/4 border-b border-white/10">
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded border font-mono ${methodColors[method]}`}>
          {method}
        </span>
        <code className="text-sm text-white/70 flex-1 truncate font-mono">{baseUrl}{endpoint}</code>
        <button
          onClick={handleRun}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg bg-[#E5252A] hover:bg-[#E5252A]/80 text-white text-xs font-bold transition-colors disabled:opacity-60 flex items-center gap-1.5"
        >
          {loading ? (
            <span className="animate-pulse">Running...</span>
          ) : (
            <><span>▶</span> Run</>
          )}
        </button>
      </div>

      {/* Body editor (for non-GET) */}
      {method !== "GET" && (
        <div className="border-b border-white/10">
          <div className="px-4 pt-2 pb-1 text-[10px] text-white/30 uppercase tracking-wider">Request Body</div>
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            className="w-full bg-[#070910] text-emerald-300 text-xs p-4 font-mono resize-none h-28 outline-none"
            placeholder='{"key": "value"}'
            spellCheck={false}
          />
        </div>
      )}

      {/* Response */}
      {response && (
        <div>
          <div className="px-4 pt-2 pb-1 bg-white/3 border-b border-white/10 flex items-center gap-2">
            <span className="text-[10px] text-white/30 uppercase tracking-wider">Response</span>
            {status !== null && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                status >= 200 && status < 300 ? "text-emerald-400 bg-emerald-400/10" :
                status >= 400 ? "text-[#E5252A] bg-[#E5252A]/10" : "text-yellow-400 bg-yellow-400/10"
              }`}>
                {status === 0 ? "ERR" : status}
              </span>
            )}
          </div>
          <pre className="bg-[#050710] text-white/75 text-[11px] p-4 overflow-x-auto max-h-64 font-mono leading-relaxed">
            {response}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Method Card (table-row alternative) ──────────────────────────────────────
export function ApiEndpointCard({ method, path, desc }: { method: string; path: string; desc: string }) {
  const methodColors: Record<string, string> = {
    GET: "text-emerald-400 bg-emerald-400/10",
    POST: "text-[#E5252A] bg-[#E5252A]/10",
    PUT: "text-yellow-400 bg-yellow-400/10",
    DELETE: "text-orange-400 bg-orange-400/10",
    PATCH: "text-purple-400 bg-purple-400/10",
  };
  return (
    <div className="flex items-start gap-3 py-3 border-b border-white/8 hover:bg-white/3 px-2 rounded-lg transition-colors">
      <span className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono shrink-0 mt-0.5 ${methodColors[method] || "text-white/50 bg-white/10"}`}>
        {method}
      </span>
      <div>
        <code className="text-sm text-white/80">{path}</code>
        <div className="text-xs text-white/40 mt-0.5 font-sans">{desc}</div>
      </div>
    </div>
  );
}
