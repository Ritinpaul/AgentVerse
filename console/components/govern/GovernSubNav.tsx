"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  Lock,
  FileText,
  CheckCircle2,
  Zap,
  Radio,
  Award,
  Network,
} from "lucide-react";
import { useGovernance } from "@/hooks/useGovernance";

export function GovernSubNav() {
  const pathname = usePathname();
  const { pendingApprovalsCount } = useGovernance();

  const links = [
    { href: "/govern", label: "Overview", icon: ShieldCheck, exact: true },
    { href: "/govern/policies", label: "Policy Editor", icon: Lock },
    { href: "/govern/audit", label: "Audit Ledger", icon: FileText },
    {
      href: "/govern/approvals",
      label: "Approvals",
      icon: CheckCircle2,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
    },
    { href: "/govern/analytics", label: "QI Cache", icon: Zap },
    { href: "/govern/scan", label: "ASI Scanner", icon: Radio },
    { href: "/govern/compliance", label: "Compliance", icon: Award },
    { href: "/govern/gateways", label: "Gateways", icon: Network },
  ];

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-white/10 font-mono text-xs shrink-0 select-none">
      {links.map((item) => {
        const isActive = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl transition-all whitespace-nowrap ${
              isActive
                ? "bg-[#22252A] text-white font-bold border border-[#E5252A]/50 shadow-md shadow-black/40"
                : "bg-white/[0.03] text-neutral-400 border border-white/5 hover:text-white hover:bg-white/[0.08]"
            }`}
          >
            <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#E5252A]" : "text-neutral-400"}`} />
            <span>{item.label}</span>
            {item.badge !== undefined && (
              <span className="px-1.5 py-0.2 rounded-full bg-[#E5252A] text-white font-bold text-[10px]">
                {item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}
