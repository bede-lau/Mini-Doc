import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        // Sober, paper-and-ink compliance palette. Emerald = grounded/positive,
        // amber = caution/risk, red = critical, slate = neutral structure.
        paper: "#fafaf9",     // stone-50
        ink: "#1c1917",       // stone-900
        rule: "#e7e5e4",      // stone-200
      },
    },
  },
  plugins: [],
};
export default config;
