import { useEffect, useState } from 'react'

import { alCambiarVentana, cerrarVentana, enEscritorio, estadoVentana, maximizarVentana, minimizarVentana } from '../lib/escritorio.js'
import Icono from './Icono.jsx'

/** Barra propia para la ventana Electron; la vista web conserva el marco del navegador. */
export default function BarraVentana({ onAbrirAjustes, onAbrirAsistente, onCerrarSesion }) {
  const [maximizada, setMaximizada] = useState(false)

  useEffect(() => {
    if (!enEscritorio()) return undefined
    let vigente = true
    estadoVentana().then((estado) => {
      if (vigente) setMaximizada(estado.maximizada)
    })
    const quitarEscucha = alCambiarVentana((estado) => setMaximizada(estado.maximizada))
    return () => {
      vigente = false
      quitarEscucha()
    }
  }, [])

  if (!enEscritorio()) return null

  return (
    <header className="region-arrastrable relative z-50 flex h-11 shrink-0 select-none items-center justify-between border-b border-borde bg-superficie px-3 text-texto" aria-label="Barra de ventana">
      <div className="min-w-0 flex-1 self-stretch" aria-hidden="true" />
      <div className="region-no-arrastrable flex shrink-0 items-center gap-2">
        {onAbrirAjustes && (
          <nav className="flex items-center gap-1" aria-label="Accesos rápidos">
            <button type="button" aria-label="Abrir ajustes" title="Ajustes" onClick={onAbrirAjustes} className="flex h-8 w-8 items-center justify-center rounded-md text-tenue transition-colors hover:bg-fondo-2 hover:text-primario focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
              <Icono nombre="tuerca" tamano={16} />
            </button>
            <button type="button" aria-label="Abrir asistente" title="Asistente" onClick={onAbrirAsistente} className="flex h-8 w-8 items-center justify-center rounded-md text-tenue transition-colors hover:bg-fondo-2 hover:text-primario focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
              <Icono nombre="chatbot" tamano={16} />
            </button>
            <button type="button" aria-label="Cerrar sesión" title="Cerrar sesión" onClick={onCerrarSesion} className="flex h-8 w-8 items-center justify-center rounded-md text-tenue transition-colors hover:bg-peligro-suave hover:text-peligro focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
              <Icono nombre="cerrar-sesion" tamano={16} />
            </button>
          </nav>
        )}
        {onAbrirAjustes && <span className="h-5 border-l border-borde" aria-hidden="true" />}
        <div className="flex items-center gap-1" role="group" aria-label="Controles de ventana">
          <button type="button" aria-label="Minimizar ventana" title="Minimizar" onClick={minimizarVentana} className="control-ventana group flex h-8 w-8 items-center justify-center rounded-md hover:bg-fondo-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
            <span className="h-3 w-3 rounded-full bg-[rgb(var(--dj-trafico-minimizar))] shadow-sm ring-1 ring-black/10 group-hover:ring-black/20" />
          </button>
          <button type="button" aria-label={maximizada ? 'Restaurar ventana' : 'Maximizar ventana'} title={maximizada ? 'Restaurar' : 'Maximizar'} onClick={maximizarVentana} className="control-ventana group flex h-8 w-8 items-center justify-center rounded-md hover:bg-fondo-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
            <span className="h-3 w-3 rounded-full bg-[rgb(var(--dj-trafico-expandir))] shadow-sm ring-1 ring-black/10 group-hover:ring-black/20" />
          </button>
          <button type="button" aria-label="Cerrar ventana" title="Cerrar" onClick={cerrarVentana} className="control-ventana group flex h-8 w-8 items-center justify-center rounded-md hover:bg-peligro-suave focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario">
            <span className="h-3 w-3 rounded-full bg-[rgb(var(--dj-trafico-cerrar))] shadow-sm ring-1 ring-black/10 group-hover:ring-black/20" />
          </button>
        </div>
      </div>
    </header>
  )
}
