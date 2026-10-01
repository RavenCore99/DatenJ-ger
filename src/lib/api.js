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

/** Caché de la configuración que publica el proceso principal de Electron. */
let configuracionCache = null
let promesaConfiguracion = null

/**
 * Configuración del servicio local: puerto y token.
 *
 * En Electron la entrega el proceso principal por IPC (el token se genera en
 * cada arranque); en el navegador de desarrollo se cae a las variables de Vite
 * y no hay token.
 */
export function configuracion() {
  if (configuracionCache) return Promise.resolve(configuracionCache)

  if (!promesaConfiguracion) {
    promesaConfiguracion = (async () => {
      let resuelta = null

      try {
        if (globalThis.datenjager?.configuracion) {
          resuelta = await globalThis.datenjager.configuracion()
        }
      } catch (error) {
        console.warn(`No se pudo leer la configuración de Electron: ${error.message}`)
      }

      configuracionCache = {
        puerto: resuelta?.puertoBackend ?? Number(import.meta.env?.VITE_DATENJAGER_PUERTO ?? PUERTO_BACKEND_POR_DEFECTO),
        token: resuelta?.token ?? null,
      }
      return configuracionCache
    })()
  }

  return promesaConfiguracion
}

/** Actualiza la configuración en caliente cuando el servicio arranca. */
export function fijarConfiguracion({ puertoBackend, token } = {}) {
  if (!puertoBackend && !token) return
  configuracionCache = {
    puerto: puertoBackend ?? configuracionCache?.puerto ?? PUERTO_BACKEND_POR_DEFECTO,
    token: token ?? configuracionCache?.token ?? null,
  }
  promesaConfiguracion = Promise.resolve(configuracionCache)
}

/**
 * URL base del servicio local.
 *
 * Síncrona a propósito: se usa para mostrarla en la barra de estado. Antes de
 * la primera petición devuelve el valor por defecto.
 */
export function urlBase() {
  const puerto = configuracionCache?.puerto ?? PUERTO_BACKEND_POR_DEFECTO
  return `http://127.0.0.1:${puerto}`
}

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
  const { puerto, token } = await configuracion()

  const cabeceras = {}
  if (cuerpo) cabeceras['Content-Type'] = 'application/json'
  if (token) cabeceras['X-DatenJager-Token'] = token

  let respuesta

  try {
    respuesta = await fetch(`http://127.0.0.1:${puerto}${ruta}`, {
      method: metodo,
      headers: cabeceras,
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

/**
 * Ejecuta una petición que responde **en flujo** (SSE) y entrega cada marco ya
 * parseado. `solicitar` espera un JSON completo, así que no sirve para esto:
 * aquí se lee el cuerpo a medida que llega y se avisa marco a marco.
 */
export async function transmitir(ruta, cuerpo, onMarco, senal) {
  const { puerto, token } = await configuracion()

  const cabeceras = { 'Content-Type': 'application/json' }
  if (token) cabeceras['X-DatenJager-Token'] = token

  let respuesta
  try {
    respuesta = await fetch(`http://127.0.0.1:${puerto}${ruta}`, {
      method: 'POST',
      headers: cabeceras,
      body: JSON.stringify(cuerpo),
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
  if (!respuesta.body) {
    throw new ErrorBackend('El servicio no entregó un flujo de respuesta.', 'SinFlujo', 0)
  }

  const lector = respuesta.body.getReader()
  const decodificador = new TextDecoder()
  let pendiente = ''

  while (true) {
    const { value, done } = await lector.read()
    if (done) break

    pendiente += decodificador.decode(value, { stream: true })
    const marcos = pendiente.split('\n\n')
    // El último trozo puede estar a medias: se guarda para el ciclo siguiente.
    pendiente = marcos.pop() ?? ''

    for (const marco of marcos) {
      const linea = marco.split('\n').find((candidata) => candidata.startsWith('data:'))
      if (!linea) continue
      try {
        onMarco?.(JSON.parse(linea.slice(5).trim()))
      } catch {
        /* marco ilegible: se ignora en vez de cortar el flujo */
      }
    }
  }
}

/** Accesos concretos al backend, por área del sistema. */
export const backend = {
  salud: (senal) => solicitar('/api/salud', { senal }),

  sesion: {
    actual: (senal) => solicitar('/api/sesion', { senal }),
    // `tokenConfianza` es el token del dispositivo: si el servicio lo acepta,
    // el segundo factor se omite en este acceso.
    entrar: (nombre, contrasena, tokenConfianza = null) =>
      solicitar('/api/sesion', {
        metodo: 'POST',
        cuerpo: { nombre, contrasena, token_confianza: tokenConfianza },
      }),
    // Alta de una cuenta nueva (SCRUM-57). El servicio abre la sesión del
    // usuario recién creado, que es desde la que se configura el 2FA.
    registrar: (nombre, contrasena) =>
      solicitar('/api/registro', { metodo: 'POST', cuerpo: { nombre, contrasena } }),
    verificarCodigo: (codigo) =>
      solicitar('/api/sesion/2fa', { metodo: 'POST', cuerpo: { codigo } }),
    // Restablecimiento de contraseña (SCRUM-84): primero se verifica un código
    // de respaldo, después se fija la contraseña nueva. Ningún paso exige sesión.
    solicitarRestablecimiento: (nombre, codigo) =>
      solicitar('/api/sesion/restablecer', { metodo: 'POST', cuerpo: { nombre, codigo } }),
    fijarContrasenaRestablecida: (contrasenaNueva) =>
      solicitar('/api/sesion/restablecer/contrasena', {
        metodo: 'POST',
        cuerpo: { contrasena_nueva: contrasenaNueva },
      }),
    usarCodigoDeRespaldo: (codigo) =>
      solicitar('/api/sesion/respaldo', { metodo: 'POST', cuerpo: { codigo } }),
    salir: () => solicitar('/api/sesion', { metodo: 'DELETE' }),
  },

  cuenta: {
    estado: () => solicitar('/api/cuenta'),
    // El secreto del 2FA no se activa hasta que el usuario confirma un código.
    prepararSegundoFactor: () => solicitar('/api/cuenta/2fa/preparar', { metodo: 'POST' }),
    activarSegundoFactor: (secreto, codigo) =>
      solicitar('/api/cuenta/2fa/activar', { metodo: 'POST', cuerpo: { secreto, codigo } }),
    desactivarSegundoFactor: (codigo) =>
      solicitar('/api/cuenta/2fa/desactivar', { metodo: 'POST', cuerpo: { codigo } }),
    regenerarCodigos: (codigo) =>
      solicitar('/api/cuenta/2fa/codigos', { metodo: 'POST', cuerpo: { codigo } }),
    cambiarContrasena: (contrasenaActual, contrasenaNueva, codigo) =>
      solicitar('/api/cuenta/contrasena', {
        metodo: 'POST',
        cuerpo: {
          contrasena_actual: contrasenaActual,
          contrasena_nueva: contrasenaNueva,
          codigo,
        },
      }),
    revocarConfianza: () => solicitar('/api/cuenta/confianza', { metodo: 'DELETE' }),
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

  empresas: {
    listar: (busqueda = '') =>
      solicitar(`/api/empresas${busqueda ? `?buscar=${encodeURIComponent(busqueda)}` : ''}`),
    contar: () => solicitar('/api/empresas/conteo'),
    obtener: (id) => solicitar(`/api/empresas/${id}`),
    crear: (nombre) => solicitar('/api/empresas', { metodo: 'POST', cuerpo: { nombre } }),
    renombrar: (id, nombre) =>
      solicitar(`/api/empresas/${id}`, { metodo: 'PATCH', cuerpo: { nombre } }),
    fusionar: (origenId, destinoId) =>
      solicitar(`/api/empresas/${origenId}/fusionar`, {
        metodo: 'POST',
        cuerpo: { destino_id: destinoId },
      }),
    eliminar: (id) => solicitar(`/api/empresas/${id}`, { metodo: 'DELETE' }),
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
    // Distribución y serie temporal para el panel de datos y estadísticas.
    porEmpresa: () => solicitar('/api/reportes/por-empresa'),
    porDia: () => solicitar('/api/reportes/por-dia'),
    // Serie con regresión, predicción, R² y la paleta de gráficos (SCRUM-81).
    tendencia: () => solicitar('/api/reportes/tendencia'),
    exportar: (destino, formato) =>
      solicitar('/api/reportes/exportar', { metodo: 'POST', cuerpo: { destino, formato } }),
  },

  // Conexión de modelos de IA (SCRUM-64). El servicio nunca devuelve la clave:
  // solo informa de si está configurada y de dónde sale.
  modelos: {
    estado: () => solicitar('/api/modelos'),
    guardar: (datos) => solicitar('/api/modelos', { metodo: 'POST', cuerpo: datos }),
    probar: () => solicitar('/api/modelos/probar', { metodo: 'POST' }),
  },

  chat: {
    iniciar: (contexto = '') =>
      solicitar('/api/chat', { metodo: 'POST', cuerpo: { contexto } }),
    enviar: (mensaje) => solicitar('/api/chat/mensajes', { metodo: 'POST', cuerpo: { mensaje } }),
    // Respuesta progresiva (RF-16): cada marco trae un `fragmento`, un `error`
    // o el `fin` del flujo.
    enviarStream: (mensaje, onMarco, senal) =>
      transmitir('/api/chat/mensajes/stream', { mensaje }, onMarco, senal),
    // Prueba real de generación, para el panel de conexión (SCRUM-62).
    probar: () => solicitar('/api/chat/probar', { metodo: 'POST' }),
    limpiar: () => solicitar('/api/chat', { metodo: 'DELETE' }),
  },
}

export default backend