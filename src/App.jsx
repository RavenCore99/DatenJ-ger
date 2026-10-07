import { useCallback, useEffect, useRef, useState } from 'react'

import { ProveedorApp, useApp } from './estado/ProveedorApp.jsx'
import BarraLateral from './components/BarraLateral.jsx'
import BarraEstado from './components/BarraEstado.jsx'
import BusquedaGlobal from './components/BusquedaGlobal.jsx'
import Entrada from './components/Entrada.jsx'
import Icono from './components/Icono.jsx'
import Notificaciones from './components/Notificaciones.jsx'
import { capaAbierta, escribiendoEn } from './lib/atajos.js'
import { alternarPantallaCompleta } from './lib/escritorio.js'
import { backend } from './lib/api.js'
import { pulso } from './lib/movimiento.js'
import Inicio from './pages/Inicio.jsx'
import Documentos from './pages/Documentos.jsx'
import Personas from './pages/Personas.jsx'
import Cuenta from './pages/Cuenta.jsx'
import Acceso from './pages/Acceso.jsx'
import Bienvenida from './pages/Bienvenida.jsx'
import Registro from './pages/Registro.jsx'
import Chatbot from './pages/Chatbot.jsx'
import Reportes from './pages/Reportes.jsx'
import Estadisticas from './pages/Estadisticas.jsx'
import siluetaAsistente from '../assets/chatbot/nousresearch_backcontrast.png'

/**
 * Secciones del sistema. Cada una corresponde a un panel del CustomTkinter
 * actual (ver CLAUDE.md sección 3) y se reconstruye en la Fase 3.
 *
 * Las cinco primeras son los paneles migrados en el Sprint 2; de «Asistente» en
 * adelante son las pantallas que faltaban (Sprint 5, `SCRUM-57` a `SCRUM-64`).
 *
 * **Auditoría y Modelos no están aquí.** Son ajustes del sistema —historial de
 * acciones y conexión de las APIs— y viven **solo** dentro de «Ajustes»
 * (`src/pages/Cuenta.jsx`), que es donde Raven los pidió. Tenerlos además en la
 * barra de secciones los duplicaba: la misma pantalla en dos sitios, con el
 * usuario sin saber cuál es «el bueno».
 */
export const SECCIONES = [
  { clave: 'inicio', titulo: 'Inicio', descripcion: 'Resumen documental', icono: 'inicio', Componente: Inicio },
  { clave: 'documentos', titulo: 'Documentos', descripcion: 'PDFs cifrados', icono: 'documentos', Componente: Documentos },
  { clave: 'personas', titulo: 'Personas', descripcion: 'Titulares y empresas', icono: 'personas', Componente: Personas },
  { clave: 'chatbot', titulo: 'Asistente', descripcion: 'Chat por API', icono: 'chatbot', Componente: Chatbot },
  { clave: 'reportes', titulo: 'Reportes', descripcion: 'Inventario exportable', icono: 'lista', Componente: Reportes },
  { clave: 'estadisticas', titulo: 'Estadísticas', descripcion: 'Datos y gráficos', icono: 'grafico', Componente: Estadisticas },
  { clave: 'cuenta', titulo: 'Ajustes', descripcion: 'Cuenta y seguridad', icono: 'cuenta', Componente: Cuenta },
]

export function App() {
  return (
    <ProveedorApp>
      <Entrada />
      <Marco />
      {/* Notificaciones del sistema (SCRUM-87): viven fuera del marco para que
          también se vean en el portal de acceso y en el registro. */}
      <Notificaciones />
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
  const { tema, autenticado, recargarSalud, pedir } = useApp()
  const [seccion, setSeccion] = useSeccionInicial()
  const [plegada, setPlegada] = useBarraLateral()
  // Búsqueda global (SCRUM-85), en `Ctrl / ⌘ + F`.
  const [buscando, setBuscando] = useState(false)
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

  /** Cierra la sesión abierta (`Ctrl / ⌘ + Q`), con confirmación. */
  const cerrarSesion = useCallback(async () => {
    if (!autenticado) return
    if (!globalThis.confirm('¿Cerrar la sesión abierta?')) return

    try {
      await backend.sesion.salir()
    } finally {
      await recargarSalud()
    }
  }, [autenticado, recargarSalud])

  // Atajos globales (SCRUM-85). La tabla que se anuncia en Ajustes vive en
  // `src/lib/atajos.js`; aquí está el manejador que los hace funcionar.
  useEffect(() => {
    const alPulsar = (evento) => {
      const conModificador = evento.ctrlKey || evento.metaKey
      const tecla = evento.key.toLowerCase()

      if (conModificador && tecla === 'b') {
        evento.preventDefault()
        setPlegada((valor) => !valor)
        return
      }

      // Los atajos que abren una capa o cierran la sesión solo tienen sentido
      // con sesión: en el portal de acceso se ignoran en vez de no hacer nada.
      if (!autenticado) return

      if (conModificador && tecla === 'f') {
        evento.preventDefault()
        setBuscando(true)
        return
      }

      if (conModificador && tecla === 'n') {
        evento.preventDefault()
        setSeccion('documentos')
        pedir('nuevo-documento')
        return
      }

      if (conModificador && tecla === 'q') {
        evento.preventDefault()
        cerrarSesion()
        return
      }

      if (evento.key === 'F11') {
        evento.preventDefault()
        alternarPantallaCompleta()
        return
      }

      // `Supr` solo borra en Documentos, con una fila elegida y sin nada abierto
      // encima; si el foco está en un campo, borrar es borrar texto.
      if (
        evento.key === 'Delete' &&
        seccion === 'documentos' &&
        !escribiendoEn(evento) &&
        !capaAbierta()
      ) {
        evento.preventDefault()
        pedir('eliminar-seleccionado')
      }
    }

    globalThis.addEventListener('keydown', alPulsar)
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [setPlegada, pedir, setSeccion, seccion, autenticado, cerrarSesion])

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

      <div className="relative flex min-w-0 flex-1 flex-col">
        <SubCabecera seccion={activa} onAbrirAjustes={() => setSeccion('cuenta')} />

        <main className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          {/* Transición de pantalla (SCRUM-32): al cambiar de sección, el
              contenido entra con un fundido breve. La clave fuerza el remonte
              para que la animación vuelva a dispararse. */}
          <div key={seccion} className="aparecer">
            <Componente onNavegar={setSeccion} />
          </div>
        </main>

        {/* Asistente flotante: se oculta en Ajustes, donde estorbaría sobre los
            formularios de seguridad. */}
        {seccion !== 'cuenta' && (
          <BotonAsistente
            enElAsistente={seccion === 'chatbot'}
            onAbrir={() => {
              if (seccion === 'chatbot') {
                // Ya estamos aquí: el botón lleva el foco al compositor en vez
                // de navegar a donde ya se está.
                document.querySelector('main textarea')?.focus()
                return
              }
              setSeccion('chatbot')
            }}
          />
        )}

        <BarraEstado />
      </div>

      {/* Búsqueda global (SCRUM-85): capa sobre el shell, no una pantalla más. */}
      {buscando && (
        <BusquedaGlobal onNavegar={setSeccion} onCerrar={() => setBuscando(false)} />
      )}
    </div>
  )
}

/**
 * Sub-cabecera fija: migas de pan y accesos rápidos.
 *
 * El control de la barra lateral vive en el propio logo (ver `BarraLateral`),
 * así que aquí no se repite. La insignia de cifrado se retiró de este extremo
 * porque competía con el contenido de cada panel: el cifrado en uso ya se
 * informa donde importa —la franja de telemetría, el detalle de cada
 * expediente y la sección «Acerca de»— y aquí ocupaba el sitio de los accesos.
 */
function SubCabecera({ seccion, onAbrirAjustes }) {
  return (
    <header className="flex h-cabecera shrink-0 items-center justify-between gap-4 border-b border-borde bg-superficie px-6">
      <nav aria-label="Ubicación" className="flex min-w-0 items-center gap-2 text-etiqueta-md">
        <span className="font-marca text-tenue">DatenJäger</span>
        <span aria-hidden="true" className="text-borde-fuerte">
          /
        </span>
        <span className="truncate font-medium">{seccion.titulo}</span>
        <span className="hidden truncate text-tenue sm:inline">· {seccion.descripcion}</span>
      </nav>

      <div className="flex shrink-0 items-center gap-1">
        <AccesoRapido icono="tuerca" titulo="Ajustes" onPulsar={onAbrirAjustes} />
      </div>
    </header>
  )
}

/** Acceso rápido de la sub-cabecera: mismo aspecto en todas las secciones. */
function AccesoRapido({ icono, titulo, onPulsar }) {
  return (
    <button
      type="button"
      onClick={onPulsar}
      title={titulo}
      aria-label={titulo}
      className="flex h-8 w-8 items-center justify-center rounded-md border border-borde text-tenue transition-colors hover:border-primario hover:text-primario"
    >
      <Icono nombre={icono} tamano={16} />
    </button>
  )
}

/**
 * Asistente flotante (calidad de vida): el chat queda a un clic desde cualquier
 * sección, sin depender de la barra lateral ni de tenerla desplegada.
 *
 * Se oculta en Ajustes, donde el botón flotaría sobre formularios de seguridad
 * y estorbaría. Dentro del propio asistente no navega —ya se está ahí—, sino
 * que lleva el foco al compositor, para que el botón nunca sea un no-op.
 *
 * **Lleva la imagen del asistente** (petición de Raven): el mismo archivo de
 * `assets/chatbot/` que el avatar del panel. Se usa la versión de trazo blanco
 * porque el fondo del botón es el azul primario, oscuro en los dos temas.
 */
function BotonAsistente({ onAbrir, enElAsistente }) {
  const boton = useRef(null)

  return (
    <button
      ref={boton}
      type="button"
      onClick={() => {
        pulso(boton.current)
        onAbrir()
      }}
      title={enElAsistente ? 'Escribir en el asistente' : 'Abrir el asistente'}
      aria-label={enElAsistente ? 'Escribir en el asistente' : 'Abrir el asistente'}
      className="absolute bottom-12 right-6 z-20 flex h-11 w-11 items-center justify-center overflow-hidden rounded-full bg-primario shadow-flotante transition-colors hover:bg-primario-enfasis"
    >
      <img src={siluetaAsistente} alt="" aria-hidden="true" className="h-full w-full object-cover" />
    </button>
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