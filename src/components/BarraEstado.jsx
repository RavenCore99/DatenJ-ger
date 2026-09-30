import { useApp } from '../estado/ProveedorApp.jsx'
import { urlBase } from '../lib/api.js'

/**
 * Franja de telemetría inferior (SCRUM-28): `32px` pegados al borde, en
 * monoespaciada de 11px, con el estado del servicio a la izquierda y la
 * versión con el hash del build a la derecha.
 *
 * `__VERSION__` y `__HASH__` los inyecta Vite al compilar (ver `vite.config.mjs`),
 * de modo que la aplicación empaquetada no depende de tener git al lado.
 */
export default function BarraEstado() {
  const { estadoBackend, version, sesion, autenticado } = useApp()

  return (
    <footer className="flex h-telemetria shrink-0 items-center justify-between gap-4 border-t border-borde bg-superficie px-4 font-mono text-telemetria text-tenue">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex shrink-0 items-center gap-1.5">
          <Indicador estado={estadoBackend} />
          {DESCRIPCION[estadoBackend] ?? 'Verificando servicio local…'}
        </span>

        <Filete />

        <span className="hidden shrink-0 sm:inline">AES-256-GCM</span>

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

function Filete() {
  return <span aria-hidden="true" className="h-3 w-px shrink-0 bg-borde" />
}

function Indicador({ estado }) {
  const color = {
    conectado: 'bg-exito',
    sin_conexion: 'bg-peligro',
    verificando: 'bg-alerta',
  }[estado]

  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full ${color ?? 'bg-alerta'}`}
      aria-hidden="true"
    />
  )
}