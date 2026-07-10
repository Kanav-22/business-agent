import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // validated chart series (dark surface #0f172a)
        revenue: "#199e70",
        expense: "#d95926",
      },
    },
  },
  plugins: [],
};

export default config;
