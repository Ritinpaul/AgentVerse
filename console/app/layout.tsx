import type { Metadata } from "next";
import { Black_Ops_One, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { ShellLayout } from "@/components/layout/ShellLayout";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { MuiProvider } from "@/components/shared/MuiProvider";

const blackOpsOne = Black_Ops_One({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-black-ops-one",
  display: "swap",
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AgentVerse Console — The Operating System for the Agentic Economy",
  description: "Enterprise console for building, running, governing, and monetizing autonomous AI agents at scale.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${blackOpsOne.variable} ${plusJakartaSans.variable} h-full`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Bebas+Neue&family=Oswald:wght@400;500;600;700&family=Teko:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={`${plusJakartaSans.className} bg-[#070709] text-slate-100 antialiased selection:bg-red-600/30 selection:text-white relative overflow-x-hidden min-h-screen`}>
        {/* Background Ambient Glows */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
          <div className="ambient-glow-center" />
          <div className="ambient-glow-left" />
          <div className="ambient-glow-right" />
        </div>
        <MuiProvider>
          <AuthGuard>
            <ShellLayout>{children}</ShellLayout>
          </AuthGuard>
        </MuiProvider>
      </body>
    </html>
  );
}
