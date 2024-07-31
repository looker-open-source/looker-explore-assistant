// tailwind.config.js
const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: ['./src/**/*.{html,js,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Google Sans', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        primary: '#1a73e8', // Google Blue
        secondary: '#ea4335', // Google Red
        tertiary: '#fbbc05', // Google Yellow
        quaternary: '#34a853', // Google Green
        gray: {
          ...defaultTheme.colors.gray,
          900: '#202124', // Google Dark Gray
          800: '#303134', // Google Lighter Dark Gray
          700: '#5f6368', // Google Medium Gray
        },
      },
    },
  },
  plugins: [],
}
