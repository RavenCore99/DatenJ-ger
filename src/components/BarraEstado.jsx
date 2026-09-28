import { useApp } from '../estado/ProveedorApp.jsx'
import { urlBase } from '../lib/api.js'

/** Pie de la ventana: estado del servicio local y datos de la sesión. */
export default function BarraEstado() {
  const { estadoBackend, version, sesion, autenticado } = useApp()

  return (
    <footer className="flex items-center justify-between gap-4 border-t border-borde px-8 py-2 text-[11px] text-tenue">
      <div className="flex items-center gap-2">
        <Indicador estado={estadoBackend} />
        <span>{DESCRIPCION[estadoBackend] ?? 'Verificando servicio local…'}</span>
        <span className="font-mono">{urlBase()}</span>
      </div>

      <div className="flex items-center gap-4 font-mono">
        {version && <span>backend v{version}</span>}
        <span>
          {autenticado ? `sesión: ${sesion?.usuario_nombre ?? 'activa'}` : 'sin sesión'}
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

function Indicador({ estado }) {
  const color = {
    conectado: 'bg-exito',
    sin_conexion: 'bg-peligro',
    verificando: 'bg-alerta',
  }[estado]

  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} aria-hidden="true" />
}