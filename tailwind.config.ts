import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: 'class', // Add this line
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // your theme config
    },
  },
  plugins: [],
};
export default config;