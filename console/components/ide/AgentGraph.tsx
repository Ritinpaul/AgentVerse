"use client";

import React from "react";
import { cn } from "@/lib/utils";

/**
 * Compact agent dependency graph — MODEL → AGENT → TOOLS → RUNTIME / GOVERNANCE.
 * Lightweight fixed-layout SVG for the connector lines + positioned node chips.
 * No physics simulation, no heavy canvas libraries.
 */

interface AgentGraphProps {
  agentName: string;
  modelLabel: string;
  tools: string[];
  status: "ready" | "running" | "error" | "stopped";
  trustLevel: string;
  trustScore: number;
  running?: boolean;
}

const W = 372;
const H = 336;

interface NodeCfg {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  sub: string;
  color: string;
}

function layoutNodes(props: AgentGraphProps): NodeCfg[] {
  const tools = props.tools.length > 0 ? props.tools.slice(0, 3) : ["web_search"];
  const toolRowW = tools.length * 104 - 12;
  const startX = (W - toolRowW) / 2;

  const nodes: NodeCfg[] = [
    {
      id: "model",
      x: W / 2 - 105,
      y: 8,
      w: 210,
      h: 38,
      label: "MODEL",
      sub: props.modelLabel,
      color: "#61AFEF",
    },
    {
      id: "agent",
      x: W / 2 - 88,
      y: 74,
      w: 176,
      h: 50,
      label: "AGENT",
      sub: props.agentName,
      color: "#E5252A",
    },
    ...tools.map((t, i) => ({
      id: `tool-${i}`,
      x: startX + i * 104,
      y: 152,
      w: 92,
      h: 40,
      label: "TOOL",
      sub: t,
      color: "#10B981",
    })),
    {
      id: "runtime",
      x: W / 2 - 108,
      y: 268,
      w: 96,
      h: 44,
      label: "RUNTIME",
      sub: "MicroVM",
      color: "#C678DD",
    },
    {
      id: "governance",
      x: W / 2 + 12,
      y: 268,
      w: 96,
      h: 44,
      label: "GOVERNANCE",
      sub: props.trustLevel,
      color: "#E5C07B",
    },
  ];
  return nodes;
}

function edgePaths(nodes: NodeCfg[]) {
  const model = nodes.find((n) => n.id === "model")!;
  const agent = nodes.find((n) => n.id === "agent")!;
  const tools = nodes.filter((n) => n.id.startsWith("tool-"));
  const runtime = nodes.find((n) => n.id === "runtime")!;
  const governance = nodes.find((n) => n.id === "governance")!;
  const spineY = tools[0] ? tools[0].y + tools[0].h + 10 : 0;

  const paths: string[] = [];

  // MODEL → AGENT
  paths.push(`M ${model.x + model.w / 2} ${model.y + model.h} V ${agent.y}`);
  // AGENT → each TOOL
  for (const tool of tools) {
    paths.push(`M ${agent.x + agent.w / 2} ${agent.y + agent.h} V ${tool.y}`);
    paths.push(`M ${tool.x + tool.w / 2} ${tool.y - 16} V ${tool.y - 1}`);
  }
  // TOOL bus → spine
  if (tools.length > 1) {
    const first = tools[0];
    const last = tools[tools.length - 1];
    paths.push(`M ${first.x + first.w / 2} ${first.y - 16} H ${last.x + last.w / 2}`);
  }
  // spine → RUNTIME & GOVERNANCE
  const spineMidY = spineY;
  paths.push(`M ${runtime.x + runtime.w / 2} ${spineY} V ${runtime.y}`);
  paths.push(`M ${governance.x + governance.w / 2} ${spineY} V ${governance.y}`);
  // AGENT → GOVERNANCE (dashed policy link)
  paths.push(
    `M ${agent.x + agent.w - 4} ${agent.y + agent.h} C ${agent.x + agent.w + 24} ${agent.y + agent.h + 30}, ${governance.x} ${governance.y - 24}, ${governance.x + 10} ${governance.y - 4}`
  );

  return { paths, spineY };
}

export function AgentGraph(props: AgentGraphProps) {
  const nodes = layoutNodes(props);
  const { paths } = edgePaths(nodes);
  const agent = nodes.find((n) => n.id === "agent")!;
  const isActive = props.status !== "stopped";

  return (
    <div className="relative w-full select-none" style={{ height: H }}>
      {/* Connector lines */}
      <svg width={W} height={H} className="absolute inset-0 z-0" style={{ overflow: "hidden" }}>
        {paths.map((d, i) => (
          <path
            key={i}
            d={d}
            fill="none"
            stroke="#2A2A38"
            strokeWidth={1}
            strokeDasharray={i === paths.length - 1 ? "3 3" : undefined}
          />
        ))}
      </svg>

      {/* Nodes */}
      {nodes.map((n) => {
        const isAgentNode = n.id === "agent";
        return (
          <div
            key={n.id}
            className={cn(
              "absolute z-10 flex flex-col items-center justify-center text-center px-2 border rounded-[3px] transition-shadow",
              isAgentNode && isActive
                ? "border-[#E5252A] shadow-[0_0_16px_rgba(229,37,42,0.35)] bg-[#16131A]"
                : "border-[#2A2A38] bg-[#111117]"
            )}
            style={{ left: n.x, top: n.y, width: n.w, height: n.h }}
          >
            <span className="text-[8px] font-bold uppercase tracking-[0.14em] font-mono" style={{ color: n.color }}>
              {n.label}
            </span>
            <span className="text-[10px] font-semibold text-white font-mono truncate w-full">{n.sub}</span>
          </div>
        );
      })}

      {/* Status footer */}
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-1 text-[9px] font-mono text-[#5C5C6C]">
        <span className="flex items-center gap-1.5">
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full animate-pulse",
              props.status === "running"
                ? "bg-[#61AFEF]"
                : props.status === "ready"
                ? "bg-[#10B981]"
                : props.status === "error"
                ? "bg-[#E5252A]"
                : "bg-[#71717A]"
            )}
          />
          {props.status.toUpperCase()}
        </span>
        <span>TRUST {props.trustScore.toFixed(1)}</span>
      </div>
    </div>
  );
}