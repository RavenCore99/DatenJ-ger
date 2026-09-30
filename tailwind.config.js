/** @type {import('tailwindcss').Config} */

/*
 * Tokens de Tailwind para DatenJäger (SCRUM-27).
 *
 * Los valores NO se escriben aquí: viven en `src/estilos/tokens.css`, generados
 * desde los DESIGN.md del sistema de diseño ("DatenJäger Precision Desktop")
 * con `@google/design.md export`. Aquí solo se registran para poder escribir
 * utilidades (`bg-superficie`, `text-tenue`, `text-titulo-lg`, `w-lateral`).
 *
 * Los tripletes RGB permiten aplicar opacidad: `bg-superficie/50`.
 */
const conVariable = (nombre) => `rgb(var(--dj-${nombre}) / <alpha-value>)`

// Escala tipográfica del spec (la del modo claro; ver planning.md).
const escala = {
  display: ['48px', { lineHeight: '52px', letterSpacing: '-0.04em', fontWeight: '700' }],
  'titulo-lg': ['32px', { lineHeight: '38px', letterSpacing: '-0.03em', fontWeight: '600' }],
  'titulo-md': ['22px', { lineHeight: '28px', letterSpacing: '-0.02em', fontWeight: '600' }],
  'titulo-sm': ['16px', { lineHeight: '22px', letterSpacing: '-0.01em', fontWeight: '600' }],
  'cuerpo-lg': ['15px', { lineHeight: '24px', fontWeight: '400' }],
  'cuerpo-md': ['13px', { lineHeight: '20px', fontWeight: '400' }],
  'cuerpo-sm': ['12px', { lineHeight: '18px', fontWeight: '400' }],
  'etiqueta-md': ['13px', { lineHeight: '18px', fontWeight: '500' }],
  'etiqueta-sm': ['11px', { lineHeight: '14px', fontWeight: '500' }],
  telemetria: ['11px', { lineHeight: '14px', letterSpacing: '0.02em', fontWeight: '500' }],
  codigo: ['12px', { lineHeight: '18px', fontWeight: '400' }],
}

module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Superficies
        fondo: conVariable('fondo'),
        'fondo-2': conVariable('fondo-2'),
        superficie: conVariable('superficie'),
        'superficie-2': conVariable('superficie-2'),
        'superficie-3': conVariable('superficie-3'),
        'superficie-4': conVariable('superficie-4'),
        lienzo: conVariable('lienzo'),
        cristal: conVariable('cristal'),
        // Líneas
        borde: conVariable('borde'),
        'borde-fuerte': conVariable('borde-fuerte'),
        // Texto
        texto: conVariable('texto'),
        'texto-2': conVariable('texto-2'),
        tenue: conVariable('tenue'),
        // Acción
        primario: conVariable('primario'),
        'primario-enfasis': conVariable('primario-enfasis'),
        'primario-suave': conVariable('primario-suave'),
        'sobre-primario': conVariable('sobre-primario'),
        acento: conVariable('acento'),
        'acento-suave': conVariable('acento-suave'),
        // Estado
        exito: conVariable('exito'),
        alerta: conVariable('alerta'),
        peligro: conVariable('peligro'),
        'peligro-suave': conVariable('peligro-suave'),
        'sobre-peligro': conVariable('sobre-peligro'),
        // Semáforo de la ventana
        'trafico-cerrar': conVariable('trafico-cerrar'),
        'trafico-minimizar': conVariable('trafico-minimizar'),
        'trafico-expandir': conVariable('trafico-expandir'),
      },
      fontFamily: {
        marca: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },
      fontSize: escala,
      borderRadius: {
        // El spec reemplaza la escala de radios de Tailwind.
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.5rem',
        full: '9999px',
        panel: '1rem', // alias del radio de panel del spec
      },
      spacing: {
        gutter: '0.75rem',
        'space-xs': '0.25rem',
        'space-sm': '0.5rem',
        'space-md': '0.75rem',
        'space-lg': '1.25rem',
        'space-xl': '2rem',
      },
      width: {
        lateral: '240px',
        'lateral-min': '64px',
      },
      height: {
        cabecera: '48px',
        telemetria: '32px',
      },
      boxShadow: {
        // Sombra difusa de los elementos flotantes (DESIGN.md, Elevación).
        flotante:
          '0 4px 20px -2px rgba(37, 99, 235, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.04)',
      },
    },
  },
  plugins: [],
}