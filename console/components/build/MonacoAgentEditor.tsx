"use client";

import React, { useRef, useEffect, useCallback } from "react";
import Editor, { useMonaco, OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

// ─── Governance Diagnostics ──────────────────────────────────────────────────
export interface GovernanceDiagnostic {
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  line?: number;
}

function findLineNumber(text: string, pattern: string | RegExp): number | undefined {
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    if (typeof pattern === "string") {
      if (lines[i].includes(pattern)) return i + 1;
    } else {
      if (pattern.test(lines[i])) return i + 1;
    }
  }
  return undefined;
}

function runGovernanceChecks(yaml: string): GovernanceDiagnostic[] {
  const issues: GovernanceDiagnostic[] = [];

  // ASI01 – prompt injection risk: no system prompt isolation
  if (!yaml.includes("policy_set") && !yaml.includes("governance")) {
    issues.push({
      code: "ASI01",
      severity: "error",
      message: "ASI01: No governance block. Prompt injection attacks are unmitigated.",
      line: 1,
    });
  }

  // ASI02 – tool scope not explicit
  const hasWriteScope = yaml.includes("scope: write") || yaml.includes("scope: read_write") || yaml.includes("scope: admin");
  const hasAllowedScopes = yaml.includes("allowed_tool_scopes");
  if (hasWriteScope && !hasAllowedScopes) {
    issues.push({
      code: "ASI02",
      severity: "warning",
      message: "ASI02: Tools with write/admin scope but no allowed_tool_scopes whitelist in governance block.",
      line: findLineNumber(yaml, "scope:") ?? findLineNumber(yaml, "tools:") ?? 1,
    });
  }

  // ASI03 – PII risk: email/send tools without pii_scan
  const hasPiiRiskTool =
    yaml.includes("send_email") ||
    yaml.includes("send_sms") ||
    yaml.includes("user_data") ||
    yaml.includes("personal");
  const hasPiiScan = yaml.includes("pii_scan: true");
  if (hasPiiRiskTool && !hasPiiScan) {
    issues.push({
      code: "ASI03",
      severity: "warning",
      message: "ASI03: Tool with potential PII access detected. Add `pii_scan: true` under governance.",
      line: findLineNumber(yaml, /(send_email|send_sms|user_data|personal)/) ?? 1,
    });
  }

  // ASI04 – no budget cap
  if (!yaml.includes("budget")) {
    issues.push({
      code: "ASI04",
      severity: "error",
      message: "ASI04: No budget limits defined. Runaway cost execution risk.",
      line: findLineNumber(yaml, "governance:") ?? findLineNumber(yaml, "model:") ?? findLineNumber(yaml, "runtime:") ?? 1,
    });
  }

  // ASI05 – admin scope without human approval
  const hasAdminScope = yaml.includes("scope: admin");
  const hasHumanApproval = yaml.includes("require_human_approval: true");
  if (hasAdminScope && !hasHumanApproval) {
    issues.push({
      code: "ASI05",
      severity: "error",
      message: "ASI05: Admin-scoped tool found. Require human approval for admin actions (require_human_approval: true).",
      line: findLineNumber(yaml, "scope: admin") ?? 1,
    });
  }

  // ASI06 – no fallback model
  if (!yaml.includes("fallback_model")) {
    issues.push({
      code: "ASI06",
      severity: "info",
      message: "ASI06: No fallback_model specified. Consider adding one for resilience.",
      line: findLineNumber(yaml, "model:") ?? findLineNumber(yaml, "provider:") ?? 1,
    });
  }

  return issues;
}

// ─── Cost Estimator ──────────────────────────────────────────────────────────
const MODEL_PRICES: Record<string, number> = {
  "gemini-2.5-pro": 0.00125,
  "gemini-2.5-flash": 0.000075,
  "gemini-2.0-flash": 0.0001,
  "gpt-4o": 0.005,
  "gpt-4o-mini": 0.00015,
  "claude-sonnet-4-5": 0.003,
  "claude-3-5-haiku": 0.0008,
  "mistral-large": 0.004,
  "llama-3.3-70b": 0.00072,
};

export interface CostEstimate {
  modelName: string;
  pricePerKToken: number;
  maxTokens: number;
  estimatedCostPerRun: number;
  budgetCeiling: number | null;
}

function estimateCost(yaml: string): CostEstimate {
  // Extract model
  const modelMatch = yaml.match(/model:\s*([\w.-]+)/);
  const modelName = modelMatch?.[1] ?? "gemini-2.5-flash";
  const pricePerKToken = MODEL_PRICES[modelName] ?? 0.001;

  // Extract max_tokens
  const tokenMatch = yaml.match(/max_tokens:\s*(\d+)/);
  const maxTokens = parseInt(tokenMatch?.[1] ?? "8192");

  // Budget ceiling
  const budgetMatch = yaml.match(/max_cost_per_run:\s*([\d.]+)/);
  const budgetCeiling = budgetMatch ? parseFloat(budgetMatch[1]) : null;

  const estimatedCostPerRun = (maxTokens / 1000) * pricePerKToken;

  return { modelName, pricePerKToken, maxTokens, estimatedCostPerRun, budgetCeiling };
}

// ─── Props ───────────────────────────────────────────────────────────────────
interface MonacoAgentEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** Editor language id — switch to match the active file extension. */
  language?: string;
  /** Optional per-file model path (keeps undo stacks per file). */
  path?: string;
  onDiagnosticsChange?: (diagnostics: GovernanceDiagnostic[]) => void;
  onCostChange?: (cost: CostEstimate) => void;
}

// ─── Component ───────────────────────────────────────────────────────────────
export function MonacoAgentEditor({
  value,
  onChange,
  language = "yaml",
  path,
  onDiagnosticsChange,
  onCostChange,
}: MonacoAgentEditorProps) {
  const monaco = useMonaco();
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<string[]>([]);

  // Register YAML schema once Monaco loads
  useEffect(() => {
    if (!monaco) return;

    // Configure YAML language (Monaco treats YAML as plain text by default;
    // we'll use the yaml language id and add tokenization later).
    // For now, configure it as yaml and hook schema via diagnostics.
    monaco.languages.register({ id: "yaml" });

    // Set editor theme
    monaco.editor.defineTheme("agentverse-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "key", foreground: "79b8ff" },
        { token: "string", foreground: "85e89d" },
        { token: "number", foreground: "f8e3a1" },
        { token: "comment", foreground: "6a737d", fontStyle: "italic" },
        { token: "keyword", foreground: "ea4a5a" },
      ],
      colors: {
        "editor.background": "#0B0D14",
        "editor.foreground": "#E6EDF3",
        "editorLineNumber.foreground": "#3d444d",
        "editorLineNumber.activeForeground": "#6e7681",
        "editor.selectionBackground": "#3B4252",
        "editor.inactiveSelectionBackground": "#2D333B",
        "editorCursor.foreground": "#6366f1",
        "editor.lineHighlightBackground": "#161b22",
        "editorGutter.background": "#0B0D14",
        "scrollbarSlider.background": "#21262d80",
        "scrollbarSlider.hoverBackground": "#30363d",
      },
    });

    monaco.editor.setTheme("agentverse-dark");
  }, [monaco]);

  // Apply governance diagnostics as Monaco markers
  const applyDiagnostics = useCallback(
    (yaml: string) => {
      if (!monaco || !editorRef.current) return;

      const model = editorRef.current.getModel();
      if (!model) return;

      // If viewing a non-YAML file (e.g. tools.py), clear governance markers and return
      if (path && !path.endsWith(".yaml") && !path.endsWith(".yml")) {
        monaco.editor.setModelMarkers(model, "governos", []);
        return;
      }

      const issues = runGovernanceChecks(yaml);
      const cost = estimateCost(yaml);

      onDiagnosticsChange?.(issues);
      onCostChange?.(cost);

      // Convert to Monaco markers
      const markers: editor.IMarkerData[] = issues.map((issue) => ({
        severity:
          issue.severity === "error"
            ? monaco.MarkerSeverity.Error
            : issue.severity === "warning"
            ? monaco.MarkerSeverity.Warning
            : monaco.MarkerSeverity.Info,
        message: issue.message,
        startLineNumber: issue.line ?? 1,
        startColumn: 1,
        endLineNumber: issue.line ?? 1,
        endColumn: 999,
        code: issue.code,
        source: "GovernOS ASI Scanner",
      }));

      monaco.editor.setModelMarkers(model, "governos", markers);
    },
    [monaco, path, onDiagnosticsChange, onCostChange]
  );

  // Reactively re-run diagnostics whenever value or active file path changes externally
  useEffect(() => {
    applyDiagnostics(value);
  }, [value, path, applyDiagnostics]);

  const handleMount: OnMount = useCallback(
    (editorInstance) => {
      editorRef.current = editorInstance;
      applyDiagnostics(value);

      // Add keyboard shortcut: Ctrl+Shift+V = Validate
      editorInstance.addCommand(
        ((window as any).monaco?.KeyMod?.CtrlCmd || 2048) |
          ((window as any).monaco?.KeyMod?.Shift || 1024) |
          ((window as any).monaco?.KeyCode?.KeyV || 52),
        () => {
          applyDiagnostics(editorInstance.getValue());
        }
      );
    },
    [applyDiagnostics, value]
  );

  const handleChange = useCallback(
    (newValue: string | undefined) => {
      const v = newValue ?? "";
      onChange(v);
      applyDiagnostics(v);
    },
    [onChange, applyDiagnostics]
  );

  return (
    <Editor
      height="100%"
      language={language}
      path={path}
      value={value}
      onChange={handleChange}
      onMount={handleMount}
      theme="agentverse-dark"
      options={{
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
        fontLigatures: true,
        lineNumbers: "on",
        minimap: { enabled: true, size: "proportional", maxColumn: 60, renderCharacters: false },
        scrollBeyondLastLine: false,
        wordWrap: "off",
        tabSize: 2,
        insertSpaces: true,
        renderLineHighlight: "all",
        cursorBlinking: "smooth",
        cursorSmoothCaretAnimation: "on",
        smoothScrolling: true,
        padding: { top: 12, bottom: 12 },
        glyphMargin: true,
        folding: true,
        showUnused: true,
        bracketPairColorization: { enabled: true },
        guides: { indentation: true, bracketPairs: true, highlightActiveIndentation: true },
        "semanticHighlighting.enabled": true,
        renderWhitespace: "none",
        scrollbar: {
          verticalScrollbarSize: 6,
          horizontalScrollbarSize: 6,
          verticalSliderSize: 6,
          horizontalSliderSize: 6,
        },
      }}
    />
  );
}

// Re-export helpers for parent components
export { runGovernanceChecks, estimateCost };
