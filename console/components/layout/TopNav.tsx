"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { CommandPalette } from "@/components/shared/CommandPalette";
import { getStoredUser, clearAuth } from "@/lib/auth";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import HelpOutlineRoundedIcon from "@mui/icons-material/HelpOutlineRounded";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import { LogOut, ChevronDown } from "lucide-react";

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [user, setUser] = React.useState<any>(null);

  React.useEffect(() => {
    setUser(getStoredUser());
  }, []);

  useEffect(() => {
    const handleGlobalKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleGlobalKey);
    return () => window.removeEventListener("keydown", handleGlobalKey);
  }, []);

  const handleSignOut = () => {
    clearAuth();
    router.push("/login");
  };

  // Compute breadcrumb based on pathname
  let sectionName = "Registry Overview";
  if (pathname.includes("/govern")) sectionName = "GovernOS Sentinel";
  else if (pathname.includes("/monitor")) sectionName = "Telemetry & Traces";
  else if (pathname.includes("/agents")) sectionName = "Agents Fleet";
  else if (pathname.includes("/build")) sectionName = "IDE & Sandbox";
  else if (pathname.includes("/store")) sectionName = "AgentStore Marketplace";
  else if (pathname.includes("/settings")) sectionName = "Settings & Keys";

  return (
    <>
      <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} />
      <header className="h-14 border-b border-white/10 bg-[#181A1D]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30 select-none font-mono text-white">
        
        {/* Left: Breadcrumbs in White & Red */}
        <div className="flex items-center gap-2.5 text-sm text-white">
          <Link
            href="/console"
            className="flex items-center gap-2 group hover:opacity-80 transition-opacity"
            title="Go to Console Overview"
          >
            <img
              src="/logo.png"
              alt="AgentVerse Logo"
              className="w-5 h-5 object-contain filter brightness-0 invert group-hover:scale-105 transition-transform"
            />
            <span className="font-bold tracking-tight text-white font-sans group-hover:text-[#38D9A9] transition-colors">
              AgentVerse
            </span>
          </Link>
          <span className="text-[#E5252A] font-bold">/</span>
          <span className="text-neutral-300 text-xs font-mono">{sectionName}</span>
        </div>

        {/* Right: Search + Icons + Sign Out & Profile Dropdown */}
        <div className="flex items-center gap-4">
          
          {/* Search bar */}
          <div
            onClick={() => setIsPaletteOpen(true)}
            className="flex items-center gap-2 bg-[#22252A] border border-white/10 px-3 py-1.5 rounded-xl text-xs text-neutral-300 cursor-pointer hover:border-[#E5252A]/50 transition-colors w-64 shadow-inner"
          >
            <SearchRoundedIcon sx={{ fontSize: 15, color: "#E5252A" }} />
            <span className="flex-1 truncate">Search kernels...</span>
            <span className="text-[10px] bg-[#181A1D] px-1.5 py-0.5 rounded border border-white/10 text-neutral-400">⌘K</span>
          </div>

          {/* Quick Icons & Profile */}
          <div className="flex items-center gap-3 text-neutral-300">
            <Link href="/docs" className="hover:text-white transition-colors flex items-center p-1 rounded-lg hover:bg-white/5" title="Documentation">
              <HelpOutlineRoundedIcon sx={{ fontSize: 18, color: "#34D399" }} />
            </Link>
            <Link href="/settings" className="hover:text-white transition-colors flex items-center p-1 rounded-lg hover:bg-white/5" title="Settings">
              <SettingsOutlinedIcon sx={{ fontSize: 18, color: "#FFFFFF" }} />
            </Link>

            {/* Direct Sign Out Button */}
            <button
              onClick={handleSignOut}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-bold text-red-400 hover:text-red-200 bg-red-950/40 hover:bg-red-900/60 border border-red-800/50 rounded-xl transition-all shadow-sm active:scale-95"
              title="Sign Out of AgentVerse"
            >
              <LogOut className="w-3.5 h-3.5 text-red-500" />
              <span>Sign Out</span>
            </button>
            
            {/* User Profile & Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsProfileOpen((prev) => !prev)}
                className="flex items-center gap-1.5 p-1 rounded-xl hover:bg-white/5 transition-colors focus:outline-none"
                title="User Profile & Account Settings"
              >
                <div className="w-7 h-7 rounded-xl bg-[#E5252A] text-white text-xs font-bold flex items-center justify-center shadow-md shadow-red-950/50">
                  {user?.email?.charAt(0).toUpperCase() || "A"}
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-neutral-400 transition-transform ${isProfileOpen ? "rotate-180" : ""}`} />
              </button>

              {/* Profile Dropdown Menu */}
              {isProfileOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsProfileOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-64 bg-[#14151D] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden font-sans p-1.5">
                    {/* User Info Header */}
                    <div className="p-3 bg-[#1A1C26] rounded-xl border border-white/5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white truncate max-w-[130px]">
                          {user?.name || "Platform Executive"}
                        </span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 uppercase font-semibold">
                          {user?.role || "Owner"}
                        </span>
                      </div>
                      <div className="text-[11px] text-neutral-400 font-mono truncate">
                        {user?.email || "admin@nuuvixx.ai"}
                      </div>
                      <div className="text-[10px] text-neutral-500 font-mono truncate pt-0.5">
                        {user?.org_name || "Nuuvixx AI Systems"}
                      </div>
                    </div>

                    <div className="my-1.5 border-t border-white/5" />

                    {/* Multi-Workspace Context Switcher */}
                    <div className="px-2 py-1 space-y-1">
                      <div className="text-[10px] font-mono uppercase text-neutral-400 font-bold px-1 tracking-wider flex items-center justify-between">
                        <span>Active Workspace Context</span>
                        <span className="text-[9px] text-[#38D9A9] font-normal">SaaS Scoped</span>
                      </div>
                      <div className="space-y-1 pt-0.5">
                        {[
                          { id: "ws-personal", name: "Personal Workspace", slug: "personal-ws", role: "owner", tag: "Owner (Personal)" },
                          { id: "ws-acme", name: "Acme Corp Dev Team", slug: "acme-corp", role: "admin", tag: "Admin (Invited)" },
                          { id: "ws-[#audit]", name: "Global Audit Org", slug: "global-audit", role: "read", tag: "Auditor (Read Only)" },
                        ].map((ws) => {
                          const isActive = user?.org_slug === ws.slug || (!user?.org_slug && ws.id === "ws-personal");
                          return (
                            <button
                              key={ws.id}
                              onClick={() => {
                                const updatedUser = {
                                  ...user,
                                  role: ws.role as any,
                                  org_name: ws.name,
                                  org_slug: ws.slug,
                                  active_workspace_id: ws.id,
                                };
                                setUser(updatedUser);
                                if (typeof window !== "undefined") {
                                  localStorage.setItem("agentverse_user_profile", JSON.stringify(updatedUser));
                                }
                                setIsProfileOpen(false);
                              }}
                              className={`w-full px-2.5 py-1.5 text-xs font-mono rounded-xl border text-left transition-all flex items-center justify-between ${
                                isActive
                                  ? "bg-[#E5252A]/10 border-[#E5252A]/40 text-white font-bold"
                                  : "bg-[#181A22] border-white/5 text-neutral-400 hover:text-white hover:bg-white/5"
                              }`}
                              title={`Switch context to ${ws.name} (${ws.role})`}
                            >
                              <div className="truncate pr-2">
                                <div className="text-[11px] truncate text-white">{ws.name}</div>
                                <div className="text-[9px] text-neutral-500 font-mono">{ws.tag}</div>
                              </div>
                              {isActive && (
                                <span className="w-1.5 h-1.5 rounded-full bg-[#E5252A] shrink-0" />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="my-1.5 border-t border-white/5" />

                    {/* Menu items */}
                    <div className="space-y-0.5 text-xs">
                      <Link
                        href="/settings"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-neutral-300 hover:text-white hover:bg-white/5 transition-colors"
                      >
                        <SettingsOutlinedIcon sx={{ fontSize: 16 }} />
                        <span>Settings & API Keys</span>
                      </Link>
                      <Link
                        href="/docs"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-neutral-300 hover:text-white hover:bg-white/5 transition-colors"
                      >
                        <HelpOutlineRoundedIcon sx={{ fontSize: 16 }} />
                        <span>Documentation</span>
                      </Link>
                    </div>

                    <div className="my-1.5 border-t border-white/5" />

                    {/* Sign Out Button in Dropdown */}
                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        handleSignOut();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-red-400 hover:text-red-300 hover:bg-red-950/40 border border-transparent hover:border-red-900/30 transition-colors"
                    >
                      <LogOut className="w-4 h-4 text-red-500" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>
    </>
  );
}

