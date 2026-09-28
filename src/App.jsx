import { useEffect, useState } from 'react'

import { ProveedorApp, useApp } from './estado/ProveedorApp.jsx'
import BarraLateral from './components/BarraLateral.jsx'
import BarraEstado from './components/BarraEstado.jsx'
import Inicio from './pages/Inicio.jsx'
import Documentos from './pages/Documentos.jsx'
import Personas from './pages/Personas.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Cuenta from './pages/Cuenta.jsx'

/**
 * Secciones del sistema. Cada una corresponde a un panel del CustomTkinter
 * actual (ver CLAUDE.md sección 3) y se reconstruye en SCRUM-22 a SCRUM-25.
 */
export const SECCIONES = [
  { clave: 'inicio', titulo: 'Inicio', descripcion: 'Resumen documental', Componente: Inicio },
  { clave: 'documentos', titulo: 'Documentos', descripcion: 'PDFs cifrados', Componente: Documentos },
  { clave: 'personas', titulo: 'Personas', descripcion: 'Titulares y empresas', Componente: Personas },
  { clave: 'auditoria', titulo: 'Auditoría', descripcion: 'Historial de acciones', Componente: Auditoria },
  { clave: 'cuenta', titulo: 'Cuenta', descripcion: 'Seguridad y apariencia', Componente: Cuenta },
]

export function App() {
  return (
    <ProveedorApp>
      <Marco />
    </ProveedorApp>
  )
}

/** Marco visual: barra lateral fija, área de contenido desplazable, pie de estado. */
function Marco() {
  const { tema } = useApp()
  const [seccion, setSeccion] = useSeccionInicial()

  useEffect(() => {
    try {
      localStorage.setItem('datenjager.tema', tema)
    } catch {
      /* almacenamiento no disponible */
    }
  }, [tema])

  const activa = SECCIONES.find(({ clave }) => clave === seccion) ?? SECCIONES[0]
  const { Componente } = activa

  return (
    <div className="flex h-full w-full bg-fondo text-texto">
      <BarraLateral seccion={seccion} onSeleccionar={setSeccion} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Cabecera titulo={activa.titulo} descripcion={activa.descripcion} />

        <main className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
          <Componente onNavegar={setSeccion} />
        </main>

        <BarraEstado />
      </div>
    </div>
  )
}

function Cabecera({ titulo, descripcion }) {
  return (
    <header className="flex items-baseline justify-between border-b border-borde px-8 py-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{titulo}</h1>
        <p className="text-xs text-tenue">{descripcion}</p>
      </div>
      <span className="font-mono text-[11px] uppercase tracking-widest text-tenue">
        DatenJäger
      </span>
    </header>
  )
}

/** La sección activa sobrevive al recargado de la ventana. */
function useSeccionInicial() {
  const [seccion, setSeccion] = useState(() => {
    try {
      const guardada = localStorage.getItem('datenjager.seccion')
      if (SECCIONES.some(({ clave }) => clave === guardada)) return guardada
    } catch {
      /* almacenamiento no disponible */
    }
    return SECCIONES[0].clave
  })

  useEffect(() => {
    try {
      localStorage.setItem('datenjager.seccion', seccion)
    } catch {
      /* almacenamiento no disponible */
    }
  }, [seccion])

  return [seccion, setSeccion]
}

export default App