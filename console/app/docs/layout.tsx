"use client";

import React, { useState, useEffect, createContext, useContext } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen, Search, X, ChevronRight, Menu, ExternalLink,
  Zap, Layers, Shield, Terminal, Code2, Server, Box,
  Link2, GitBranch, Settings, Home
} from "lucide-react";

// ── Navigation Data ──────────────────────────────────────────────────────────
export const NAV_SECTIONS = [
  {
    title: "GETTING STARTED",
    items: [
      { slug: "quickstart",      label: "Quickstart",          icon: Zap },
      { slug: "architecture",    label: "Platform Architecture", icon: Layers },
      { slug: "concepts",        label: "Core Concepts",        icon: BookOpen },
    ]
  },
  {
    title: "AGENT DEVELOPMENT",
    items: [
      { slug: "agent-yaml",      label: "agent.yaml Reference", icon: Code2 },
      { slug: "sdk-python",      label: "Python SDK",           icon: Box },
      { slug: "sdk-typescript",  label: "TypeScript SDK",       icon: Box },
      { slug: "cli",             label: "CLI Reference",        icon: Terminal },
    ]
  },
  {
    title: "SECURITY & GOVERNANCE",
    items: [
      { slug: "sentinel",        label: "GovernOS Sentinel",    icon: Shield },
      { slug: "policies",        label: "Policy Engine",        icon: Settings },
      { slug: "audit-ledger",    label: "Decision Ledger",      icon: Shield },
    ]
  },
  {
    title: "API REFERENCE",
    items: [
      { slug: "api-agentstore",  label: "AgentStore API",       icon: Server },
      { slug: "api-governance",  label: "Governance API",       icon: Server },
      { slug: "api-control",     label: "Control Plane API",    icon: Server },
    ]
  },
  {
    title: "INTEGRATIONS",
    items: [
      { slug: "vscode-extension", label: "VS Code Extension",  icon: Code2 },
      { slug: "mcp-protocol",    label: "MCP Protocol",         icon: Link2 },
      { slug: "a2a-protocol",    label: "A2A Protocol",         icon: GitBranch },
    ]
  },
];

// ── TOC Context ───────────────────────────────────────────────────────────────
type Heading = {id: string; text: string; level: number};

export const TOCContext = createContext<{ 
  headings: Heading[]; 
  setHeadings: React.Dispatch<React.SetStateAction<Heading[]>>
}>({
  headings: [], 
  setHeadings: () => {}
});

export function useTOC() { return useContext(TOCContext); }

// ── Docs Layout ───────────────────────────────────────────────────────────────
export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [headings, setHeadings] = useState<{id: string; text: string; level: number}[]>([]);
  const [activeHeading, setActiveHeading] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Keyboard shortcut for search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Active heading tracking
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) setActiveHeading(entry.target.id);
        });
      },
      { rootMargin: "-80px 0px -80% 0px" }
    );
    headings.forEach(h => {
      const el = document.getElementById(h.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [headings]);

  const currentSlug = pathname.split("/docs/")[1] || "quickstart";

  // Simple flat search across nav
  const allItems = NAV_SECTIONS.flatMap(s => s.items.map(i => ({ ...i, section: s.title })));
  const filtered = searchQuery
    ? allItems.filter(i => i.label.toLowerCase().includes(searchQuery.toLowerCase()) || i.section.toLowerCase().includes(searchQuery.toLowerCase()))
    : allItems.slice(0, 6);

  const SidebarNav = () => (
    <nav className="py-4 space-y-6">
      {NAV_SECTIONS.map(section => (
        <div key={section.title}>
          <div className="px-3 mb-2 text-[10px] font-bold tracking-widest text-[#E5252A]/80 uppercase">
            {section.title}
          </div>
          <div className="space-y-0.5">
            {section.items.map(item => {
              const isActive = currentSlug === item.slug;
              const Icon = item.icon;
              return (
                <Link
                  key={item.slug}
                  href={`/docs/${item.slug}`}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 group ${
                    isActive
                      ? "bg-[#E5252A]/15 text-[#E5252A] font-semibold border border-[#E5252A]/30"
                      : "text-white/60 hover:text-white/90 hover:bg-white/5"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-[#E5252A]" : "text-white/30 group-hover:text-white/60"}`} />
                  <span className="font-mono text-xs">{item.label}</span>
                  {isActive && <ChevronRight className="w-3 h-3 ml-auto text-[#E5252A]/60" />}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );

  return (
    <TOCContext.Provider value={{ headings, setHeadings }}>
      <div className="min-h-screen bg-[#0B0D14] text-white font-mono">

        {/* ── Top Header Bar ─────────────────────────────────────── */}
        <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-[#0B0D14]/95 backdrop-blur-xl border-b border-white/8 flex items-center gap-4 px-4">
          {/* Mobile menu toggle */}
          <button
            className="lg:hidden p-1.5 text-white/60 hover:text-white"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <img
              src="/logo.png"
              alt="AgentVerse Logo"
              className="w-6 h-6 object-contain shrink-0 filter brightness-0 invert"
            />
            <span className="text-white font-bold text-sm hidden sm:block">AGENTVERSE</span>
            <span className="text-white/30 hidden sm:block">/</span>
            <span className="text-white/60 text-sm hidden sm:block">DOCS</span>
          </Link>

          {/* Search bar */}
          <button
            onClick={() => setSearchOpen(true)}
            className="flex-1 max-w-md mx-auto flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-white/40 hover:text-white/70 transition-all text-xs"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Search docs...</span>
            <span className="ml-auto flex items-center gap-0.5">
              <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px]">⌘</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-[10px]">K</kbd>
            </span>
          </button>

          {/* Right links */}
          <div className="flex items-center gap-3 ml-auto shrink-0">
            <Link href="/" className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
              <Home className="w-3.5 h-3.5" />
              <span className="hidden sm:block">Console</span>
            </Link>
            <a href="http://localhost:8050" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:block">Marketplace</span>
            </a>
          </div>
        </header>

        {/* ── Body: Sidebar + Content + TOC ─────────────────────── */}
        <div className="flex pt-14">

          {/* Left Sidebar — desktop fixed */}
          <aside className="hidden lg:block fixed top-14 left-0 bottom-0 w-60 overflow-y-auto border-r border-white/8 bg-[#090B11]">
            <SidebarNav />
          </aside>

          {/* Mobile Sidebar Overlay */}
          {sidebarOpen && (
            <div className="lg:hidden fixed inset-0 z-40" onClick={() => setSidebarOpen(false)}>
              <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
              <aside className="absolute top-14 left-0 bottom-0 w-64 bg-[#090B11] border-r border-white/10 overflow-y-auto z-50" onClick={e => e.stopPropagation()}>
                <SidebarNav />
              </aside>
            </div>
          )}

          {/* Main Content */}
          <main className="flex-1 lg:ml-60 lg:mr-56 min-h-[calc(100vh-3.5rem)]">
            <div className="max-w-3xl mx-auto px-6 py-10">
              {children}
            </div>
          </main>

          {/* Right TOC — desktop fixed */}
          {headings.length > 0 && (
            <aside className="hidden lg:block fixed top-14 right-0 bottom-0 w-56 overflow-y-auto border-l border-white/8 bg-[#090B11] px-4 py-6">
              <div className="text-[10px] font-bold tracking-widest text-white/30 uppercase mb-3">On This Page</div>
              <nav className="space-y-1">
                {headings.map(h => (
                  <a
                    key={h.id}
                    href={`#${h.id}`}
                    className={`block text-xs py-1 transition-colors hover:text-white ${
                      activeHeading === h.id ? "text-[#E5252A]" : "text-white/40"
                    } ${h.level === 3 ? "pl-3" : ""}`}
                  >
                    {h.text}
                  </a>
                ))}
              </nav>
            </aside>
          )}
        </div>

        {/* ── Search Modal ───────────────────────────────────────── */}
        {searchOpen && (
          <div className="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4" onClick={() => setSearchOpen(false)}>
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <div
              className="relative w-full max-w-lg bg-[#0F1117] border border-white/15 rounded-xl shadow-2xl overflow-hidden"
              onClick={e => e.stopPropagation()}
            >
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
                <Search className="w-4 h-4 text-white/40 shrink-0" />
                <input
                  autoFocus
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search documentation..."
                  className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/30 font-mono"
                />
                <button onClick={() => setSearchOpen(false)} className="text-white/40 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Results */}
              <div className="p-2 max-h-80 overflow-y-auto">
                {filtered.length === 0 ? (
                  <div className="text-center py-8 text-white/30 text-sm">No results found</div>
                ) : (
                  filtered.map(item => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.slug}
                        href={`/docs/${item.slug}`}
                        onClick={() => { setSearchOpen(false); setSearchQuery(""); }}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/8 transition-colors group"
                      >
                        <div className="p-1.5 rounded-md bg-white/5 group-hover:bg-[#E5252A]/15 transition-colors">
                          <Icon className="w-3.5 h-3.5 text-white/40 group-hover:text-[#E5252A]" />
                        </div>
                        <div>
                          <div className="text-sm text-white/80 group-hover:text-white">{item.label}</div>
                          <div className="text-[10px] text-white/30">{item.section}</div>
                        </div>
                        <ChevronRight className="w-3.5 h-3.5 ml-auto text-white/20 group-hover:text-white/50" />
                      </Link>
                    );
                  })
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-white/10 px-4 py-2 flex items-center gap-3 text-[10px] text-white/30">
                <span><kbd className="px-1.5 py-0.5 rounded bg-white/10">↵</kbd> to select</span>
                <span><kbd className="px-1.5 py-0.5 rounded bg-white/10">↑↓</kbd> to navigate</span>
                <span><kbd className="px-1.5 py-0.5 rounded bg-white/10">Esc</kbd> to close</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </TOCContext.Provider>
  );
}
