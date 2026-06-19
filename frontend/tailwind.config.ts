import type { Config } from "tailwindcss";

/**
 * Calm, professional palette. Slate-based neutrals, a single restrained accent.
 * No neon, no "command center" theming — the evidence is the focus, not the chrome.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#1e293b", // slate-800
          muted: "#475569", // slate-600
          faint: "#94a3b8", // slate-400
        },
        surface: {
          DEFAULT: "#ffffff",
          sunken: "#f8fafc", // slate-50
          border: "#e2e8f0", // slate-200
        },
        accent: {
          DEFAULT: "#3b6ea5", // muted steel blue
          soft: "#eaf1f8",
        },
        // Confidence bands — muted, legible, non-alarmist.
        band: {
          unverified: "#94a3b8",
          low: "#b45309",
          medium: "#0e7490",
          high: "#2563eb",
          confirmed: "#15803d",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
