"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import CircularProgress from "@mui/material/CircularProgress";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    // Public routes that don't require auth
    const isPublic = pathname === "/" || pathname.startsWith("/login") || pathname.startsWith("/register") || pathname.startsWith("/docs");

    if (isPublic) {
      setAuthorized(true);
      return;
    }

    const authed = isAuthenticated();
    if (!authed) {
      setAuthorized(false);
      router.replace("/login");
    } else {
      setAuthorized(true);
    }
  }, [pathname, router]);

  if (authorized === null) {
    return (
      <div className="min-h-screen bg-[#070709] flex flex-col items-center justify-center gap-4 text-white">
        <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/40 text-red-500">
          <SecurityRoundedIcon sx={{ fontSize: 32 }} />
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <CircularProgress size={16} sx={{ color: "#E5252A" }} />
          <span>VERIFYING CRYPTOGRAPHIC SESSION...</span>
        </div>
      </div>
    );
  }

  if (!authorized && !(pathname === "/" || pathname.startsWith("/login") || pathname.startsWith("/register"))) {
    return null;
  }

  return <>{children}</>;
}
