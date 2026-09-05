"use client";

import React from "react";
import { StyledEngineProvider, createTheme, ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

// Nuuvixx dark crimson theme — Tailwind wins layout, MUI handles components
const nuuvixxTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#E5252A",
      dark: "#b91c1c",
      light: "#f87171",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#7c3aed",
      contrastText: "#ffffff",
    },
    background: {
      default: "#070709",
      paper: "#0e0e12",
    },
    text: {
      primary: "#f1f5f9",
      secondary: "#94a3b8",
      disabled: "#52525b",
    },
    error: { main: "#fb7185" },
    warning: { main: "#fbbf24" },
    success: { main: "#34d399" },
    divider: "rgba(127,29,29,0.3)",
  },
  typography: {
    fontFamily: "var(--font-sans), system-ui, sans-serif",
    fontSize: 13,
  },
  components: {
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: "#0e0e12",
          border: "1px solid rgba(127,29,29,0.4)",
          color: "#cbd5e1",
          fontSize: "11px",
          fontFamily: "monospace",
        },
        arrow: { color: "#0e0e12" },
      },
      defaultProps: { arrow: true },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          backgroundColor: "#0e0e12",
          border: "1px solid rgba(127,29,29,0.4)",
          borderRadius: 8,
          boxShadow: "0 20px 60px rgba(0,0,0,0.8)",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontFamily: "monospace" },
      },
    },
    MuiCircularProgress: {
      defaultProps: { size: 16 },
    },
  },
  shape: { borderRadius: 8 },
});

export function MuiProvider({ children }: { children: React.ReactNode }) {
  return (
    <StyledEngineProvider injectFirst>
      <ThemeProvider theme={nuuvixxTheme}>
        {/* CssBaseline suppressed — Tailwind handles resets */}
        {children}
      </ThemeProvider>
    </StyledEngineProvider>
  );
}
