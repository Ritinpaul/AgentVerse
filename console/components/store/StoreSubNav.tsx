"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShoppingBag,
  UploadCloud,
  Key,
  DollarSign,
  Handshake,
  Layers,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";

export function StoreSubNav() {
  const pathname = usePathname();
  const { totalInstalled, activeContractsCount } = useStore();

  const links = [
    { href: "/store", label: "Marketplace", icon: ShoppingBag, exact: true },
    { href: "/store/publish", label: "Publish Wizard", icon: UploadCloud },
    {
      href: "/store/purchases",
      label: "My Installs",
      icon: Key,
      badge: totalInstalled > 0 ? totalInstalled : undefined,
    },
    { href: "/store/revenue", label: "Creator Revenue", icon: DollarSign },
    {
      href: "/store/a2a",
      label: "A2A Escrow",
      icon: Handshake,
      badge: activeContractsCount > 0 ? activeContractsCount : undefined,
    },
    { href: "/store/compositions", label: "Compositions", icon: Layers },
  ];

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1 border-b border-surface-border font-mono text-xs shrink-0">
      {links.map((item) => {
        const isActive = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
              isActive
                ? "bg-surface-100 text-emerald-400 font-bold border border-emerald-500/40 shadow-sm"
                : "text-text-muted hover:text-text-primary hover:bg-surface-100/50"
            }`}
          >
            <Icon className={`w-3.5 h-3.5 ${isActive ? "text-emerald-400" : "text-text-muted"}`} />
            <span>{item.label}</span>
            {item.badge !== undefined && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">
                {item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}
