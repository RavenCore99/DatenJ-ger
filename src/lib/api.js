/**
 * Cliente del backend local de DatenJäger.
 *
 * El backend Python expone `backend/commands.py` por HTTP (FastAPI + uvicorn,
 * SCRUM-21). Este módulo es el único punto del renderer que conoce la URL y el
 * formato de las respuestas: las pantallas nunca llaman a `fetch` directamente.
 *
 * Contrato de errores — el backend devuelve `{ "detail": { "tipo": "...",
 * "mensaje": "..." } }`. Aquí se traduce a `ErrorBackend` para que la UI
 * decida qué mostrar sin interpretar códigos HTTP.
 */

export const PUERTO_BACKEND_POR_DEFECTO = 8756

/** Error tipado que replica las excepciones de `backend/errors.py`. */
export class ErrorBackend extends Error {
  constructor(mensaje, tipo = 'BackendError', estado = 0) {
    super(mensaje)
    this.name = 'ErrorBackend'
    this.tipo = tipo
    this.estado = estado
  }

  get sinSesion() {
    return this.tipo === 'NoAutenticadoError' || this.estado === 401
  }

  get noEncontrado() {
    return this.tipo === 'NoEncontradoError' || this.estado === 404
  }
}

/**
 * URL base del backend.
 *
 * En Electron el proceso principal inyecta la configuración real (puerto
 * elegido en tiempo de arranque) mediante `window.datenjager`; en el navegador
 * de desarrollo se usa la variable de Vite o el puerto por defecto.
 */
export function urlBase() {
  const configurada =
    globalThis.datenjager?.puertoBackend ??
    import.meta.env?.VITE_DATENJAGER_PUERTO ??
    PUERTO_BACKEND_POR_DEFECTO

  return `http://127.0.0.1:${configurada}`
}

/** Normaliza la respuesta de error del backend a un `ErrorBackend`. */
async function aError(respuesta) {
  let tipo = 'BackendError'
  let mensaje = `Error ${respuesta.status} al comunicarse con el backend`

  try {
    const cuerpo = await respuesta.json()
    const detalle = cuerpo?.detail ?? cuerpo
    if (typeof detalle === 'string') {
      mensaje = detalle
    } else if (detalle && typeof detalle === 'object') {
      tipo = detalle.tipo ?? tipo
      mensaje = detalle.mensaje ?? mensaje
    }
  } catch {
    /* respuesta sin cuerpo JSON: se conserva el mensaje genérico */
  }

  return new ErrorBackend(mensaje, tipo, respuesta.status)
}

/**
 * Ejecuta una petición contra el backend.
 *
 * @param {string} ruta    ruta relativa, p. ej. `/api/documentos`
 * @param {object} [opciones] `metodo`, `cuerpo`, `señal` (AbortSignal)
 */
export async function solicitar(ruta, { metodo = 'GET', cuerpo, senal } = {}) {
  let respuesta

  try {
    respuesta = await fetch(`${urlBase()}${ruta}`, {
      method: metodo,
      headers: cuerpo ? { 'Content-Type': 'application/json' } : undefined,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      signal: senal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ErrorBackend(
      'No se pudo contactar el servicio local. Verifica que el backend esté en ejecución.',
      'ServicioNoDisponible',
      0,
    )
  }

  if (!respuesta.ok) throw await aError(respuesta)
  if (respuesta.status === 204) return null

  return respuesta.json()
}

/** Accesos concretos al backend, por área del sistema. */
export const backend = {
  salud: (senal) => solicitar('/api/salud', { senal }),

  sesion: {
    actual: (senal) => solicitar('/api/sesion', { senal }),
    entrar: (usuario, contrasena) =>
      solicitar('/api/sesion', { metodo: 'POST', cuerpo: { usuario, contrasena } }),
    salir: () => solicitar('/api/sesion', { metodo: 'DELETE' }),
  },

  documentos: {
    listar: (busqueda = '') =>
      solicitar(`/api/documentos${busqueda ? `?buscar=${encodeURIComponent(busqueda)}` : ''}`),
    contar: () => solicitar('/api/documentos/conteo'),
    obtener: (id) => solicitar(`/api/documentos/${id}`),
    crear: (datos) => solicitar('/api/documentos', { metodo: 'POST', cuerpo: datos }),
    actualizar: (id, datos) =>
      solicitar(`/api/documentos/${id}`, { metodo: 'PATCH', cuerpo: datos }),
    eliminar: (id) => solicitar(`/api/documentos/${id}`, { metodo: 'DELETE' }),
    descargar: (id) => solicitar(`/api/documentos/${id}/descarga`),
    exportar: (id, destino) =>
      solicitar(`/api/documentos/${id}/exportar`, { metodo: 'POST', cuerpo: { destino } }),
  },

  personas: {
    listar: (busqueda = '') =>
      solicitar(`/api/personas${busqueda ? `?buscar=${encodeURIComponent(busqueda)}` : ''}`),
    obtener: (id) => solicitar(`/api/personas/${id}`),
    crear: (datos) => solicitar('/api/personas', { metodo: 'POST', cuerpo: datos }),
    actualizar: (id, datos) =>
      solicitar(`/api/personas/${id}`, { metodo: 'PATCH', cuerpo: datos }),
    eliminar: (id) => solicitar(`/api/personas/${id}`, { metodo: 'DELETE' }),
  },

  auditoria: {
    listar: (filtros = {}) => {
      const parametros = new URLSearchParams(
        Object.entries(filtros).filter(([, valor]) => valor),
      ).toString()
      return solicitar(`/api/auditoria${parametros ? `?${parametros}` : ''}`)
    },
    contar: () => solicitar('/api/auditoria/conteo'),
    limpiar: () => solicitar('/api/auditoria', { metodo: 'DELETE' }),
    log: () => solicitar('/api/auditoria/log'),
  },

  reportes: {
    estadisticas: () => solicitar('/api/reportes/estadisticas'),
    inventario: () => solicitar('/api/reportes/inventario'),
    exportar: (destino, formato) =>
      solicitar('/api/reportes/exportar', { metodo: 'POST', cuerpo: { destino, formato } }),
  },

  chat: {
    iniciar: (contexto = '') =>
      solicitar('/api/chat', { metodo: 'POST', cuerpo: { contexto } }),
    enviar: (mensaje) => solicitar('/api/chat/mensajes', { metodo: 'POST', cuerpo: { mensaje } }),
  },
}

export default backend