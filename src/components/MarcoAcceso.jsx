import logo from '../../assets/logo/logo.png'
import Icono from './Icono.jsx'
import Particulas from './Particulas.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Marco de las pantallas de acceso (SCRUM-29): cabecera de ventana con la marca
 * y franja de telemetría al pie, con las mismas densidades que el marco del
 * sistema (48px y 32px).
 *
 * Los mockups dibujan un semáforo de ventana estilo macOS; aquí no se imita
 * porque la ventana de Electron conserva su marco nativo en Linux y Windows, y
 * unos botones que no harían nada serían decoración engañosa.
 *
 * **La marca de la cabecera es opcional.** La pantalla de bienvenida ya muestra
 * el nombre en grande en su propio contenido, así que repetirlo arriba era
 * redundante (hallazgo de Raven): cuando no se pasa `titulo`, la cabecera deja
 * solo el logo. Acceso y registro sí lo pasan, porque su título no aparece en
 * ningún otro sitio.
 *
 * **El fondo de marca es del marco, no de una pantalla** (calidad de vida): la
 * marca de agua con el nombre y el campo de partículas vivían dentro de la
 * bienvenida, así que desaparecían al pasar al acceso o al registro. Al subirlos
 * aquí, las tres pantallas del portal comparten el mismo fondo y el cambio entre
 * ellas se siente continuo en vez de un salto a una página distinta.
 *
 * **El pie dice la verdad del servicio** (hallazgo de Raven): el cifrado en uso
 * y el estado real de la conexión con el servicio local viven abajo, no en la
 * cabecera, y sustituyen al pie estático «Los documentos no salen de este
 * equipo» —que era una afirmación de marketing, no un dato—.
 */
export default function MarcoAcceso({ titulo, subtitulo, onVolver, children }) {
  return (
    <div className="flex h-full w-full flex-col bg-fondo text-texto">
      <header className="flex h-cabecera shrink-0 items-center justify-between gap-4 border-b border-borde bg-superficie px-4">
        <div className="flex min-w-0 items-center gap-3">
          <img src={logo} alt="" className="h-7 w-7 shrink-0 rounded-full object-contain" />

          {titulo && (
            <div className="flex min-w-0 items-baseline gap-2">
              <span className="truncate font-marca text-etiqueta-md font-semibold tracking-tight">
                DatenJäger
              </span>
              <span aria-hidden="true" className="text-borde-fuerte">
                ·
              </span>
              <span className="truncate text-etiqueta-sm text-tenue">{titulo}</span>
            </div>
          )}
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

      <PiePortal />
    </div>
  )
}

/**
 * Pie del portal: el cifrado en uso y el estado **real** del servicio local a la
 * izquierda, la versión y el hash del build a la derecha. El estado sale de la
 * misma comprobación que alimenta al resto de la aplicación (`useApp`), así que
 * no puede contradecir a lo que muestra el acceso.
 */
function PiePortal() {
  const { conectado, estadoBackend } = useApp()

  const estado = conectado
    ? { punto: 'bg-exito', texto: 'Servicio local conectado' }
    : estadoBackend === 'verificando'
      ? { punto: 'bg-alerta', texto: 'Comprobando el servicio local…' }
      : { punto: 'bg-peligro', texto: 'Servicio local no disponible' }

  return (
    <footer className="flex h-telemetria shrink-0 items-center justify-between gap-4 border-t border-borde bg-superficie px-4 font-mono text-telemetria text-tenue">
      <span className="flex min-w-0 items-center gap-2">
        <span className="flex shrink-0 items-center gap-1.5">
          <Icono nombre="escudo" tamano={12} className="text-primario" />
          AES-256-GCM
        </span>

        <span aria-hidden="true" className="h-3 w-px shrink-0 bg-borde" />

        <span className="flex min-w-0 items-center gap-1.5">
          <span
            aria-hidden="true"
            className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${estado.punto}`}
          />
          <span className="truncate">{estado.texto}</span>
        </span>
      </span>

      <span className="shrink-0 text-primario">
        v{__VERSION__} ({__HASH__})
      </span>
    </footer>
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
