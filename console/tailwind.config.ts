import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#070709",
        surface: {
          50: "#16161d",
          100: "#0e0e12",
          200: "#121217",
          300: "#070709",
          border: "rgba(220, 38, 38, 0.28)",
          "border-strong": "rgba(220, 38, 38, 0.55)",
          hover: "#1f1416",
        },
        crimson: {
          50: "#fef2f2",
          100: "#fee2e2",
          200: "#fecaca",
          300: "#fca5a5",
          400: "#f87171",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
          800: "#991b1b",
          900: "#7f1d1d",
          950: "#450a0a",
        },
        primary: {
          DEFAULT: "#dc2626",
          hover: "#ef4444",
          light: "#f87171",
          glow: "rgba(220, 38, 38, 0.4)",
        },
        accent: {
          cyan: "#06B6D4",
          purple: "#A855F7",
          emerald: "#10B981",
          amber: "#F59E0B",
          rose: "#F43F5E",
          crimson: "#dc2626",
        },
        ruby: "#e50914",
        text: {
          primary: "#F8FAFC",
          secondary: "#94A3B8",
          muted: "#64748B",
          dim: "#475569",
        },
      },
      fontFamily: {
        display: ['"Anton"', '"Oswald"', '"Bebas Neue"', "sans-serif"],
        condensed: ['"Oswald"', '"Bebas Neue"', "sans-serif"],
        sans: ['"Plus Jakarta Sans"', '"Inter"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
        blackops: ['var(--font-black-ops-one)', '"Black Ops One"', "Impact", "sans-serif"],
      },
      backgroundImage: {
        "radial-crimson": "radial-gradient(circle at 50% 20%, rgba(220, 38, 38, 0.22) 0%, transparent 65%)",
        "radial-ambient-left": "radial-gradient(circle at 10% 40%, rgba(185, 28, 28, 0.18) 0%, transparent 50%)",
        "radial-ambient-right": "radial-gradient(circle at 90% 30%, rgba(220, 38, 38, 0.20) 0%, transparent 55%)",
        "card-crimson-gradient": "linear-gradient(135deg, rgba(185, 28, 28, 0.85) 0%, rgba(80, 10, 14, 0.95) 45%, rgba(18, 18, 22, 0.98) 100%)",
        "card-crimson-vibrant": "radial-gradient(circle at 75% 20%, #b91c1c 0%, #7f1d1d 40%, #15151b 95%)",
        "card-dark-gradient": "linear-gradient(180deg, #18181f 0%, #0d0d12 100%)",
      },
      boxShadow: {
        "crimson-glow": "0 0 35px rgba(220, 38, 38, 0.35)",
        "crimson-glow-strong": "0 0 50px rgba(220, 38, 38, 0.6)",
        "card-glow": "0 10px 30px -10px rgba(220, 38, 38, 0.25)",
      },
      animation: {
        "pulse-glow": "pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "subtle-fade": "fadeIn 0.3s ease-in-out",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
