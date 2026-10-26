/** Dashboard CSS. Rebuild after changing classes in web/: `npm install && npm run build:css` */
module.exports = {
  darkMode: 'class',
  content: ['./web/**/*.{html,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
};
