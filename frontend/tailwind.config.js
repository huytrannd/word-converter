/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#FFFFFF',
          subbg: '#FFF7F7',
          primary: '#E57373',
          hover: '#D65F65',
          border: '#F2CACA',
          text: '#292929',
          subtext: '#777777',
        }
      }
    },
  },
  plugins: [],
}

