/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // ChemFetch Brand Colors (matching website)
        primary: '#2563eb',
        'primary-dark': '#1d4ed8',
        secondary: '#64748b',
        accent: '#06b6d4',
        'text-primary': '#1f2937',
        'text-secondary': '#6b7280',
        'bg-primary': '#ffffff',
        'bg-secondary': '#f8fafc',
        'border-color': '#e5e7eb',
        // Additional colors for better mobile experience
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
        light: {
          100: '#f8fafc',
          200: '#f1f5f9',
          300: '#e2e8f0',
        },
        dark: {
          100: '#334155',
          200: '#1e293b',
          300: '#0f172a',
        },
      },
      fontFamily: {
        sans: ['System'],
      },
      borderRadius: {
        xl: '12px',
        '2xl': '16px',
      },
      spacing: {
        18: '4.5rem',
        88: '22rem',
      },
    },
  },
  plugins: [],
};
