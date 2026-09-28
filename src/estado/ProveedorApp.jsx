import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import { backend, ErrorBackend, fijarConfiguracion } from '../lib/api.js'

/**
 * Estado de aplicación del renderer: sesión, tema y disponibilidad del
 * backend local. Es el equivalente React de `backend/state.py` — la sesión
 * real vive en Python; aquí solo se refleja lo que el backend informa.
 */

const INTERVALO_SALUD_MS = 5000

const ContextoApp = createContext(null)

export function ProveedorApp({ children }) {
  const [estadoBackend, setEstadoBackend] = useState('verificando')
  const [version, setVersion] = useState(null)
  const [sesion, setSesion] = useState(null)
  const [tema, setTema] = useState(() => temaInicial())
  const [aviso, setAviso] = useState(null)

  const montado = useRef(true)

  useEffect(() => {
    montado.current = true
    return () => {
      montado.current = false
    }
  }, [])

  const consultarSalud = useCallback(async (senal) => {
    try {
      const info = await backend.salud(senal)
      if (!montado.current) return
      setEstadoBackend('conectado')
      setVersion(info?.version ?? null)
    } catch (error) {
      if (error?.name === 'AbortError') return
      if (!montado.current) return
      setEstadoBackend('sin_conexion')
      if (!(error instanceof ErrorBackend)) setAviso(String(error))
    }
  }, [])

  // El proceso principal avisa cuando el servicio Python terminó de arrancar
  // (o cuando no pudo): la configuración se refresca y el sondeo se repite.
  useEffect(() => {
    if (!globalThis.datenjager?.alCambiarServicio) return undefined

    return globalThis.datenjager.alCambiarServicio((configuracion) => {
      fijarConfiguracion(configuracion)
      setAviso(configuracion?.error ?? null)
      consultarSalud()
    })
  }, [consultarSalud])

  // Sondeo del servicio local: el backend puede arrancar después que la
  // ventana (Electron lanza el proceso Python en paralelo).
  useEffect(() => {
    const control = new AbortController()
    consultarSalud(control.signal)

    const temporizador = setInterval(() => consultarSalud(control.signal), INTERVALO_SALUD_MS)
    return () => {
      control.abort()
      clearInterval(temporizador)
    }
  }, [consultarSalud])

  // El tema se resuelve como clase en <html>, igual que hoy en CustomTkinter.
  useEffect(() => {
    const raiz = document.documentElement
    raiz.classList.toggle('tema-oscuro', tema === 'oscuro')
    raiz.dataset.tema = tema
  }, [tema])

  const alternarTema = useCallback(() => {
    setTema((actual) => (actual === 'oscuro' ? 'claro' : 'oscuro'))
  }, [])

  const valor = useMemo(
    () => ({
      estadoBackend,
      conectado: estadoBackend === 'conectado',
      version,
      sesion,
      autenticado: Boolean(sesion?.autenticado),
      setSesion,
      tema,
      alternarTema,
      aviso,
      limpiarAviso: () => setAviso(null),
      recargarSalud: () => consultarSalud(),
    }),
    [estadoBackend, version, sesion, tema, aviso, alternarTema, consultarSalud],
  )

  return <ContextoApp.Provider value={valor}>{children}</ContextoApp.Provider>
}

/** Acceso al estado de aplicación. Falla ruidosamente si falta el proveedor. */
export function useApp() {
  const contexto = useContext(ContextoApp)
  if (!contexto) {
    throw new Error('useApp() debe usarse dentro de <ProveedorApp>')
  }
  return contexto
}

function temaInicial() {
  try {
    const guardado = localStorage.getItem('datenjager.tema')
    if (guardado === 'claro' || guardado === 'oscuro') return guardado
  } catch {
    /* almacenamiento no disponible: se usa el tema claro */
  }
  return 'claro'
}