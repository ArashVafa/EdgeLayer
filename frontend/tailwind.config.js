/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b0e11',
        surface: '#131720',
        'surface-2': '#1a1f2e',
        'surface-3': '#222838',
        accent: '#06b6d4',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
