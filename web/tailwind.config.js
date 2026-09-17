/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#090B0E",
          900: "#0B0D10",
          850: "#11151A",
          800: "#171B21",
          700: "#1E242E",
          600: "#2A313D",
          500: "#38404D",
        },
        amber: {
          DEFAULT: "#F2B84B",
          bright: "#FFC966",
          dim: "#C8902F",
        },
        coral: {
          DEFAULT: "#FF6B57",
          dim: "#C75A48",
        },
        cyan: {
          DEFAULT: "#5EE0D6",
          dim: "#3E9E98",
        },
        mint: {
          DEFAULT: "#7BE0A3",
          dim: "#57B47C",
        },
      },
      fontFamily: {
        sans: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(242,184,75,0.25), 0 0 24px -6px rgba(242,184,75,0.35)",
        panel: "0 10px 40px -12px rgba(0,0,0,0.65)",
      },
    },
  },
  plugins: [],
};