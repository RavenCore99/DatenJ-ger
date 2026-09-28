import { useApp } from '../estado/ProveedorApp.jsx'
import { SECCIONES } from '../App.jsx'

/** Barra lateral de navegación entre los paneles del sistema. */
export default function BarraLateral({ seccion, onSeleccionar }) {
  return (
    <nav className="flex w-60 shrink-0 flex-col border-r border-borde bg-superficie">
      <div className="flex items-center gap-3 px-5 py-5">
        <Logo />
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight">DatenJäger</p>
          <p className="text-[11px] text-tenue">Gestión documental</p>
        </div>
      </div>

      <ul className="flex flex-col gap-1 px-3 py-2">
        {SECCIONES.map(({ clave, titulo, descripcion }) => {
          const activa = clave === seccion
          return (
            <li key={clave}>
              <button
                type="button"
                onClick={() => onSeleccionar(clave)}
                aria-current={activa ? 'page' : undefined}
                className={[
                  'group flex w-full flex-col items-start rounded-lg px-3 py-2 text-left transition-colors',
                  activa
                    ? 'bg-primario/10 text-primario'
                    : 'text-texto hover:bg-fondo',
                ].join(' ')}
              >
                <span className="text-sm font-medium">{titulo}</span>
                <span className="text-[11px] text-tenue">{descripcion}</span>
              </button>
            </li>
          )
        })}
      </ul>

      <div className="mt-auto border-t border-borde px-5 py-4">
        <BotonTema />
      </div>
    </nav>
  )
}

function BotonTema() {
  const { tema, alternarTema } = useApp()

  return (
    <button
      type="button"
      onClick={alternarTema}
      className="w-full rounded-lg border border-borde px-3 py-2 text-xs font-medium text-tenue transition-colors hover:text-texto"
    >
      {tema === 'oscuro' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
    </button>
  )
}

/**
 * Marca del proyecto: círculo azul con anillo y ave.
 * Provisional — el logo definitivo llega con los assets de la Fase 3.
 */
function Logo() {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#0D0F1A] ring-2 ring-primario">
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" aria-hidden="true">
        <path
          fill="currentColor"
          d="M4 14c3.2-.4 5.6-1.9 7.4-4.4.5-.7.9-1.5 1.2-2.3 1.6 1 2.5 2.2 2.8 3.6.3 1.5-.1 3-1.2 4.4-1.9 2.4-4.9 3.4-8.4 3l-1.8-4.3Z"
        />
      </svg>
    </span>
  )
}