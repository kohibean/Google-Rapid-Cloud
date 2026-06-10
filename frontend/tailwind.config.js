/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7",
        ink: {
          DEFAULT: "#1A1815",
          soft: "#6B6660",
        },
        rule: "#E8E5DD",
        accent: {
          DEFAULT: "#B5532A",
          deep: "#8F3D1C",
        },
        stage: {
          sketch: "#9A8F7A",
          early: "#C08A2D",
          late: "#B5532A",
          final: "#6B7256",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        serif: ['"Newsreader"', "Georgia", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      letterSpacing: {
        smallcaps: "0.18em",
      },
      maxWidth: {
        page: "1440px",
        prose: "68ch",
      },
    },
  },
  plugins: [],
}
