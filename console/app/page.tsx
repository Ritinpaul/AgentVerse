"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
} from "framer-motion";

// MUI Icons
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import MonitorHeartRoundedIcon from "@mui/icons-material/MonitorHeartRounded";
import ConstructionRoundedIcon from "@mui/icons-material/ConstructionRounded";
import StorefrontRoundedIcon from "@mui/icons-material/StorefrontRounded";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import LayersRoundedIcon from "@mui/icons-material/LayersRounded";
import MemoryRoundedIcon from "@mui/icons-material/MemoryRounded";
import LockRoundedIcon from "@mui/icons-material/LockRounded";
import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import DnsRoundedIcon from "@mui/icons-material/DnsRounded";
import PublicRoundedIcon from "@mui/icons-material/PublicRounded";
import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import TrendingUpRoundedIcon from "@mui/icons-material/TrendingUpRounded";
import PaidRoundedIcon from "@mui/icons-material/PaidRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";

/* ══════════════════════════════════════════════════════════════════════════
   ANIMATION VARIANTS
   ══════════════════════════════════════════════════════════════════════════ */

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const fadeLeft = {
  hidden: { opacity: 0, x: 40 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.65, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const pillStagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

const pillItem = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as const },
  },
};

/* ══════════════════════════════════════════════════════════════════════════
   LOGO
   ══════════════════════════════════════════════════════════════════════════ */

const NuuvixxLogoMark = ({ size = "md" }: { size?: "sm" | "md" | "lg" }) => {
  const sizeClasses = {
    sm: "w-7 h-7",
    md: "w-9 h-9",
    lg: "w-12 h-12",
  }[size];

  return (
    <img
      src="/logo.png"
      alt="AgentVerse Logo"
      className={`${sizeClasses} object-contain shrink-0 filter brightness-0 invert transition-transform duration-200 hover:scale-105`}
    />
  );
};

/* ══════════════════════════════════════════════════════════════════════════
   DATA
   ══════════════════════════════════════════════════════════════════════════ */

const CAPABILITIES = [
  { icon: <MemoryRoundedIcon sx={{ fontSize: 20 }} />, label: "MicroVM Isolation" },
  { icon: <LockRoundedIcon sx={{ fontSize: 20 }} />, label: "Zero-Trust Auth" },
  { icon: <BoltRoundedIcon sx={{ fontSize: 20 }} />, label: "Sub-100ms Launch" },
  { icon: <PublicRoundedIcon sx={{ fontSize: 20 }} />, label: "Multi-Region" },
  { icon: <LayersRoundedIcon sx={{ fontSize: 20 }} />, label: "MCP Protocol" },
  { icon: <VerifiedUserRoundedIcon sx={{ fontSize: 20 }} />, label: "OWASP Verified" },
  { icon: <DnsRoundedIcon sx={{ fontSize: 20 }} />, label: "Self-Hosted Ready" },
  { icon: <CodeRoundedIcon sx={{ fontSize: 20 }} />, label: "SDK / CLI" },
];

const PLANS = [
  {
    name: "STARTER",
    price: "$0",
    period: "/ month",
    highlight: false,
    features: [
      "5 active agents",
      "10K tasks / month",
      "Visual Agent Studio",
      "Community support",
      "Console & CLI access",
    ],
  },
  {
    name: "PRO",
    price: "$29",
    period: "/ month",
    highlight: true,
    features: [
      "25 active agents",
      "250K tasks / month",
      "MicroVM sandboxing",
      "Governance & policy engine",
      "Priority execution queue",
      "Custom MCP tools integration",
    ],
  },
  {
    name: "ENTERPRISE",
    price: "Custom",
    period: "",
    highlight: false,
    features: [
      "Unlimited agents & tasks",
      "Dedicated MicroVM clusters",
      "Custom security policies & SSO",
      "99.99% Uptime SLA",
      "24/7 Dedicated engineering lead",
    ],
  },
];

const TRUST_BADGES = [
  "OWASP ASI-01 VERIFIED",
  "SOC 2 TYPE II",
  "ZERO TRUST",
  "GDPR READY",
  "99.99% SLA",
];

const CLI_LINES = [
  { c: "#57595B", t: "# Install the Nuuvixx CLI" },
  { c: "#E5252A", t: "$ npx nuuvixx init" },
  { c: "#57595B", t: "" },
  { c: "#57595B", t: "# Define your agent" },
  { c: "#C9C4B6", t: 'agent "summarizer" {' },
  { c: "#C9C4B6", t: '  model = "gpt-4o"' },
  { c: "#C9C4B6", t: '  runtime = "microvm"' },
  { c: "#C9C4B6", t: "  trust_threshold = 0.95" },
  { c: "#C9C4B6", t: "}" },
  { c: "#57595B", t: "" },
  { c: "#57595B", t: "# Deploy to AgentVerse" },
  { c: "#E5252A", t: "$ nuuvixx deploy --env prod" },
  { c: "#34d399", t: "✓ Agent spawned · ID: ag_7f2a9c · MicroVM ready" },
];

const STEPS = [
  {
    n: "01",
    icon: <ConstructionRoundedIcon sx={{ fontSize: 22, color: "#F2EFE7" }} />,
    title: "BUILD",
    desc: "Define agents in YAML or our visual Studio. Select models, memory, tools, and trust thresholds.",
  },
  {
    n: "02",
    icon: <BoltRoundedIcon sx={{ fontSize: 22, color: "#F2EFE7" }} />,
    title: "DEPLOY",
    desc: "Push to AgentVerse with one command. Auto-provisioned MicroVM, cryptographic ID, and health monitoring.",
  },
  {
    n: "03",
    icon: <TrendingUpRoundedIcon sx={{ fontSize: 22, color: "#F2EFE7" }} />,
    title: "MONETIZE",
    desc: "Publish to the AgentStore marketplace. Set per-task pricing. Revenue settled in real-time.",
  },
];

/* ══════════════════════════════════════════════════════════════════════════
   PAGE
   ══════════════════════════════════════════════════════════════════════════ */

export default function LandingPage() {
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  // Ref for the hero section — drives all scroll transforms
  const heroRef = useRef<HTMLElement>(null);

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  /* ── Scroll-driven transforms ──────────────────────────────────────── */

  // Video slowly zooms in as you scroll past hero
  const videoScale = useTransform(
    scrollYProgress,
    [0, 1],
    shouldReduceMotion ? [1, 1] : [1, 1.08]
  );

  const heroContentY = useTransform(
    scrollYProgress,
    [0, 1],
    shouldReduceMotion ? [0, 0] : [0, 60]
  );

  const heroOpacity = useTransform(
    scrollYProgress,
    [0, 0.85],
    [1, 0.3]
  );

  /* ── Nav scroll detection ──────────────────────────────────────────── */
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText("npx nuuvixx init");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="min-h-screen w-full overflow-x-hidden"
      style={{ backgroundColor: "#F2EFE7", color: "#2E3033" }}
    >
      {/* ════════════════════════════════════════════════════════════════
          FLOATING NAV
          ════════════════════════════════════════════════════════════════ */}
      <motion.nav
        className="fixed top-5 left-1/2 -translate-x-1/2 z-50 w-[94%] max-w-6xl px-6 sm:px-8 py-3 rounded-full backdrop-blur-2xl flex items-center justify-between"
        animate={{
          backgroundColor: scrolled ? "rgba(46,48,51,0.96)" : "rgba(46,48,51,0.85)",
          borderColor: scrolled ? "rgba(201,196,182,0.4)" : "rgba(201,196,182,0.2)",
          boxShadow: scrolled
            ? "0 16px 36px rgba(0,0,0,0.35)"
            : "0 8px 24px rgba(0,0,0,0.2)",
        }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        style={{ border: "1px solid rgba(201,196,182,0.2)" }}
      >
        {/* Logo */}
        <a href="#hero" className="flex items-center gap-3 shrink-0 cursor-pointer">
          <NuuvixxLogoMark size="sm" />
          <span
            className="text-lg sm:text-xl font-bold tracking-widest uppercase"
            style={{ fontFamily: "'Black Ops One', 'Anton', sans-serif", letterSpacing: "0.15em" }}
          >
            <span className="text-white">AGENT</span>
            <span style={{ color: "#E5252A" }}>VERSE</span>
          </span>
        </a>

        {/* Links */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10">
          {[
            { name: "Platform",    href: "#platform" },
            { name: "Marketplace", href: "https://agentstore.nuuvixx.com" },
            { name: "Governance",  href: "#governance" },
            { name: "Docs",        href: "/docs" },
          ].map((item) => 
            item.href.startsWith("/") ? (
              <Link
                key={item.name}
                href={item.href}
                className="px-4 py-1.5 rounded-full text-sm font-semibold tracking-wider uppercase transition-all duration-200 hover:bg-white/15 hover:text-white cursor-pointer"
                style={{ color: "#C9C4B6", fontFamily: "'JetBrains Mono', monospace" }}
              >
                {item.name}
              </Link>
            ) : (
              <a
                key={item.name}
                href={item.href}
                className="px-4 py-1.5 rounded-full text-sm font-semibold tracking-wider uppercase transition-all duration-200 hover:bg-white/15 hover:text-white cursor-pointer"
                style={{ color: "#C9C4B6", fontFamily: "'JetBrains Mono', monospace" }}
              >
                {item.name}
              </a>
            )
          )}
        </div>

        {/* CTAs */}
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/login"
            className="hidden sm:block px-4 py-2 rounded-full text-sm font-semibold tracking-wider uppercase transition-all hover:bg-white/10 cursor-pointer"
            style={{ color: "#F2EFE7", fontFamily: "'JetBrains Mono', monospace" }}
          >
            Sign In
          </Link>
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Link
              href="/register"
              className="px-6 py-2.5 rounded-full text-sm font-bold tracking-widest uppercase transition-all inline-block cursor-pointer"
              style={{
                backgroundColor: "#E5252A",
                color: "#FFFFFF",
                fontFamily: "'Black Ops One', 'Anton', sans-serif",
                letterSpacing: "0.1em",
                boxShadow: "0 2px 10px rgba(229,37,42,0.25)",
              }}
            >
              Launch Console
            </Link>
          </motion.div>
        </div>
      </motion.nav>

      {/* ════════════════════════════════════════════════════════════════
          HERO SECTION WITH BACKGROUND VIDEO
          ════════════════════════════════════════════════════════════════ */}
      <section
        ref={heroRef}
        className="relative min-h-[92vh] sm:min-h-screen w-full flex flex-col justify-center overflow-hidden"
      >
        {/* Background video with subtle zoom */}
        <motion.div
          className="absolute inset-0 w-full h-full"
          style={{ scale: videoScale, transformOrigin: "center center" }}
        >
          <video
            src="/Hero_section.mp4"
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        </motion.div>

        {/* Crisp dark gradient overlay so text is 100% readable */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "linear-gradient(to bottom, rgba(14,15,18,0.60) 0%, rgba(14,15,18,0.72) 45%, rgba(14,15,18,0.94) 100%)",
          }}
        />

        {/* ── Hero Content ──────────────────────────────────────────── */}
        <motion.div
          className="relative z-20 flex-1 flex flex-col items-center justify-center px-4 pt-32 sm:pt-36 pb-16 sm:pb-20 text-center"
          style={{ y: heroContentY, opacity: heroOpacity }}
        >
          {/* Badge */}
          <div className="flex justify-center mb-4 sm:mb-5">
            <motion.div
              className="inline-flex items-center gap-2 px-4 sm:px-5 py-1.5 sm:py-2 rounded-full text-[11px] sm:text-xs tracking-widest uppercase shadow-lg"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
              style={{
                backgroundColor: "rgba(17,18,20,0.85)",
                color: "#E2DED4",
                fontFamily: "'JetBrains Mono', monospace",
                border: "1px solid rgba(201,196,182,0.35)",
                backdropFilter: "blur(12px)",
              }}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              ENTERPRISE AI INFRASTRUCTURE · PRODUCTION READY
            </motion.div>
          </div>

          {/* Headline */}
          <motion.h1
            className="leading-tight mb-4 sm:mb-5 uppercase"
            initial={{ opacity: 0, y: 35 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.95, delay: 0.42, ease: [0.16, 1, 0.3, 1] }}
            style={{
              fontFamily: "'Black Ops One', 'Anton', sans-serif",
              fontSize: "clamp(34px, 5vw, 76px)",
              letterSpacing: "0.02em",
              color: "#FFFFFF",
              textShadow: "0 4px 35px rgba(0,0,0,0.8)",
            }}
          >
            The Operating
            <br />
            <span style={{ color: "#E5252A" }}>System</span> for
            <br />
            Agentic AI
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            className="max-w-2xl mx-auto mb-6 sm:mb-8 leading-relaxed font-medium"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.62, ease: [0.16, 1, 0.3, 1] }}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "clamp(12px, 1.35vw, 15px)",
              color: "#D8D3C5",
              textShadow: "0 2px 16px rgba(0,0,0,0.85)",
            }}
          >
            Build, deploy, govern, and monetize autonomous AI agents at enterprise scale.
            <br />
            Cryptographic identity. MicroVM isolation. Real-time decision ledger.
          </motion.p>

          {/* CTAs */}
          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6 sm:mb-7"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.85, delay: 0.82, ease: [0.16, 1, 0.3, 1] }}
          >
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }}>
              <Link
                href="/register"
                className="inline-flex items-center gap-3 px-8 py-3.5 sm:py-4 rounded-full text-sm font-bold tracking-widest uppercase transition-all"
                style={{
                  backgroundColor: "#E5252A",
                  color: "#FFFFFF",
                  fontFamily: "'Anton', sans-serif",
                  letterSpacing: "0.15em",
                  boxShadow: "0 4px 14px rgba(229,37,42,0.25)",
                }}
              >
                START BUILDING FREE
                <ArrowForwardRoundedIcon sx={{ fontSize: 18 }} />
              </Link>
            </motion.div>

            <motion.button
              onClick={handleCopy}
              whileHover={{ backgroundColor: "rgba(255,255,255,0.15)", scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              className="inline-flex items-center gap-3 px-6 py-3.5 sm:py-4 rounded-full text-xs font-medium cursor-pointer shadow-lg"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                color: "#F2EFE7",
                border: "1.5px solid rgba(201,196,182,0.45)",
                backgroundColor: "rgba(17,18,20,0.75)",
                backdropFilter: "blur(12px)",
              }}
            >
              <TerminalRoundedIcon sx={{ fontSize: 16 }} />
              npx nuuvixx init
              {copied ? (
                <CheckRoundedIcon sx={{ fontSize: 14, color: "#22c55e" }} />
              ) : (
                <ContentCopyRoundedIcon sx={{ fontSize: 14 }} />
              )}
            </motion.button>
          </motion.div>

          {/* Trust badges */}
          <motion.div
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2.5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.05 }}
          >
            {TRUST_BADGES.map((t) => (
              <div
                key={t}
                className="flex items-center gap-2 text-[10px] tracking-widest uppercase font-medium"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  color: "#E2DED4",
                  textShadow: "0 1px 8px rgba(0,0,0,0.8)",
                }}
              >
                <CheckRoundedIcon sx={{ fontSize: 13, color: "#34d399" }} />
                {t}
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          TELEMETRY INSTRUMENT PANEL
          ════════════════════════════════════════════════════════════════ */}
      <section className="px-4 md:px-8 max-w-7xl mx-auto pt-16 sm:pt-20 mb-28 relative z-20">
        <motion.div
          className="rounded-3xl overflow-hidden"
          style={{
            backgroundColor: "#2E3033",
            border: "1px solid rgba(201,196,182,0.12)",
            boxShadow: "0 32px 80px rgba(0,0,0,0.12)",
          }}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeUp}
        >
          {/* Terminal bar */}
          <div
            className="flex items-center justify-between px-6 py-4"
            style={{ borderBottom: "1px solid rgba(201,196,182,0.1)" }}
          >
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-red-500 opacity-80" />
              <div className="w-3 h-3 rounded-full bg-yellow-400 opacity-80" />
              <div className="w-3 h-3 rounded-full bg-emerald-400 opacity-80" />
              <span
                className="ml-3 text-xs tracking-widest uppercase"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}
              >
                agentverse-console · live telemetry
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span
                className="text-[10px] tracking-widest"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}
              >
                CONNECTED
              </span>
            </div>
          </div>

          {/* Metrics */}
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-px"
            style={{ backgroundColor: "rgba(201,196,182,0.08)" }}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            variants={stagger}
          >
            {[
              { icon: <SmartToyRoundedIcon sx={{ fontSize: 20 }} />, label: "ACTIVE AGENTS", value: "12,847", sub: "+3.2% today" },
              { icon: <BoltRoundedIcon sx={{ fontSize: 20 }} />, label: "TASKS / MIN", value: "94,203", sub: "peak throughput" },
              { icon: <VerifiedUserRoundedIcon sx={{ fontSize: 20 }} />, label: "TRUST SCORE", value: "98.6%", sub: "org average" },
              { icon: <PaidRoundedIcon sx={{ fontSize: 20 }} />, label: "REVENUE ROUTED", value: "$2.4M", sub: "last 24 hours" },
            ].map((m) => (
              <motion.div
                key={m.label}
                className="px-6 py-6"
                style={{ backgroundColor: "#2E3033" }}
                variants={fadeUp}
              >
                <div className="flex items-center gap-2 mb-3" style={{ color: "#C9C4B6" }}>
                  {m.icon}
                  <span className="text-[10px] tracking-widest uppercase" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    {m.label}
                  </span>
                </div>
                <div
                  className="text-3xl font-bold mb-1"
                  style={{ fontFamily: "'Anton', sans-serif", color: "#F2EFE7", letterSpacing: "-0.01em" }}
                >
                  {m.value}
                </div>
                <div className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: "#57595B" }}>
                  {m.sub}
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Live log stream */}
          <div className="px-6 py-5" style={{ borderTop: "1px solid rgba(201,196,182,0.1)" }}>
            <motion.div
              className="space-y-1.5"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={stagger}
            >
              {[
                { prefix: "→", text: "agent:invoker-7f2a spawned in microvm-pool-09", color: "#C9C4B6" },
                { prefix: "✓", text: "policy:owasp-asi-01 PASSED · latency 2ms", color: "#34d399" },
                { prefix: "↗", text: "task routed to agent:summarizer-v2 · tokens 1,204", color: "#C9C4B6" },
                { prefix: "⬡", text: "trust:score updated 98.6 → 98.7 · cryptographic proof attached", color: "#E5252A" },
              ].map((line, i) => (
                <motion.div
                  key={i}
                  className="flex items-start gap-3"
                  style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}
                  variants={fadeUp}
                >
                  <span style={{ color: line.color, minWidth: 12 }}>{line.prefix}</span>
                  <span style={{ color: "#C9C4B6" }}>{line.text}</span>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          BENTO FEATURES GRID
          ════════════════════════════════════════════════════════════════ */}
      <section id="platform" className="px-4 md:px-8 max-w-7xl mx-auto mb-24">
        <motion.div
          className="text-center mb-14"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={fadeUp}
        >
          <div
            className="text-xs tracking-widest uppercase mb-3"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: "#57595B" }}
          >
            Platform Capabilities
          </div>
          <h2
            className="uppercase"
            style={{
              fontFamily: "'Anton', sans-serif",
              fontSize: "clamp(42px, 6vw, 88px)",
              letterSpacing: "-0.01em",
              color: "#2E3033",
              lineHeight: 1,
            }}
          >
            Everything<br />
            <span style={{ color: "#E5252A" }}>Agents</span> Need
          </h2>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-3"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={stagger}
        >
          {/* Agent Runtime — large */}
          <motion.div
            className="md:col-span-2 rounded-3xl p-8 flex flex-col justify-between min-h-[280px] relative overflow-hidden cursor-pointer"
            style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
            variants={fadeUp}
            whileHover={{ scale: 1.02, y: -5, transition: { duration: 0.22 } }}
          >
            <div>
              <div className="flex items-center gap-3 mb-5">
                <div className="p-2.5 rounded-2xl" style={{ backgroundColor: "rgba(242,239,231,0.08)" }}>
                  <SmartToyRoundedIcon sx={{ fontSize: 28, color: "#F2EFE7" }} />
                </div>
                <span
                  className="text-[10px] tracking-widest uppercase px-3 py-1 rounded-full"
                  style={{ backgroundColor: "rgba(229,37,42,0.15)", color: "#E5252A", fontFamily: "'JetBrains Mono', monospace" }}
                >
                  CORE RUNTIME
                </span>
              </div>
              <h3 className="uppercase mb-3" style={{ fontFamily: "'Anton', sans-serif", fontSize: 40, color: "#F2EFE7", letterSpacing: "-0.01em", lineHeight: 1 }}>
                Agent Runtime
              </h3>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#C9C4B6", lineHeight: 1.75 }}>
                Every agent runs in a hardware-enforced MicroVM sandbox with cryptographic identity,
                isolated networking, and a full decision audit trail. Sub-100ms cold starts.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-6">
              {["MicroVM", "Crypto Identity", "100ms Launch", "Full Audit"].map((tag) => (
                <span
                  key={tag}
                  className="text-[9px] tracking-widest uppercase px-2.5 py-1 rounded-full"
                  style={{ border: "1px solid rgba(201,196,182,0.2)", color: "#C9C4B6", fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="absolute -right-12 -bottom-12 w-48 h-48 rounded-full opacity-[0.04]" style={{ backgroundColor: "#F2EFE7" }} />
          </motion.div>

          {/* Governance */}
          <motion.div
            className="rounded-3xl p-8 flex flex-col justify-between min-h-[280px] relative overflow-hidden cursor-pointer"
            style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
            variants={fadeUp}
            whileHover={{ scale: 1.02, y: -5, transition: { duration: 0.22 } }}
          >
            <div>
              <div className="p-2.5 rounded-2xl mb-4 inline-block" style={{ backgroundColor: "rgba(242,239,231,0.08)" }}>
                <SecurityRoundedIcon sx={{ fontSize: 28, color: "#F2EFE7" }} />
              </div>
              <h3 className="uppercase mb-3" style={{ fontFamily: "'Anton', sans-serif", fontSize: 32, color: "#F2EFE7", letterSpacing: "-0.01em", lineHeight: 1 }}>
                Governance Engine
              </h3>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#C9C4B6", lineHeight: 1.75 }}>
                Policy-as-code enforcement. Real-time OWASP ASI-01 compliance audits on every task invocation.
              </p>
            </div>
            <span
              className="self-start text-[9px] tracking-widest uppercase px-3 py-1 rounded-full mt-4"
              style={{ backgroundColor: "rgba(229,37,42,0.15)", color: "#E5252A", fontFamily: "'JetBrains Mono', monospace" }}
            >
              COMPLIANCE
            </span>
          </motion.div>

          {/* Observability — light card */}
          <motion.div
            className="md:col-span-2 rounded-3xl p-8 flex flex-col justify-between min-h-[220px] relative overflow-hidden cursor-pointer"
            style={{ backgroundColor: "#F2EFE7", border: "1.5px solid #C9C4B6" }}
            variants={fadeUp}
            whileHover={{ scale: 1.02, y: -5, transition: { duration: 0.22 } }}
          >
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 rounded-2xl" style={{ backgroundColor: "#2E3033" }}>
                  <MonitorHeartRoundedIcon sx={{ fontSize: 24, color: "#F2EFE7" }} />
                </div>
                <h3 className="uppercase" style={{ fontFamily: "'Anton', sans-serif", fontSize: 30, color: "#2E3033", letterSpacing: "-0.01em", lineHeight: 1 }}>
                  Observability Suite
                </h3>
              </div>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#57595B", lineHeight: 1.75 }}>
                Sub-millisecond trace latency. Full decision ledger with per-task cost attribution,
                live feed, and cross-agent correlation graphs.
              </p>
            </div>
            <div className="flex items-end gap-1 mt-5 h-10">
              {[60, 80, 45, 95, 70, 88, 55, 100, 72, 90, 65, 85].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-full"
                  style={{ height: `${h}%`, backgroundColor: i === 7 ? "#E5252A" : "#C9C4B6" }}
                />
              ))}
            </div>
          </motion.div>

          {/* Swarm — light card */}
          <motion.div
            className="rounded-3xl p-8 flex flex-col justify-between min-h-[220px] cursor-pointer"
            style={{ backgroundColor: "#F2EFE7", border: "1.5px solid #C9C4B6" }}
            variants={fadeUp}
            whileHover={{ scale: 1.02, y: -5, transition: { duration: 0.22 } }}
          >
            <div>
              <div className="p-2.5 rounded-2xl mb-4 inline-block" style={{ backgroundColor: "#2E3033" }}>
                <AccountTreeRoundedIcon sx={{ fontSize: 24, color: "#F2EFE7" }} />
              </div>
              <h3 className="uppercase mb-3" style={{ fontFamily: "'Anton', sans-serif", fontSize: 28, color: "#2E3033", letterSpacing: "-0.01em", lineHeight: 1 }}>
                Swarm<br />Orchestration
              </h3>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#57595B", lineHeight: 1.75 }}>
                Multi-agent graph execution with circuit breakers, fan-out routing, and dependency resolution.
              </p>
            </div>
          </motion.div>

          {/* Marketplace — full width */}
          <motion.div
            className="md:col-span-3 rounded-3xl p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-8 cursor-pointer"
            style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
            variants={fadeUp}
            whileHover={{ scale: 1.01, y: -3, transition: { duration: 0.22 } }}
          >
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 rounded-2xl" style={{ backgroundColor: "rgba(242,239,231,0.08)" }}>
                  <StorefrontRoundedIcon sx={{ fontSize: 24, color: "#F2EFE7" }} />
                </div>
                <span
                  className="text-[9px] tracking-widest uppercase px-2.5 py-1 rounded-full"
                  style={{ backgroundColor: "rgba(229,37,42,0.15)", color: "#E5252A", fontFamily: "'JetBrains Mono', monospace" }}
                >
                  MONETIZE
                </span>
              </div>
              <h3 className="uppercase mb-3" style={{ fontFamily: "'Anton', sans-serif", fontSize: 38, color: "#F2EFE7", letterSpacing: "-0.01em", lineHeight: 1 }}>
                Agent Marketplace
              </h3>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#C9C4B6", lineHeight: 1.75, maxWidth: 520 }}>
                Publish verified agents. Earn per-task revenue. Built-in A2A commerce protocol with
                cryptographic billing and real-time revenue routing.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 shrink-0">
              {[
                { label: "AGENTS PUBLISHED", value: "4,280" },
                { label: "REVENUE ROUTED", value: "$12.4M" },
                { label: "BUILDERS", value: "1,840" },
                { label: "AVG RATING", value: "4.91★" },
              ].map((s) => (
                <div key={s.label} className="px-5 py-4 rounded-2xl text-center" style={{ backgroundColor: "rgba(242,239,231,0.06)" }}>
                  <div className="text-2xl font-bold mb-0.5" style={{ fontFamily: "'Anton', sans-serif", color: "#F2EFE7" }}>{s.value}</div>
                  <div className="text-[9px] tracking-widest uppercase" style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}>{s.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          CAPABILITIES PILL STRIP
          ════════════════════════════════════════════════════════════════ */}
      <section className="px-4 md:px-8 max-w-7xl mx-auto mb-24">
        <motion.div
          className="rounded-3xl p-8"
          style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeUp}
        >
          <div className="text-center mb-8">
            <h2
              className="uppercase"
              style={{ fontFamily: "'Anton', sans-serif", fontSize: "clamp(28px, 4vw, 52px)", color: "#F2EFE7", letterSpacing: "-0.01em" }}
            >
              Enterprise-Grade <span style={{ color: "#E5252A" }}>By Default</span>
            </h2>
          </div>
          <motion.div
            className="flex flex-wrap justify-center gap-3"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={pillStagger}
          >
            {CAPABILITIES.map((cap) => (
              <motion.div
                key={cap.label}
                className="flex items-center gap-2.5 px-5 py-3 rounded-full cursor-default"
                style={{
                  border: "1px solid rgba(201,196,182,0.2)",
                  color: "#C9C4B6",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  letterSpacing: "0.08em",
                }}
                variants={pillItem}
                whileHover={{
                  borderColor: "rgba(229,37,42,0.5)",
                  color: "#F2EFE7",
                  backgroundColor: "rgba(229,37,42,0.06)",
                  transition: { duration: 0.15 },
                }}
              >
                <span style={{ color: "#F2EFE7" }}>{cap.icon}</span>
                {cap.label}
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          CLI / QUICKSTART + 3-STEP
          ════════════════════════════════════════════════════════════════ */}
      <section id="docs" className="px-4 md:px-8 max-w-7xl mx-auto mb-24">
        <div className="grid md:grid-cols-2 gap-6">
          {/* Code block */}
          <motion.div
            className="rounded-3xl p-8"
            style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={fadeUp}
          >
            <div
              className="text-xs tracking-widest uppercase mb-4"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}
            >
              <TerminalRoundedIcon sx={{ fontSize: 14, mr: 0.5 }} /> Quickstart · 60 Seconds
            </div>
            <motion.div
              className="rounded-2xl p-5 space-y-2 text-xs"
              style={{ backgroundColor: "#111214", fontFamily: "'JetBrains Mono', monospace" }}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={stagger}
            >
              {CLI_LINES.map((l, i) => (
                <motion.div key={i} style={{ color: l.c }} variants={fadeUp}>
                  {l.t || "\u00a0"}
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* 3 steps */}
          <motion.div
            className="flex flex-col gap-4"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={stagger}
          >
            {STEPS.map((step) => (
              <motion.div
                key={step.n}
                className="flex items-start gap-5 p-6 rounded-3xl cursor-default"
                style={{ backgroundColor: "#F2EFE7", border: "1.5px solid #C9C4B6" }}
                variants={fadeLeft}
                whileHover={{ x: 5, transition: { duration: 0.2 } }}
              >
                <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl" style={{ backgroundColor: "#2E3033" }}>
                  {step.icon}
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1.5">
                    <span className="text-[9px] tracking-widest" style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}>
                      STEP {step.n}
                    </span>
                    <span className="text-lg" style={{ fontFamily: "'Anton', sans-serif", color: "#2E3033", letterSpacing: "0.05em" }}>
                      {step.title}
                    </span>
                  </div>
                  <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#57595B", lineHeight: 1.75 }}>
                    {step.desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          ARCHITECTURE & COMPARISON MATRIX (AMOEBA-INSPIRED)
          ════════════════════════════════════════════════════════════════ */}
      <section id="comparison" className="px-4 md:px-8 max-w-7xl mx-auto mb-24">
        <motion.div
          className="text-center mb-14"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={fadeUp}
        >
          <div className="text-xs tracking-widest uppercase mb-3" style={{ fontFamily: "'JetBrains Mono', monospace", color: "#57595B" }}>
            Architectural Comparison
          </div>
          <h2
            className="uppercase"
            style={{ fontFamily: "'Anton', sans-serif", fontSize: "clamp(42px, 6vw, 88px)", color: "#2E3033", letterSpacing: "-0.01em", lineHeight: 1 }}
          >
            Why Teams Choose<br /><span style={{ color: "#E5252A" }}>AgentVerse</span>
          </h2>
        </motion.div>

        <motion.div
          className="rounded-3xl p-6 sm:p-10 border shadow-2xl overflow-x-auto"
          style={{ backgroundColor: "#2E3033", borderColor: "rgba(201,196,182,0.15)" }}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={fadeUp}
        >
          <table className="w-full text-left font-mono text-xs border-collapse min-w-[640px]">
            <thead>
              <tr className="border-b border-[#C9C4B6]/20 text-[#C9C4B6] uppercase tracking-wider text-[11px]">
                <th className="py-4 px-4 font-bold w-1/3">CAPABILITY</th>
                <th className="py-4 px-4 font-bold text-neutral-400 w-1/3">LEGACY FRAMEWORKS</th>
                <th className="py-4 px-4 font-bold text-[#38D9A9] w-1/3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#38D9A9] animate-pulse" />
                  <span>AGENTVERSE MULTIPLAYER</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#C9C4B6]/10 text-[#F2EFE7]">
              {[
                {
                  cap: "Execution Isolation",
                  legacy: "Shared Docker containers / process threads",
                  agentverse: "Firecracker MicroVM (Hardware level)",
                },
                {
                  cap: "Tool Protocol Standard",
                  legacy: "Ad-hoc REST/Python wrappers",
                  agentverse: "Native Model Context Protocol (MCP)",
                },
                {
                  cap: "Cold Start Latency",
                  legacy: "12s – 45s container spin-up",
                  agentverse: "Sub-100ms MicroVM instant boot",
                },
                {
                  cap: "Security & Audit",
                  legacy: "Unverified console logs",
                  agentverse: "SHA-256 Decision Ledger & OWASP ASI-01",
                },
                {
                  cap: "Swarm Collaboration",
                  legacy: "Single-threaded blocking loops",
                  agentverse: "Multiplayer Real-time A2A Swarm Graphs",
                },
                {
                  cap: "Marketplace & Monetization",
                  legacy: "Custom code deployment only",
                  agentverse: "1-Click AgentStore Manifest Publishing",
                },
              ].map((row, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-5 px-4 font-bold text-[#F2EFE7] tracking-wide">{row.cap}</td>
                  <td className="py-5 px-4 text-neutral-400">{row.legacy}</td>
                  <td className="py-5 px-4 text-[#38D9A9] font-bold bg-[#38D9A9]/5 rounded-xl">
                    {row.agentverse}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          FINAL CTA
          ════════════════════════════════════════════════════════════════ */}
      <section className="px-4 md:px-8 max-w-7xl mx-auto mb-16">
        <motion.div
          className="rounded-3xl px-8 py-20 text-center relative overflow-hidden"
          style={{ backgroundColor: "#2E3033", border: "1px solid rgba(201,196,182,0.08)" }}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeUp}
        >
          {/* Grid pattern */}
          <div
            className="absolute inset-0 opacity-[0.035]"
            style={{
              backgroundImage:
                "repeating-linear-gradient(0deg, #F2EFE7 0px, #F2EFE7 1px, transparent 1px, transparent 48px), repeating-linear-gradient(90deg, #F2EFE7 0px, #F2EFE7 1px, transparent 1px, transparent 48px)",
            }}
          />
          {/* Ambient crimson glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: "radial-gradient(circle at 50% 50%, rgba(229,37,42,0.07) 0%, transparent 70%)" }}
          />

          <div className="relative z-10">
            <div className="text-xs tracking-widest uppercase mb-6" style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}>
              <AutoAwesomeRoundedIcon sx={{ fontSize: 12, mr: 0.5 }} /> The Future Is Agentic
            </div>
            <h2
              className="uppercase mb-6"
              style={{ fontFamily: "'Anton', sans-serif", fontSize: "clamp(44px, 7vw, 104px)", color: "#F2EFE7", letterSpacing: "-0.01em", lineHeight: 1 }}
            >
              Start Building<br /><span style={{ color: "#E5252A" }}>Today</span>
            </h2>
            <p className="max-w-lg mx-auto mb-10" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: "#C9C4B6", lineHeight: 1.75 }}>
              Join 1,800+ teams building the next generation of autonomous AI infrastructure
              on AgentVerse. Free tier includes 3 agents and 1K tasks per day.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <motion.div whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.97 }}>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-3 px-10 py-4 rounded-full text-sm font-bold tracking-widest uppercase"
                  style={{
                    backgroundColor: "#F2EFE7",
                    color: "#2E3033",
                    fontFamily: "'Anton', sans-serif",
                    letterSpacing: "0.15em",
                    boxShadow: "0 8px 40px rgba(242,239,231,0.15)",
                  }}
                >
                  LAUNCH FREE CONSOLE
                  <ArrowForwardRoundedIcon sx={{ fontSize: 18 }} />
                </Link>
              </motion.div>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-xs font-medium tracking-widest uppercase transition-all hover:bg-white/10"
                style={{ color: "#C9C4B6", fontFamily: "'JetBrains Mono', monospace", border: "1px solid rgba(201,196,182,0.2)" }}
              >
                Sign In
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          FOOTER (CHARCOAL STONE + TECHNICAL GRID)
          ════════════════════════════════════════════════════════════════ */}
      <footer
        className="relative px-4 md:px-8 py-12 overflow-hidden"
        style={{
          backgroundColor: "#2E3033",
          borderTop: "1px solid rgba(201,196,182,0.12)",
        }}
      >
        {/* Engineering grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.035] pointer-events-none"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, #F2EFE7 0px, #F2EFE7 1px, transparent 1px, transparent 48px), repeating-linear-gradient(90deg, #F2EFE7 0px, #F2EFE7 1px, transparent 1px, transparent 48px)",
          }}
        />

        <div className="relative z-10 max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <NuuvixxLogoMark size="sm" />
            <span
              className="text-base font-bold tracking-widest uppercase"
              style={{ fontFamily: "'Black Ops One', 'Anton', sans-serif", letterSpacing: "0.18em" }}
            >
              <span className="text-white">AGENT</span>
              <span style={{ color: "#E5252A" }}>VERSE</span>
            </span>
          </div>

          {/* Nav links */}
          <div className="flex flex-wrap items-center justify-center gap-6">
            {[
              { name: "Platform", href: "#platform" },
              { name: "Marketplace", href: "http://localhost:8050/" },
              { name: "Governance", href: "#governance" },
              { name: "Comparison", href: "#comparison" },
              { name: "Docs", href: "/docs" },
            ].map((item) => 
              item.href.startsWith("/") ? (
                <Link
                  key={item.name}
                  href={item.href}
                  className="text-xs tracking-widest uppercase transition-colors hover:text-white cursor-pointer"
                  style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}
                >
                  {item.name}
                </Link>
              ) : (
                <a
                  key={item.name}
                  href={item.href}
                  className="text-xs tracking-widest uppercase transition-colors hover:text-white cursor-pointer"
                  style={{ fontFamily: "'JetBrains Mono', monospace", color: "#C9C4B6" }}
                >
                  {item.name}
                </a>
              )
            )}
          </div>

          {/* System status & copyright */}
          <div
            className="flex items-center gap-2"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#C9C4B6", letterSpacing: "0.08em" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span style={{ color: "#34d399" }}>ALL SYSTEMS OPERATIONAL</span>
            <span className="opacity-30">·</span>
            <span>© 2026 NUUVIXX</span>
          </div>
        </div>
      </footer>
    </div>
  );
}