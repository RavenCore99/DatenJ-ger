/** @type {import('tailwindcss').Config} */

// Paleta base de DatenJäger (ver CLAUDE.md sección 6). Los valores viven en
// un único lugar: `src/index.css` los expone como variables CSS --dj-* y aquí
// se registran como tokens de Tailwind (`bg-superficie`, `text-primario`, ...).
const conVariable = (nombre) => `rgb(var(--dj-${nombre}) / <alpha-value>)`

module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        fondo: conVariable('fondo'),
        superficie: conVariable('superficie'),
        borde: conVariable('borde'),
        primario: conVariable('primario'),
        texto: conVariable('texto'),
        tenue: conVariable('tenue'),
        exito: conVariable('exito'),
        alerta: conVariable('alerta'),
        peligro: conVariable('peligro'),
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        panel: '0.875rem',
      },
    },
  },
  plugins: [],
}