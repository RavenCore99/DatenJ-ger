import { useApp } from '../estado/ProveedorApp.jsx'
import { urlBase } from '../lib/api.js'
import Icono from './Icono.jsx'

/**
 * Franja de telemetría inferior (SCRUM-28; iconos en SCRUM-65; estado con color
 * de las piezas del sistema en SCRUM-68): `32px` pegados al borde, en
 * monoespaciada de 11px. A la izquierda el estado del servicio, la base de
 * datos, las conexiones de modelos y el chatbot —cada uno con su punto de
 * color—; a la derecha la dirección del servicio y la versión con el hash del
 * build.
 *
 * Solo la base de datos se pinta verde cuando una lectura real ha respondido:
 * las conexiones de modelos y el chatbot aún no tienen configuración (Fase 4),
 * así que se muestran como «sin configurar», no como si estuvieran listos.
 *
 * `__VERSION__` y `__HASH__` los inyecta Vite al compilar (ver `vite.config.mjs`),
 * de modo que la aplicación empaquetada no depende de tener git al lado.
 */
export default function BarraEstado() {
  const { estadoBackend, version, sesion, autenticado, componentes } = useApp()

  return (
    <footer className="flex h-telemetria shrink-0 items-center justify-between gap-4 border-t border-borde bg-superficie px-4 font-mono text-telemetria text-tenue">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex shrink-0 items-center gap-1.5">
          <Icono nombre="base-datos" tamano={12} />
          <Indicador estado={estadoBackend} />
          {DESCRIPCION[estadoBackend] ?? 'Verificando servicio local…'}
        </span>

        <Filete />

        <ChipEstado
          etiqueta="BD"
          estado={componentes.baseDatos}
          detalle="Base de datos cifrada: se marca en verde cuando una lectura real responde"
        />

        <ChipEstado
          etiqueta="APIs"
          estado={componentes.apis}
          detalle="Conexión de modelos por API: se configura en la Fase 4"
        />

        <ChipEstado
          etiqueta="Chatbot"
          estado={componentes.chatbot}
          detalle="El asistente funciona por API: se configura en la Fase 4"
        />

        <Filete />

        <span className="hidden shrink-0 items-center gap-1.5 sm:flex">
          <Icono nombre="escudo" tamano={12} />
          AES-256-GCM
        </span>

        <Filete />

        <span className="truncate">
          {autenticado ? `sesión: ${sesion?.usuario_nombre ?? 'activa'}` : 'sin sesión'}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden truncate lg:inline">{urlBase()}</span>
        {version && <span className="hidden sm:inline">servicio v{version}</span>}
        <span className="text-primario">
          v{__VERSION__} ({__HASH__})
        </span>
      </div>
    </footer>
  )
}

const DESCRIPCION = {
  conectado: 'Servicio local conectado',
  sin_conexion: 'Servicio local no disponible',
  verificando: 'Verificando servicio local…',
}

/** Punto de color por estado de una pieza del sistema (SCRUM-68). */
const PUNTO = {
  ok: 'bg-exito',
  error: 'bg-peligro',
  verificando: 'bg-alerta',
  sin_verificar: 'bg-borde-fuerte',
  sin_configurar: 'bg-borde-fuerte',
}

function Filete() {
  return <span aria-hidden="true" className="h-3 w-px shrink-0 bg-borde" />
}

function Indicador({ estado }) {
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full ${PUNTO[estado] ?? 'bg-alerta'}`}
      aria-hidden="true"
    />
  )
}

/**
 * Pieza del sistema con su punto de color. El estado se anuncia en texto para
 * lectores de pantalla y el detalle viaja en el `title`.
 */
function ChipEstado({ etiqueta, estado, detalle }) {
  const leyenda = LEYENDA[estado] ?? estado

  return (
    <span className="hidden shrink-0 items-center gap-1.5 md:flex" title={`${etiqueta}: ${detalle}`}>
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${PUNTO[estado] ?? 'bg-borde-fuerte'}`} />
      <span className="text-texto-2">{etiqueta}</span>
      <span className="sr-only">{leyenda}</span>
    </span>
  )
}

const LEYENDA = {
  ok: 'disponible',
  error: 'no disponible',
  verificando: 'verificando',
  sin_verificar: 'sin verificar',
  sin_configurar: 'sin configurar',
}