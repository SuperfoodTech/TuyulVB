/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      spacing: {
        "4.5": "1.125rem",
      },
      colors: {
        zinc: {
          150: "#ececea",
          250: "#d4d4d1",
          350: "#b0b0aa",
          450: "#898984",
          455: "#83837e",
          650: "#454541",
          750: "#333330",
          850: "#20201e",
        },
        brand: {
          red: "#B91C1C",
          "red-hover": "#991B1B",
          white: "#FFFFFF",
          "white-hover": "#F5F4F1",
          card: "#FFFFFF",
          border: "#B91C1C",
          muted: "#78716C",
          dark: "#1C1917",
          light: "#F8F7F4",
        }
      }
    },
  },
  plugins: [],
}
