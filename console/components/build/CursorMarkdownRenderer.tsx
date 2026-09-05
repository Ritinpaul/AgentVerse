"use client";

import React, { useState } from "react";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";

interface CursorMarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
  isAccepted?: boolean;
  isRejected?: boolean;
  onApplyCode?: (code: string, language: string) => void;
  onApplyAllCode?: (blocks: { code: string; language: string }[]) => void;
  onRejectAllCode?: () => void;
}

interface ParsedBlock {
  type: "text" | "code";
  content: string;
  language?: string;
}

/** Blinking caret shown at the end of a streaming AI message */
function StreamingCursor() {
  return (
    <>
      <style>{`
        @keyframes agentverse-cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        .agentverse-cursor {
          display: inline-block;
          width: 2px;
          height: 0.85em;
          background: #38D9A9;
          border-radius: 1px;
          margin-left: 2px;
          vertical-align: text-bottom;
          animation: agentverse-cursor-blink 0.9s ease-in-out infinite;
        }
      `}</style>
      <span className="agentverse-cursor" aria-hidden="true" />
    </>
  );
}

export function CursorMarkdownRenderer({
  content,
  isStreaming = false,
  isAccepted = false,
  isRejected = false,
  onApplyCode,
  onApplyAllCode,
  onRejectAllCode,
}: CursorMarkdownRendererProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [appliedIndices, setAppliedIndices] = useState<Set<number>>(new Set());
  const [allApplied, setAllApplied] = useState(false);

  const isAllDone = isAccepted || allApplied;

  // Parse Markdown into text blocks and fenced code blocks
  const parseBlocks = (raw: string): ParsedBlock[] => {
    const blocks: ParsedBlock[] = [];
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(raw)) !== null) {
      if (match.index > lastIndex) {
        blocks.push({ type: "text", content: raw.substring(lastIndex, match.index) });
      }
      blocks.push({
        type: "code",
        language: match[1] || "yaml",
        content: match[2].trim(),
      });
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < raw.length) {
      blocks.push({ type: "text", content: raw.substring(lastIndex) });
    }

    return blocks;
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleApply = (code: string, language: string, index: number) => {
    onApplyCode?.(code, language);
    setAppliedIndices((prev) => new Set(prev).add(index));
  };

  const renderInlineFormattedText = (text: string, showCursorAtEnd = false) => {
    const lines = text.split("\n");
    return lines.map((line, lIdx) => {
      const trimmed = line.trim();
      const isLastLine = lIdx === lines.length - 1;

      // Heading 3 / Heading 2 / Heading 1
      if (/^#{1,3}\s/.test(trimmed)) {
        const headerText = trimmed.replace(/^#{1,3}\s/, "");
        return (
          <h4 key={lIdx} className="text-xs font-bold text-white mt-2.5 mb-1 flex items-center gap-1.5 border-b border-[#22222B] pb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E5252A]" />
            {formatBoldAndCode(headerText)}
            {showCursorAtEnd && isLastLine && <StreamingCursor />}
          </h4>
        );
      }

      // Bullet List Item
      if (/^[-*•]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) {
        const listText = trimmed.replace(/^([-*•]|\d+\.)\s/, "");
        return (
          <div key={lIdx} className="flex items-start gap-2 my-1 pl-1 text-xs text-neutral-300 leading-relaxed">
            <span className="text-[#10B981] font-bold shrink-0 mt-0.5">•</span>
            <span>
              {formatBoldAndCode(listText)}
              {showCursorAtEnd && isLastLine && <StreamingCursor />}
            </span>
          </div>
        );
      }

      if (!trimmed) {
        return <div key={lIdx} className="h-1.5" />;
      }

      return (
        <p key={lIdx} className="my-1 text-xs leading-relaxed text-neutral-300">
          {formatBoldAndCode(line)}
          {showCursorAtEnd && isLastLine && <StreamingCursor />}
        </p>
      );
    });
  };

  // Helper to format **bold** and `inline code`
  const formatBoldAndCode = (str: string) => {
    const parts = str.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={pIdx} className="font-bold text-white">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={pIdx}
            className="px-1.5 py-0.5 bg-[#1C1C26] text-[#E5C07B] border border-[#2A2A38] rounded font-mono text-[11px]"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  const blocks = parseBlocks(content);
  const lastBlockIndex = blocks.length - 1;

  return (
    <div className="space-y-2.5 font-sans">
      {blocks.map((block, bIdx) => {
        const isLastBlock = bIdx === lastBlockIndex;

        if (block.type === "text") {
          return (
            <div key={bIdx}>
              {renderInlineFormattedText(block.content, isStreaming && isLastBlock)}
            </div>
          );
        }

        const isCopied = copiedIndex === bIdx;
        const isApplied = isAllDone || appliedIndices.has(bIdx);
        const lang = block.language || "yaml";

        return (
          <div
            key={bIdx}
            className="my-2.5 border border-[#272734] bg-[#0A0A0E] rounded-xl overflow-hidden shadow-lg font-mono"
          >
            {/* VS Code IDE Header Bar */}
            <div className="h-7 px-3 bg-[#121218] border-b border-[#22222E] flex items-center justify-between text-[10px] font-sans">
              <div className="flex items-center gap-2">
                <CodeRoundedIcon sx={{ fontSize: 13, color: "#10B981" }} />
                <span className="font-bold uppercase tracking-wider text-neutral-300">
                  {lang}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCopy(block.content, bIdx)}
                  className="px-2 py-0.5 bg-[#1A1A24] hover:bg-[#252534] text-neutral-300 hover:text-white border border-[#2A2A3A] rounded transition-all flex items-center gap-1 text-[10px]"
                  title="Copy code"
                >
                  {isCopied ? (
                    <>
                      <CheckRoundedIcon sx={{ fontSize: 11, color: "#10B981" }} /> Copied
                    </>
                  ) : (
                    <>
                      <ContentCopyRoundedIcon sx={{ fontSize: 11 }} /> Copy
                    </>
                  )}
                </button>
                {onApplyCode && (
                  isAllDone || appliedIndices.has(bIdx) ? (
                    <span className="px-2 py-0.5 bg-[#10B981]/15 text-[#10B981] font-mono text-[10px] rounded border border-[#10B981]/30 flex items-center gap-1 font-semibold">
                      <CheckRoundedIcon sx={{ fontSize: 11 }} /> Applied
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleApply(block.content, lang, bIdx)}
                      className="px-2 py-0.5 bg-[#10B981]/20 hover:bg-[#10B981] text-[#10B981] hover:text-black font-bold border border-[#10B981]/50 rounded transition-all flex items-center gap-1 text-[10px] cursor-pointer active:scale-95"
                      title="Apply to file"
                    >
                      <PlayArrowRoundedIcon sx={{ fontSize: 11 }} /> Apply to {lang === "python" || lang === "py" ? "tools.py" : "agent.yaml"}
                    </button>
                  )
                )}
              </div>
            </div>

          {/* Code Block Lines */}
          <div className="p-3 text-[11px] leading-relaxed overflow-x-auto bg-[#07070A] text-[#10B981]">
            <pre className="font-mono">
              {block.content.split("\n").map((line, lIdx, arr) => (
                <div key={lIdx} className="flex gap-3">
                  <span className="w-5 shrink-0 text-right text-neutral-600 font-mono text-[10px] select-none">
                    {lIdx + 1}
                  </span>
                  <span className="text-neutral-200">
                    {line}
                    {isStreaming && isLastBlock && lIdx === arr.length - 1 && <StreamingCursor />}
                  </span>
                </div>
              ))}
            </pre>
          </div>
        </div>
      );
    })}

    {/* Cursor on empty message before first tokens arrive */}
    {isStreaming && content === "" && (
      <p className="my-1 text-xs leading-relaxed text-neutral-300">
        <StreamingCursor />
      </p>
    )}

    {/* Antigravity / Cursor Apply All & Reject All Bar for Code Blocks */}
    {!isStreaming && blocks.some((b) => b.type === "code") && (onApplyAllCode || onRejectAllCode) && (
      <div className="mt-3 pt-2.5 border-t border-[#22222E] flex items-center justify-between gap-2 font-sans">
        <span className="text-neutral-400 text-[11px] font-medium flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9]" />
          {blocks.filter((b) => b.type === "code").length} code {blocks.filter((b) => b.type === "code").length === 1 ? "block" : "blocks"} proposed
        </span>
        {isAllDone ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#10B981]/15 border border-[#10B981]/40 rounded-lg text-[#10B981] text-[11px] font-mono font-semibold">
            <CheckRoundedIcon sx={{ fontSize: 13 }} />
            Changes Applied to Workspace
          </div>
        ) : isRejected ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#1A1A24] border border-[#2A2A3A] rounded-lg text-neutral-400 text-[11px] font-mono">
            Rejected
          </div>
        ) : (
          <div className="flex items-center gap-2">
            {onApplyAllCode && (
              <button
                type="button"
                onClick={() => {
                  const codeBlocks = blocks
                    .filter((b): b is ParsedBlock & { type: "code" } => b.type === "code")
                    .map((b) => ({ code: b.content, language: b.language || "yaml" }));
                  onApplyAllCode(codeBlocks);
                  setAllApplied(true);
                }}
                className="px-3 py-1 bg-[#10B981] hover:bg-[#059669] text-black font-bold text-[11px] rounded-lg transition-all flex items-center gap-1 shadow-md cursor-pointer active:scale-95"
              >
                <CheckRoundedIcon sx={{ fontSize: 13 }} />
                Apply All
              </button>
            )}
            {onRejectAllCode && (
              <button
                type="button"
                onClick={() => {
                  onRejectAllCode();
                  setAllApplied(false);
                }}
                className="px-2.5 py-1 bg-[#181822] hover:bg-[#252532] border border-[#2E2E3E] text-neutral-400 hover:text-white font-medium text-[11px] rounded-lg transition-all cursor-pointer active:scale-95"
              >
                Reject All
              </button>
            )}
          </div>
        )}
      </div>
    )}
  </div>
  );
}
