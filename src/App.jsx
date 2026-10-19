import { useCallback, useEffect, useRef, useState } from 'react'

import { ProveedorApp, useApp } from './estado/ProveedorApp.jsx'
import BarraLateral from './components/BarraLateral.jsx'
import BarraVentana from './components/BarraVentana.jsx'
import ConfirmarCierreSesion from './components/ConfirmarCierreSesion.jsx'
import BarraEstado from './components/BarraEstado.jsx'
import BusquedaGlobal from './components/BusquedaGlobal.jsx'
import Entrada from './components/Entrada.jsx'
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

/** Secciones de navegación; auditoría y modelos se abren desde Ajustes. */
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
      {/* Avisos visibles también durante el acceso y el registro. */}
      <Notificaciones />
    </ProveedorApp>
  )
}

/** Marco de navegación con barra lateral, contenido y telemetría. */
function Marco() {
  const { tema, autenticado, recargarSalud, pedir } = useApp()
  const [seccion, setSeccion] = useSeccionInicial()
  const [plegada, setPlegada] = useBarraLateral()
  // Búsqueda global con Ctrl/⌘+F.
  const [buscando, setBuscando] = useState(false)
  // La bienvenida precede al acceso o al registro en cada arranque.
  const [portal, setPortal] = useState('bienvenida')
  const [confirmandoSalida, setConfirmandoSalida] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem('datenjager.tema', tema)
    } catch {
      /* almacenamiento no disponible */
    }
  }, [tema])

  /** La barra y Ctrl+Q abren la misma confirmación temática. */
  const cerrarSesion = useCallback(() => {
    if (autenticado) setConfirmandoSalida(true)
  }, [autenticado])

  const confirmarCierreSesion = async () => {
    try {
      await backend.sesion.salir()
    } finally {
      await recargarSalud()
    }
    setConfirmandoSalida(false)
  }

  const abrirAsistente = () => {
    if (seccion === 'chatbot') document.querySelector('main textarea')?.focus()
    else setSeccion('chatbot')
  }

  // Los accesos se montan únicamente junto al contenido autenticado.
  const conBarra = (contenido, mostrarAccesos = false) => (
    <div className="relative flex h-full min-h-0 flex-col">
      <BarraVentana
        portal={!mostrarAccesos}
        onAbrirAjustes={mostrarAccesos ? () => setSeccion('cuenta') : undefined}
        onAbrirAsistente={mostrarAccesos ? abrirAsistente : undefined}
        onCerrarSesion={mostrarAccesos ? cerrarSesion : undefined}
      />
      <div className="min-h-0 flex-1">{contenido}</div>
      {mostrarAccesos && confirmandoSalida && (
        <ConfirmarCierreSesion
          onCancelar={() => setConfirmandoSalida(false)}
          onConfirmar={confirmarCierreSesion}
        />
      )}
    </div>
  )

  // Maneja los atajos globales anunciados en Ajustes.
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
        if (!capaAbierta()) cerrarSesion()
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

  // El registro mantiene el paso de 2FA aunque ya exista una sesión.
  if (portal === 'bienvenida') {
    return conBarra(
      <Bienvenida
        onEntrar={() => setPortal('acceso')}
        onRegistrar={() => setPortal('registro')}
      />,
    )
  }

  if (portal === 'registro') {
    return conBarra(
      <Registro
        onVolver={() => setPortal('bienvenida')}
        onTerminar={async () => {
          await recargarSalud()
          setPortal('sistema')
        }}
      />,
    )
  }

  // La aplicación requiere una sesión verificada.
  if (!autenticado) {
    return conBarra(<Acceso onVolver={() => setPortal('bienvenida')} />)
  }

  const activa = SECCIONES.find(({ clave }) => clave === seccion) ?? SECCIONES[0]
  const { Componente } = activa

  return conBarra(
    <div className="flex h-full w-full bg-fondo text-texto">
      <BarraLateral
        seccion={seccion}
        onSeleccionar={setSeccion}
        plegada={plegada}
        onPlegar={() => setPlegada((valor) => !valor)}
      />

      <div className="relative flex min-w-0 flex-1 flex-col">
        <SubCabecera seccion={activa} />

        <main className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          {/* Remonta el contenido para animar cada cambio de sección. */}
          <div key={seccion} className="aparecer">
            <Componente onNavegar={setSeccion} />
          </div>
        </main>

        {/* Asistente flotante: se oculta en Ajustes, donde estorbaría sobre los
            formularios de seguridad. */}
        {seccion !== 'cuenta' && (
          <BotonAsistente enElAsistente={seccion === 'chatbot'} onAbrir={abrirAsistente} />
        )}

        <BarraEstado />
      </div>

      {/* Búsqueda global superpuesta a la navegación. */}
      {buscando && (
        <BusquedaGlobal onNavegar={setSeccion} onCerrar={() => setBuscando(false)} />
      )}
    </div>,
    true,
  )
}

/** Indica la sección activa en la cabecera. */
function SubCabecera({ seccion }) {
  return (
    <header className="flex h-cabecera shrink-0 items-center gap-4 border-b border-borde bg-superficie px-6">
      <nav aria-label="Ubicación" className="flex min-w-0 items-center gap-2 text-etiqueta-md">
        <span className="font-marca text-tenue">DatenJäger</span>
        <span aria-hidden="true" className="text-borde-fuerte">
          /
        </span>
        <span className="truncate font-medium">{seccion.titulo}</span>
        <span className="hidden truncate text-tenue sm:inline">· {seccion.descripcion}</span>
      </nav>
    </header>
  )
}

/** Abre el asistente o enfoca su campo de escritura. */
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