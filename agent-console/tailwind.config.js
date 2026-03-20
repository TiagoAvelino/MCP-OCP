/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        rh: {
          red: "#EE0000",
          "red-muted": "#C9190B",
          surface: "#F5F5F7",
          ink: "#151515",
          muted: "#6A6E73",
          border: "#E0E0E0",
          card: "#FFFFFF",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        "card-lg": "0 4px 24px rgba(0,0,0,0.06)",
      },
    },
  },
  plugins: [],
};
