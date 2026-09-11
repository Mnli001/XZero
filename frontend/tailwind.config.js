/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0a0e14",
          panel: "#11161f",
          border: "#1e2633",
          text: "#d7dee8",
          dim: "#8b94a3",
          up: "#26a69a",
          down: "#ef5350",
          accent: "#f0b90b",
          info: "#4da3ff",
        },
      },
      fontFamily: { mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"] },
    },
  },
  plugins: [],
};
