import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dual-layer rendering palette. Greens for grounded evidence, reds for
        // unmatched red-flag rule spans. Tuned so they remain readable when both
        // layers cover overlapping characters (SPEC §A.2).
        evidence: {
          50: "#ecfdf5",
          200: "#a7f3d0",
          500: "#10b981",
          700: "#047857",
        },
        redflag: {
          50: "#fef2f2",
          200: "#fecaca",
          500: "#ef4444",
          700: "#b91c1c",
        },
        interpretation: {
          50: "#fffbeb",
          200: "#fde68a",
          500: "#f59e0b",
          700: "#b45309",
        },
      },
    },
  },
  plugins: [],
};

export default config;
