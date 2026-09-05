"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("AgentVerse Console Error Caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 glass-card rounded-2xl border border-red-500/30 text-center space-y-4 max-w-lg mx-auto my-12 font-mono">
          <div className="p-3 rounded-xl bg-red-500/10 text-red-400 w-12 h-12 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-base font-bold text-text-primary">
            {this.props.fallbackTitle || "MicroVM Service Exception Intercepted"}
          </h2>
          <p className="text-xs text-text-muted font-sans leading-relaxed">
            GovernOS Sentinel caught a runtime exception. You can reload this component or return to the overview dashboard.
          </p>
          {this.state.error && (
            <pre className="p-3 rounded-lg bg-[#0B0D14] text-[11px] text-red-300 text-left overflow-x-auto">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={() => this.setState({ hasError: false })}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 mx-auto transition-all shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Recover Component</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
