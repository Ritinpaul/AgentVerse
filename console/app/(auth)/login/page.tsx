"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
// MUI Icons
import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import LockRoundedIcon from "@mui/icons-material/LockRounded";
import EmailRoundedIcon from "@mui/icons-material/EmailRounded";
import PersonRoundedIcon from "@mui/icons-material/PersonRounded";
import BusinessRoundedIcon from "@mui/icons-material/BusinessRounded";
import CircularProgress from "@mui/material/CircularProgress";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import VisibilityOffRoundedIcon from "@mui/icons-material/VisibilityOffRounded";
import { loginWithCredentials, registerWithCredentials, demoLogin } from "@/lib/auth";

const ArrowRight = ArrowForwardRoundedIcon;
const AlertCircle = ErrorOutlineRoundedIcon;
const Lock = LockRoundedIcon;
const Mail = EmailRoundedIcon;
const User = PersonRoundedIcon;
const Building2 = BusinessRoundedIcon;

interface AuthComponentProps {
  initialMode?: "signin" | "signup";
}

// ── 3D Isometric AI Cube & Holographic Network Visual Panel ──────────────────
function IsometricAiCubeVisual() {
  return (
    <div className="relative w-full h-full bg-[#0A0C10] overflow-hidden flex items-center justify-center select-none group">
      {/* High-Definition 3D Autonomous AI Infrastructure Video (60fps FastStart + Hardware Accelerated) */}
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        disablePictureInPicture
        className="absolute inset-0 w-full h-full object-cover pointer-events-none"
        style={{
          willChange: "transform",
          transform: "translateZ(0)",
          backfaceVisibility: "hidden",
          filter: "brightness(0.95) contrast(1.05)",
        }}
      >
        <source src="/signup_page.mp4" type="video/mp4" />
      </video>

      {/* Floating Holographic Telemetry Callout Panels */}
      <div className="absolute top-6 left-6 z-20 px-3 py-1.5 rounded-xl bg-[#14171C]/90 border border-red-500/40 backdrop-blur-md shadow-[0_0_20px_rgba(229,37,42,0.3)] flex items-center gap-2 text-[11px] font-mono text-white">
        <span className="w-2 h-2 rounded-full bg-[#E5252A] animate-pulse" />
        <span className="text-neutral-400">ACTIVE AGENTS:</span>
        <span className="font-bold text-white">24</span>
      </div>

      <div className="absolute top-6 right-6 z-20 px-3 py-1.5 rounded-xl bg-[#14171C]/90 border border-emerald-500/40 backdrop-blur-md shadow-[0_0_20px_rgba(52,211,153,0.3)] flex items-center gap-2 text-[11px] font-mono text-white">
        <span className="w-2 h-2 rounded-full bg-emerald-400" />
        <span className="text-neutral-400">TRUST SCORE:</span>
        <span className="font-bold text-white">98.4%</span>
      </div>

      <div className="absolute bottom-6 left-6 z-20 px-3 py-1.5 rounded-xl bg-[#14171C]/90 border border-white/20 backdrop-blur-md shadow-xl flex items-center gap-2 text-[11px] font-mono text-white">
        <span className="text-neutral-400">TELEMETRY</span>
        <span className="text-[#E5252A] text-xs font-bold">∨</span>
      </div>

      <div className="absolute bottom-6 right-6 z-20 px-3 py-1.5 rounded-xl bg-[#14171C]/90 border border-blue-500/40 backdrop-blur-md shadow-[0_0_20px_rgba(59,130,246,0.3)] flex items-center gap-2 text-[11px] font-mono text-white">
        <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
        <span className="text-neutral-400">UPTIME:</span>
        <span className="font-bold text-white">99.9%</span>
      </div>
    </div>
  );
}

// ── Main Authentication Split Component ─────────────────────────────────────
export function AuthSplitExperience({ initialMode = "signin" }: AuthComponentProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [mode, setMode] = useState<"signin" | "signup">(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  
  // Form fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const urlMode = searchParams?.get("mode");
    if (urlMode === "signup") {
      setMode("signup");
    } else if (urlMode === "signin") {
      setMode("signin");
    }
  }, [searchParams]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg("Please enter both email and password.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      await loginWithCredentials(email, password);
      router.push("/console");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to authenticate. Check your credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      setErrorMsg("Please fill out all required fields.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      await registerWithCredentials(email, password, name, orgName);
      router.push("/console");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create account. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async (demoEmail: string, demoRoleName: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    setEmail(demoEmail);
    setPassword("demo-password");

    try {
      await demoLogin(demoEmail, demoRoleName);
      router.push("/console");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to authenticate demo account.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = (targetMode: "signin" | "signup") => {
    setErrorMsg(null);
    setMode(targetMode);
    window.history.replaceState(null, "", targetMode === "signup" ? "/register" : "/login");
  };

  return (
    <div
      className="h-screen max-h-screen w-full flex flex-col items-center justify-start pt-3 sm:pt-5 pb-3 px-3 sm:px-5 gap-3 overflow-hidden selection:bg-red-500/30 selection:text-white"
      style={{ backgroundColor: "#F2EFE7" }}
    >
      {/* ── FLOATING GLASSMORPHIC STADIUM NAVBAR (PULLED UP HIGHER) ───────── */}
      <header className="w-full max-w-[1140px] px-5 sm:px-6 py-2.5 rounded-full bg-[#14171C]/85 backdrop-blur-2xl border border-white/20 shadow-[0_10px_30px_rgba(0,0,0,0.3)] flex items-center justify-between z-30 shrink-0 transition-all">
        {/* Clickable Brand Logo & Icon */}
        <Link
          href="/"
          className="flex items-center gap-2.5 group cursor-pointer transition-transform hover:scale-105"
        >
          <img
            src="/logo.png"
            alt="AgentVerse Logo"
            className="w-6 h-6 sm:w-7 sm:h-7 object-contain filter brightness-0 invert"
          />
          <span
            className="text-lg sm:text-xl font-extrabold tracking-wider uppercase select-none"
            style={{ fontFamily: "'Black Ops One', 'Anton', sans-serif" }}
          >
            <span className="text-white">AGENT</span>
            <span style={{ color: "#E5252A" }}>VERSE</span>
          </span>
        </Link>

        {/* Glass Pill Mode Switcher (SIGN IN / SIGN UP) */}
        <div className="p-1 rounded-full bg-[#101216]/90 border border-white/15 backdrop-blur-md flex items-center gap-1">
          <button
            type="button"
            onClick={() => toggleMode("signin")}
            className={`px-3.5 sm:px-4 py-1 sm:py-1.5 rounded-full text-[11px] font-mono transition-all duration-300 ${
              mode === "signin"
                ? "bg-[#E5252A] text-white font-bold shadow-[0_0_15px_rgba(229,37,42,0.5)]"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            SIGN IN
          </button>
          <button
            type="button"
            onClick={() => toggleMode("signup")}
            className={`px-3.5 sm:px-4 py-1 sm:py-1.5 rounded-full text-[11px] font-mono transition-all duration-300 ${
              mode === "signup"
                ? "bg-[#E5252A] text-white font-bold shadow-[0_0_15px_rgba(229,37,42,0.5)]"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            SIGN UP
          </button>
        </div>
      </header>

      {/* ── 50/50 SPLIT GLASSMORPHIC CONTAINER (PULLED UP CLOSE TO NAVBAR) ── */}
      <div className="w-full max-w-[1140px] h-[82vh] max-h-[610px] min-h-[480px] bg-[#14171C]/80 backdrop-blur-2xl rounded-3xl border border-white/20 shadow-[0_30px_90px_rgba(0,0,0,0.4)] overflow-hidden relative flex transition-all duration-700">
        
        {/* ──── FORM HALF (Slides horizontally on mode toggle) ──────────── */}
        <div
          className={`w-full md:w-1/2 p-6 sm:p-8 flex flex-col justify-between bg-[#181B20]/90 backdrop-blur-xl text-white transition-all duration-700 ease-in-out z-10 ${
            mode === "signup" ? "md:translate-x-full" : "md:translate-x-0"
          }`}
        >
          {/* Header Area */}
          <div>
            {/* Mode Title */}
            <h2 className="text-xl sm:text-2xl font-bold uppercase tracking-tight text-white mb-1 font-sans">
              {mode === "signin" ? "SIGN IN" : "CREATE YOUR ACCOUNT"}
            </h2>
            <p className="text-[11px] text-neutral-400 font-mono mb-4">
              {mode === "signin"
                ? "Access your stateful agent fleets and execution monitor."
                : "Join the verified autonomous AI agent marketplace."}
            </p>

            {/* Error Alert */}
            {errorMsg && (
              <div className="mb-3 p-2.5 rounded-xl text-[11px] font-mono flex items-center gap-2 bg-red-950/80 border border-red-500/40 text-red-200">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Interactive Form */}
            {mode === "signin" ? (
              <form onSubmit={handleSignIn} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Email address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email address"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Password"
                      className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-3 text-neutral-400 hover:text-white"
                    >
                      {showPassword ? <VisibilityOffRoundedIcon className="w-4 h-4" /> : <VisibilityRoundedIcon className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Checkbox & Forgot Password */}
                <div className="flex items-center justify-between text-[11px] text-neutral-400 py-0.5 font-mono">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border-neutral-700 bg-neutral-900 text-[#E5252A] focus:ring-[#E5252A]"
                    />
                    <span>Remember password</span>
                  </label>
                  <a
                    href="mailto:support@nuuvixx.ai?subject=Password Reset Request"
                    className="hover:text-white transition-colors"
                  >
                    Forgot password?
                  </a>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 rounded-xl text-xs font-bold uppercase tracking-widest text-white shadow-[0_0_20px_rgba(229,37,42,0.4)] transition-all flex items-center justify-center gap-2 hover:scale-[1.01] active:scale-95 disabled:opacity-50 mt-1"
                  style={{
                    backgroundColor: "#E5252A",
                    fontFamily: "'Black Ops One', sans-serif",
                    letterSpacing: "0.08em",
                  }}
                >
                  {isLoading ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <span>SIGN IN TO CONSOLE</span>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleSignUp} className="space-y-2.5">
                <div className="space-y-0.5">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe"
                    required
                    className="w-full px-3.5 py-2 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                  />
                </div>

                <div className="space-y-0.5">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Work Email *
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@company.com"
                    required
                    className="w-full px-3.5 py-2 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                  />
                </div>

                <div className="space-y-0.5">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Organization / Namespace
                  </label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Acme Corp"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                  />
                </div>

                <div className="space-y-0.5">
                  <label className="text-[11px] font-medium text-neutral-300 block">
                    Password *
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    className="w-full px-3.5 py-2 rounded-xl bg-[#101216] border border-white/10 text-white text-xs focus:border-[#E5252A] focus:outline-none transition-all placeholder:text-neutral-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 rounded-xl text-xs font-bold uppercase tracking-widest text-white shadow-[0_0_20px_rgba(229,37,42,0.4)] transition-all flex items-center justify-center gap-2 hover:scale-[1.01] active:scale-95 disabled:opacity-50 mt-1"
                  style={{
                    backgroundColor: "#E5252A",
                    fontFamily: "'Black Ops One', sans-serif",
                    letterSpacing: "0.08em",
                  }}
                >
                  {isLoading ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : (
                    <span>CREATE ACCOUNT & START</span>
                  )}
                </button>
              </form>
            )}
          </div>

          {/* Bottom Controls & Security Notice */}
          <div className="pt-3 border-t border-white/10 space-y-2.5">
            {mode === "signin" && (
              <div className="px-3 py-2 rounded-xl bg-[#101216]/80 border border-white/5 text-[10px] font-mono text-neutral-400 text-center space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-emerald-400 font-bold uppercase tracking-wider">
                  <Lock className="w-3 h-3 text-emerald-400" />
                  <span>SaaS IAM Security Enforced</span>
                </div>
                <p className="text-[10px] text-neutral-400 leading-tight">
                  Signing in automatically provisions Owner identity for your personal workspace. Workspace roles are strictly assigned and managed per organisation.
                </p>
              </div>
            )}

            {/* Mode Switcher Footer Link */}
            <div className="text-center text-[11px] text-neutral-400 font-mono">
              {mode === "signin" ? (
                <>
                  Don't have an account?{" "}
                  <button
                    type="button"
                    onClick={() => toggleMode("signup")}
                    className="font-bold text-[#E5252A] hover:underline"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => toggleMode("signin")}
                    className="font-bold text-[#E5252A] hover:underline"
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* ──── 3D ISOMETRIC GRAPHIC HALF (Slides horizontally on mode toggle) ── */}
        <div
          className={`w-full md:w-1/2 h-full transition-all duration-700 ease-in-out ${
            mode === "signup" ? "md:-translate-x-full" : "md:translate-x-0"
          }`}
        >
          <IsometricAiCubeVisual />
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return <AuthSplitExperience initialMode="signin" />;
}