/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0F14",
        surface: "#11161D",
        "surface-raised": "#161D27",
        border: "#1F2832",
        "border-bright": "#2A3744",
        ink: "#E7EDF3",
        muted: "#8A97A6",
        faint: "#5C6876",
        signal: "#27E6A6",
        "signal-dim": "#1A9E73",
        miss: "#FF6B5B",
        info: "#5B8DEF",
        warn: "#F5B544",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(39,230,166,0.15), 0 0 24px rgba(39,230,166,0.08)",
      },
      keyframes: {
        pulse_dot: {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.4, transform: "scale(0.85)" },
        },
        flow: {
          "0%": { strokeDashoffset: "40" },
          "100%": { strokeDashoffset: "0" },
        },
      },
      animation: {
        pulse_dot: "pulse_dot 1.8s ease-in-out infinite",
        flow: "flow 1s linear infinite",
      },
    },
  },
  plugins: [],
};
