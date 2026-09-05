"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface ActivityBarItem {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
}

interface IdActivityBarProps {
  items: ActivityBarItem[];
  activeId: string;
  expanded: boolean;
  onSelect: (id: string) => void;
  bottom?: React.ReactNode;
}

/**
 * Narrow VS Code-style activity strip. Active item gets a subtle left
 * accent indicator + lighter icon. Icons stay monochrome, sparse color.
 */
export function IdActivityBar({ items, activeId, expanded, onSelect, bottom }: IdActivityBarProps) {
  return (
    <div className="w-11 shrink-0 h-full bg-[#0F0F13] border-r border-[#1C1C24] flex flex-col items-center justify-between py-2 select-none z-20">
      <div className="flex flex-col items-center gap-0.5 w-full">
        {items.map((item) => {
          const Icon = item.icon;
          const active = activeId === item.id && expanded;
          return (
            <button
              key={item.id}
              title={item.label}
              onClick={() => onSelect(item.id)}
              className={cn(
                "relative w-full h-9 flex items-center justify-center transition-colors group",
                active ? "text-white" : "text-[#565666] hover:text-[#C7C7D1]"
              )}
            >
              {/* Left active indicator */}
              <span
                className={cn(
                  "absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[2px] rounded-r transition-colors",
                  active ? "bg-[#E5252A]" : "bg-transparent"
                )}
              />
              <Icon sx={{ fontSize: 20 }} />
              {item.badge && !active && (
                <span className="absolute top-0.5 right-1 text-[8px] font-bold text-[#E5252A] font-mono">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {bottom && <div className="flex flex-col items-center gap-0.5 w-full">{bottom}</div>}
    </div>
  );
}