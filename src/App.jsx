import { useEffect, useState } from 'react'

import { ProveedorApp, useApp } from './estado/ProveedorApp.jsx'
import BarraLateral from './components/BarraLateral.jsx'
import BarraEstado from './components/BarraEstado.jsx'
import Entrada from './components/Entrada.jsx'
import Icono from './components/Icono.jsx'
import Inicio from './pages/Inicio.jsx'
import Documentos from './pages/Documentos.jsx'
import Personas from './pages/Personas.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Cuenta from './pages/Cuenta.jsx'
import Acceso from './pages/Acceso.jsx'
import Bienvenida from './pages/Bienvenida.jsx'
import Registro from './pages/Registro.jsx'
import Chatbot from './pages/Chatbot.jsx'
import Reportes from './pages/Reportes.jsx'
import Estadisticas from './pages/Estadisticas.jsx'
import Modelos from './pages/Modelos.jsx'

/**
 * Secciones del sistema. Cada una corresponde a un panel del CustomTkinter
 * actual (ver CLAUDE.md sección 3) y se reconstruye en la Fase 3.
 *
 * Las cinco primeras son los paneles migrados en el Sprint 2; de «Asistente» en
 * adelante son las pantallas que faltaban (Sprint 5, `SCRUM-57` a `SCRUM-64`).
 */
export const SECCIONES = [
  { clave: 'inicio', titulo: 'Inicio', descripcion: 'Resumen documental', icono: 'inicio', Componente: Inicio },
  { clave: 'documentos', titulo: 'Documentos', descripcion: 'PDFs cifrados', icono: 'documentos', Componente: Documentos },
  { clave: 'personas', titulo: 'Personas', descripcion: 'Titulares y empresas', icono: 'personas', Componente: Personas },
  { clave: 'auditoria', titulo: 'Auditoría', descripcion: 'Historial de acciones', icono: 'auditoria', Componente: Auditoria },
  { clave: 'chatbot', titulo: 'Asistente', descripcion: 'Chat por API', icono: 'chatbot', Componente: Chatbot },
  { clave: 'reportes', titulo: 'Reportes', descripcion: 'Inventario exportable', icono: 'lista', Componente: Reportes },
  { clave: 'estadisticas', titulo: 'Estadísticas', descripcion: 'Datos y gráficos', icono: 'grafico', Componente: Estadisticas },
  { clave: 'modelos', titulo: 'Modelos', descripcion: 'Conexión de APIs', icono: 'globo', Componente: Modelos },
  { clave: 'cuenta', titulo: 'Ajustes', descripcion: 'Cuenta y seguridad', icono: 'cuenta', Componente: Cuenta },
]

export function App() {
  return (
    <ProveedorApp>
      <Entrada />
      <Marco />
    </ProveedorApp>
  )
}

/**
 * Marco de la aplicación (SCRUM-28), con las densidades del sistema de diseño:
 * barra lateral de `240px` que se recoge a `64px`, sub-cabecera de `48px` con
 * migas de pan, área de contenido desplazable y franja de telemetría de `32px`
 * pegada al borde inferior.
 */
function Marco() {
  const { tema, autenticado, recargarSalud } = useApp()
  const [seccion, setSeccion] = useSeccionInicial()
  const [plegada, setPlegada] = useBarraLateral()
  // Portal de entrada: bienvenida → acceso, o bienvenida → registro. No se
  // recuerda entre arranques, porque la bienvenida es la presentación de la
  // aplicación.
  const [portal, setPortal] = useState('bienvenida')

  useEffect(() => {
    try {
      localStorage.setItem('datenjager.tema', tema)
    } catch {
      /* almacenamiento no disponible */
    }
  }, [tema])

  // Atajo para plegar y desplegar la barra lateral (SCRUM-70): Ctrl/⌘ + B,
  // el mismo gesto que usan los editores para el panel lateral.
  useEffect(() => {
    const alPulsar = (evento) => {
      if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'b') {
        evento.preventDefault()
        setPlegada((valor) => !valor)
      }
    }

    globalThis.addEventListener('keydown', alPulsar)
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [setPlegada])

  // El portal manda mientras el alta no haya terminado: crear la cuenta abre
  // sesión en el backend de inmediato, así que hay que seguir mostrando el paso
  // del segundo factor aunque `autenticado` ya sea cierto (SCRUM-57/58).
  if (portal === 'bienvenida') {
    return (
      <Bienvenida
        onEntrar={() => setPortal('acceso')}
        onRegistrar={() => setPortal('registro')}
      />
    )
  }

  if (portal === 'registro') {
    return (
      <Registro
        onVolver={() => setPortal('bienvenida')}
        onTerminar={async () => {
          await recargarSalud()
          setPortal('sistema')
        }}
      />
    )
  }

  // Sin sesión verificada por el backend no se muestra el sistema (SCRUM-22).
  if (!autenticado) {
    return <Acceso onVolver={() => setPortal('bienvenida')} />
  }

  const activa = SECCIONES.find(({ clave }) => clave === seccion) ?? SECCIONES[0]
  const { Componente } = activa

  return (
    <div className="flex h-full w-full bg-fondo text-texto">
      <BarraLateral
        seccion={seccion}
        onSeleccionar={setSeccion}
        plegada={plegada}
        onPlegar={() => setPlegada((valor) => !valor)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <SubCabecera seccion={activa} plegada={plegada} onPlegar={() => setPlegada((v) => !v)} />

        <main className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          {/* Transición de pantalla (SCRUM-32): al cambiar de sección, el
              contenido entra con un fundido breve. La clave fuerza el remonte
              para que la animación vuelva a dispararse. */}
          <div key={seccion} className="aparecer">
            <Componente onNavegar={setSeccion} />
          </div>
        </main>

        <BarraEstado />
      </div>
    </div>
  )
}

/** Sub-cabecera fija: control de la barra lateral, migas de pan e insignia de cifrado. */
function SubCabecera({ seccion, plegada, onPlegar }) {
  return (
    <header className="flex h-cabecera shrink-0 items-center justify-between gap-4 border-b border-borde bg-superficie px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onPlegar}
          aria-expanded={!plegada}
          aria-keyshortcuts="Control+B"
          aria-label={plegada ? 'Desplegar la barra lateral' : 'Recoger la barra lateral'}
          title={`${plegada ? 'Desplegar' : 'Recoger'} la barra lateral (Ctrl+B)`}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-borde text-tenue transition-colors hover:border-primario hover:text-primario"
        >
          <Icono nombre={plegada ? 'chevron-derecha' : 'chevron-izquierda'} tamano={15} />
        </button>

        <nav aria-label="Ubicación" className="flex min-w-0 items-center gap-2 text-etiqueta-md">
          <span className="font-marca text-tenue">DatenJäger</span>
          <span aria-hidden="true" className="text-borde-fuerte">
            /
          </span>
          <span className="truncate font-medium">{seccion.titulo}</span>
          <span className="hidden truncate text-tenue sm:inline">· {seccion.descripcion}</span>
        </nav>
      </div>

      <span
        className="flex shrink-0 items-center gap-1.5 rounded border border-borde bg-fondo px-2 py-1 font-mono text-telemetria text-tenue"
        title="Los documentos se guardan cifrados con AES-256-GCM"
      >
        <span aria-hidden="true" className="inline-block h-1.5 w-1.5 rounded-full bg-exito" />
        AES-256-GCM
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

/** El ancho de la barra lateral también sobrevive al recargado. */
function useBarraLateral() {
  const [plegada, setPlegada] = useState(() => {
    try {
      return localStorage.getItem('datenjager.lateral') === 'plegada'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem('datenjager.lateral', plegada ? 'plegada' : 'abierta')
    } catch {
      /* almacenamiento no disponible */
    }
  }, [plegada])

  return [plegada, setPlegada]
}

export default App