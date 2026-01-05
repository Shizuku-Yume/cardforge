/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,html}',
  ],
  theme: {
    extend: {
      borderRadius: {
        'neo': '0.75rem',    // 12px
        'neo-lg': '1rem',    // 16px
      },
      boxShadow: {
        'neo-lift': '0 4px 20px -4px rgba(0,0,0,0.05), 0 -2px 10px -2px rgba(255,255,255,0.8)',
        'neo-lift-hover': '0 6px 24px -4px rgba(0,0,0,0.08), 0 -2px 12px -2px rgba(255,255,255,0.9)',
        'neo-inset': 'inset 0 2px 4px rgba(0,0,0,0.04)',
      },
      colors: {
        brand: {
          DEFAULT: '#0f766e', // teal-700
          light: '#f0fdfa',   // teal-50
          dark: '#115e59',    // teal-800
        },
        warning: {
          DEFAULT: '#b45309', // amber-700
          light: '#fffbeb',   // amber-50
          dark: '#92400e',    // amber-800
        },
        danger: {
          DEFAULT: '#b91c1c', // red-700
          light: '#fef2f2',   // red-50
          dark: '#991b1b',    // red-800
        },
      },
      keyframes: {
        'cursor-blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      animation: {
        'cursor-blink': 'cursor-blink 1s step-end infinite',
      },
      typography: {
        DEFAULT: {
          css: {
            '--tw-prose-body': 'rgb(63 63 70)',        // zinc-700
            '--tw-prose-headings': 'rgb(39 39 42)',    // zinc-800
            '--tw-prose-links': 'rgb(15 118 110)',     // teal-700
            '--tw-prose-bold': 'rgb(39 39 42)',        // zinc-800
            '--tw-prose-code': 'rgb(15 118 110)',      // teal-700
            '--tw-prose-pre-bg': 'rgb(244 244 245)',   // zinc-100
            '--tw-prose-pre-code': 'rgb(63 63 70)',    // zinc-700
            '--tw-prose-quotes': 'rgb(113 113 122)',   // zinc-500
            '--tw-prose-quote-borders': 'rgb(15 118 110)', // teal-700
            fontSize: '0.9375rem',
            lineHeight: '1.7',
            'code::before': { content: '""' },
            'code::after': { content: '""' },
            code: {
              backgroundColor: 'rgb(244 244 245)',
              padding: '0.125rem 0.375rem',
              borderRadius: '0.25rem',
              fontWeight: '400',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
