import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#F4EFE4", paper: "#FBF8F1", line: "#E3DAC8",
        ink: "#1C2B3F", inkdeep: "#142033", body: "#2A3442", quiet: "#66707E",
        sage: "#7C9272", dusk: "#58789A", ochre: "#B98A3E",
      },
      fontFamily: {
        serif: ["Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: { soft: "0 1px 2px rgba(28,43,63,0.07)" },
    },
  },
  plugins: [],
} satisfies Config;
