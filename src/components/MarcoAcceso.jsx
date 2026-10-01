import logo from '../../assets/logo/logo.png'
import Icono from './Icono.jsx'
import Particulas from './Particulas.jsx'

/**
 * Marco de las pantallas de acceso (SCRUM-29): cabecera de ventana con la marca
 * y el estado de cifrado, y franja de telemetría al pie, con las mismas
 * densidades que el marco del sistema (48px y 32px).
 *
 * Los mockups dibujan un semáforo de ventana estilo macOS; aquí no se imita
 * porque la ventana de Electron conserva su marco nativo en Linux y Windows, y
 * unos botones que no hacen nada serían decoración engañosa.
 *
 * **El fondo de marca es del marco, no de una pantalla** (calidad de vida): la
 * marca de agua con el nombre y el campo de partículas vivían dentro de la
 * bienvenida, así que desaparecían al pasar al acceso o al registro. Al subirlos
 * aquí, las tres pantallas del portal comparten el mismo fondo y el cambio entre
 * ellas se siente continuo en vez de un salto a una página distinta.
 */
export default function MarcoAcceso({ titulo, subtitulo, onVolver, children }) {
  return (
    <div className="flex h-full w-full flex-col bg-fondo text-texto">
      <header className="flex h-cabecera shrink-0 items-center justify-between gap-4 border-b border-borde bg-superficie px-4">
        <div className="flex min-w-0 items-center gap-3">
          <img src={logo} alt="" className="h-7 w-7 shrink-0 rounded-full object-contain" />

          <div className="flex min-w-0 items-baseline gap-2">
            <span className="truncate font-marca text-etiqueta-md font-semibold tracking-tight">
              DatenJäger
            </span>
            <span aria-hidden="true" className="text-borde-fuerte">
              ·
            </span>
            <span className="truncate text-etiqueta-sm text-tenue">{titulo}</span>
          </div>

          <span className="hidden shrink-0 items-center gap-1.5 rounded border border-borde bg-fondo px-2 py-0.5 font-mono text-telemetria text-tenue sm:flex">
            <span aria-hidden="true" className="inline-block h-1.5 w-1.5 rounded-full bg-exito" />
            AES-256-GCM
          </span>
        </div>

        {onVolver && (
          <button
            type="button"
            onClick={onVolver}
            className="flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1 text-etiqueta-sm text-primario transition-colors hover:bg-fondo-2"
          >
            <Icono nombre="flecha-izquierda" tamano={14} />
            {subtitulo ?? 'Volver'}
          </button>
        )}
      </header>

      {/* El fondo vive aquí para que las tres pantallas del portal lo compartan;
          va detrás del contenido y no captura el puntero. */}
      <div className="relative flex min-h-0 flex-1 flex-col">
        <FondoMarca />
        <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>
      </div>

      <footer className="flex h-telemetria shrink-0 items-center justify-between gap-4 border-t border-borde bg-superficie px-4 font-mono text-telemetria text-tenue">
        <span className="flex min-w-0 items-center gap-2">
          <Icono nombre="candado" tamano={12} className="text-primario" />
          <span className="truncate">Los documentos no salen de este equipo</span>
        </span>
        <span className="shrink-0 text-primario">
          v{__VERSION__} ({__HASH__})
        </span>
      </footer>
    </div>
  )
}

/** Campo de partículas y marca de agua tenue, compartidos por el portal. */
function FondoMarca() {
  return (
    <>
      <Particulas className="pointer-events-none absolute inset-0 h-full w-full" />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 flex select-none items-center justify-center overflow-hidden font-marca text-[16vw] font-bold tracking-tighter text-primario opacity-[0.03]"
      >
        DATENJÄGER
      </span>
    </>
  )
}