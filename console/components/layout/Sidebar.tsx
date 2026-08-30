"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAgents } from "@/hooks/useAgents";
import { useSystemHealth } from "@/hooks/useGovernance";
import { getStoredUser, clearAuth } from "@/lib/auth";
import {
  Rocket,
  Bot,
  Activity,
  ShieldCheck,
  Store,
  Wrench,
  Settings,
  LayoutDashboard,
  Cpu,
  Zap,
  ChevronRight,
  BookOpen,
  LogOut,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { agents } = useAgents();
  const health = useSystemHealth();
  const agentCount = String(agents.length);
  const [user, setUser] = React.useState<any>(null);

  React.useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const handleSignOut = () => {
    clearAuth();
    router.push("/login");
  };

  const navSections = [
    {
      title: "CORE WORKSPACE",
      items: [
        { label: "Overview", href: "/console", icon: LayoutDashboard },
        { label: "Build & IDE", href: "/build", icon: Wrench },
        { label: "Agents Fleet", href: "/agents", icon: Bot, badge: agentCount },
      ],
    },
    {
      title: "OBSERVABILITY & POLICY",
      items: [
        { label: "Monitor & Traces", href: "/monitor", icon: Activity, badge: "LIVE" },
        { label: "GovernOS Sentinel", href: "/govern", icon: ShieldCheck, badge: "100%" },
      ],
    },
    {
      title: "ECOSYSTEM",
      items: [
        { label: "AgentStore Hub", href: "/store", icon: Store },
        { label: "Documentation", href: "/docs", icon: BookOpen },
      ],
    },
    {
      title: "SYSTEM",
      items: [
        { label: "Settings & API Keys", href: "/settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 h-screen flex-shrink-0 bg-[#0E0F14] border-r border-[#1E1E28] flex flex-col justify-between select-none relative z-20 font-sans text-white">
      
      {/* Top Header: Workspace & Organization Brand */}
      <div className="p-4 border-b border-[#1E1E28] bg-[#12131A]">
        <Link
          href="/console"
          className="flex items-center gap-3 group cursor-pointer hover:opacity-85 transition-opacity"
          title="Go to Console Overview"
        >
          <img
            src="/logo.png"
            alt="AgentVerse Logo"
            className="w-9 h-9 object-contain shrink-0 filter brightness-0 invert group-hover:scale-105 transition-transform"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-white text-xs tracking-wide font-mono uppercase truncate group-hover:text-[#38D9A9] transition-colors">
                AgentVerse OS
              </h2>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30 font-bold">
                v2.4
              </span>
            </div>
            <p className="text-[11px] text-neutral-400 font-mono truncate mt-0.5 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#38D9A9] animate-pulse" />
              Nuuvixx Core Org
            </p>
          </div>
        </Link>
      </div>

      {/* Main Navigation Items */}
      <div className="flex-1 overflow-y-auto p-3 space-y-6 no-scrollbar">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="px-3 text-[10px] font-bold text-neutral-500 uppercase tracking-widest font-mono">
              {section.title}
            </div>

            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/console" && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all group",
                      isActive
                        ? "bg-[#1B1C28] text-white font-bold border border-[#2E3042] shadow-sm"
                        : "text-neutral-400 hover:text-white hover:bg-[#14151D]"
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon
                        className={cn(
                          "w-4 h-4 transition-colors shrink-0",
                          isActive ? "text-[#38D9A9]" : "text-neutral-500 group-hover:text-neutral-300"
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={cn(
                          "text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold shrink-0",
                          item.badge === "LIVE"
                            ? "bg-[#38D9A9]/15 text-[#38D9A9] border border-[#38D9A9]/30"
                            : item.badge === "100%"
                            ? "bg-violet-500/15 text-violet-300 border border-violet-500/30"
                            : "bg-[#1E1F2C] text-neutral-300 border border-[#2B2C3E]"
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Sandbox Health, User Session & Primary Action */}
      <div className="p-3 border-t border-[#1E1E28] bg-[#12131A] space-y-3">
        {/* Sandbox Health Info Pill */}
        <div className="p-2.5 rounded-xl bg-[#090A0E] border border-[#1E1E28] text-[11px] font-mono space-y-1">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-[#38D9A9]" />
              <span>MicroVM Sandbox</span>
            </span>
            <span className="text-[#38D9A9] font-bold">{agents.length} Registered</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-neutral-400 pt-0.5 font-mono">
            <span className="flex items-center gap-1">
              <span className={cn("w-1.5 h-1.5 rounded-full", health?.agentStore?.status === "online" ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-neutral-600")} />
              Store
            </span>
            <span className="flex items-center gap-1">
              <span className={cn("w-1.5 h-1.5 rounded-full", health?.agentOS?.status === "online" ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-neutral-600")} />
              AgentOS
            </span>
            <span className="flex items-center gap-1">
              <span className={cn("w-1.5 h-1.5 rounded-full", health?.agentGovernOS?.status === "online" ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" : "bg-neutral-600")} />
              GovernOS
            </span>
          </div>
        </div>

        {/* User Card with Sign Out Button */}
        <div className="p-2 rounded-xl bg-[#090A0E] border border-[#1E1E28] flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-6 h-6 rounded-lg bg-[#E5252A] text-white text-[11px] font-bold flex items-center justify-center shrink-0 shadow-md">
              {user?.email?.charAt(0).toUpperCase() || "A"}
            </div>
            <div className="min-w-0 flex-1 text-xs">
              <div className="font-semibold text-white truncate text-[11px]">
                {user?.name || "Platform Executive"}
              </div>
              <div className="text-[10px] text-neutral-400 truncate font-mono">
                {user?.email || "admin@nuuvixx.ai"}
              </div>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-red-400 hover:bg-red-950/50 border border-transparent hover:border-red-800/40 transition-colors shrink-0"
            title="Sign Out of AgentVerse"
          >
            <LogOut className="w-3.5 h-3.5 text-red-500" />
          </button>
        </div>

        {/* Deploy Agent Primary CTA Button */}
        <Link
          href="/build"
          className="w-full py-2.5 px-4 rounded-xl bg-[#E5252A] hover:bg-[#D01E23] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-[#E5252A]/25 border border-[#F5353A] transition-all active:scale-98"
        >
          <Rocket className="w-4 h-4" />
          <span>DEPLOY AGENT</span>
        </Link>
      </div>
    </aside>
  );
}

