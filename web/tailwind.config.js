/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["\"Source Serif 4\"", "Georgia", "serif"],
        sans: ["\"DM Sans\"", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#0f1c2e",
        mist: "#e8eef5",
        accent: "#0d6e6e",
        warn: "#b45309",
        danger: "#9f1239",
        good: "#047857",
      },
    },
  },
  plugins: [],
};
