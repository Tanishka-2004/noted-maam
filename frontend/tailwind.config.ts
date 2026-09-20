import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        burgundy: {
          deep: "#4A1724",
          primary: "#681F32",
          rich: "#7A2940",
          muted: "#96546A",
          dusty: "#F4E8EA",
        },
        cream: {
          warm: "#F7F1E5",
          soft: "#FBF8F1",
          dark: "#E9DFCE",
        },
        beige: {
          muted: "#CDBEA9",
        },
      },
    },
  },
  plugins: [],
};
export default config;
