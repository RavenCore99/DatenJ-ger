import { useEffect, useState } from 'react'

import { alCambiarVentana, cerrarVentana, enEscritorio, estadoVentana, maximizarVentana, minimizarVentana } from '../lib/escritorio.js'
import logo from '../../assets/logo/logo.png'

/** Barra propia para la ventana Electron; la vista web conserva el marco del navegador. */
export default function BarraVentana() {
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
      <div className="flex min-w-0 items-center gap-2.5">
        <img src={logo} alt="" className="pointer-events-none h-5 w-5 rounded-full object-contain" />
        <span className="truncate font-marca text-etiqueta-md font-semibold tracking-tight">DatenJäger</span>
        <span className="hidden text-etiqueta-sm text-tenue sm:inline">/ Gestión documental</span>
      </div>
      <div className="region-no-arrastrable flex shrink-0 items-center gap-1" role="group" aria-label="Controles de ventana">
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
    </header>
  )
}
