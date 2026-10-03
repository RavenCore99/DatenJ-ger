// Copyright (c) 2024 DatenJäger. All rights reserved.
// electron/backend.js - ciclo de vida del servicio Python local
// Trazabilidad Jira: SCRUM-60 (DatenJäger — Electron).

/**
 * Arranca y detiene `backend/server.py` (SCRUM-21).
 *
 * El servidor se anuncia en su primera línea de salida estándar:
 *
 *     DATENJAGER_LISTO puerto=8756 token=<secreto>
 *
 * De ahí salen el puerto real (por si se pidió 0 y lo eligió el sistema) y el
 * token que el renderer reenvía en `X-DatenJager-Token`. Si el servicio no
 * arranca, la aplicación sigue funcionando y la interfaz muestra el estado
 * «sin conexión» en lugar de fallar en silencio.
 */

const fs = require('node:fs')
const path = require('node:path')
const { spawn } = require('node:child_process')

// Servicios en marcha en este proceso. Si el proceso principal muere de golpe
// (cierre forzado o fallo), el hijo de Python no debe quedarse vivo ocupando
// el puerto: 'before-quit' no llega a ejecutarse en esos casos.
const VIVOS = new Set()

const limpiarAlSalir = () => {
  for (const proceso of VIVOS) {
    try {
      proceso.kill('SIGKILL')
    } catch {
      /* el proceso ya no existe */
    }
  }
}

process.on('exit', limpiarAlSalir)
process.on('SIGTERM', limpiarAlSalir)
process.on('SIGINT', limpiarAlSalir)
const { randomBytes } = require('node:crypto')

/** Tiempo máximo de espera del anuncio de arranque. */
const ESPERA_ARRANQUE_MS = 25000

/**
 * Puertos que se prueban, en orden, hasta que uno quede libre.
 *
 * Si el puerto preferido está ocupado (una instancia anterior que no se cerró
 * bien, o el `main.py` antiguo), antes la aplicación se quedaba **sin servicio**
 * y la interfaz decía «sin conexión» sin más. Probando el siguiente puerto, y
 * dejando el último en manos del sistema (`0`), arrancar deja de depender de que
 * nadie tenga ocupado el 8756.
 */
function puertosCandidatos(preferido) {
  return [preferido, preferido + 1, preferido + 2, preferido + 3, 0]
}

const RAIZ = path.join(__dirname, '..')

/**
 * Binario del servicio cuando la aplicación está empaquetada.
 *
 * El paquete de Electron lleva el backend congelado en `extraResources`
 * (`electron-builder.yml`), que en tiempo de ejecución vive bajo
 * `process.resourcesPath`. Si ese binario está, se usa **en lugar** del
 * intérprete de Python: es toda la diferencia entre una instalación que
 * funciona sola y una que exige tener Python con dependencias.
 *
 * @returns la ruta del binario, o `null` si no hay paquete (desarrollo).
 */
function binarioEmpaquetado() {
  const recursos = process.resourcesPath
  if (!recursos) return null

  const nombre = process.platform === 'win32' ? 'datenjager-servidor.exe' : 'datenjager-servidor'
  const ruta = path.join(recursos, 'servidor', nombre)
  return fs.existsSync(ruta) ? ruta : null
}

/**
 * Directorio de datos de la aplicación (base, `.env`, almacenes cifrados).
 *
 * La aplicación instalada escribe su estado aquí, nunca junto al programa:
 * el directorio de instalación puede ser de solo lectura y, sobre todo, el
 * instalador lleva **programa, no estado**. `interprete()` de abajo no lo
 * decide; lo decide este directorio, que `electron/main.js` fija con
 * `app.getPath('userData')`.
 */
function directorioDeDatos(raiz = RAIZ) {
  return process.env.DATENJAGER_DATOS || raiz
}

/**
 * Intérprete de Python a usar.
 *
 * Prioridad: variable de entorno, entorno virtual del proyecto, `python3`.
 * Solo aplica cuando **no** hay binario empaquetado.
 */
function interprete(raiz = RAIZ) {
  if (process.env.DATENJAGER_PYTHON) return process.env.DATENJAGER_PYTHON

  const candidatos =
    process.platform === 'win32'
      ? [path.join(raiz, 'venv', 'Scripts', 'python.exe')]
      : [path.join(raiz, 'venv', 'bin', 'python'), '/usr/bin/python3']

  return candidatos.find((ruta) => fs.existsSync(ruta)) ?? 'python3'
}

function generarToken() {
  return randomBytes(32).toString('base64url')
}

/**
 * Servicio Python local: encapsula el proceso hijo y su configuración.
 */
class ServicioPython {
  constructor({
    raiz = RAIZ,
    puerto = 8756,
    dbPath = process.env.DATENJAGER_DB ?? null,
    datos = directorioDeDatos(raiz),
    binario = binarioEmpaquetado(),
  } = {}) {
    this.raiz = raiz
    this.puerto = puerto
    // Base alternativa: pruebas y desarrollo no deben escribir sobre la base
    // de trabajo del usuario.
    this.dbPath = dbPath
    // Dónde vive el estado de la aplicación. En desarrollo es el proyecto; en
    // la aplicación instalada, el directorio de datos del usuario.
    this.datos = datos
    // Binario congelado del backend, si la aplicación viene empaquetada.
    this.binario = binario
    this.token = generarToken()
    this.proceso = null
    this.puertoReal = null
    this.error = null
    this.bitacora = []
  }

  /** Programa y argumentos del servicio, según esté congelado o no. */
  ordenDeArranque(puerto) {
    // Congelado, el binario **es** `backend.server`: no admite `-m`.
    const comunes = ['--host', '127.0.0.1', '--puerto', String(puerto), '--token', this.token]
    const orden = this.binario
      ? [this.binario, ...comunes]
      : [interprete(this.raiz), '-m', 'backend.server', ...comunes]

    if (this.dbPath) orden.push('--db', this.dbPath)
    return orden
  }

  /** Entorno del servicio: dónde quedan la base, los tokens y el `.env`. */
  entornoDeArranque() {
    return {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      // El directorio de datos manda sobre la base y el almacén de tokens
      // cifrado. El guion de entrada (`scripts/servidor_entry.py`) lee esta
      // misma variable, así que el binario y el guion coinciden. Un
      // `DATENJAGER_TOKENS` puesto a mano se respeta: es el que usan las
      // pruebas y las sondas para no tocar los datos reales.
      DATENJAGER_DATOS: this.datos,
      DATENJAGER_TOKENS: process.env.DATENJAGER_TOKENS || this.datos,
    }
  }

  /** Configuración que consume el renderer. */
  get configuracion() {
    return {
      puertoBackend: this.puertoReal ?? this.puerto,
      urlBackend: `http://127.0.0.1:${this.puertoReal ?? this.puerto}`,
      token: this.token,
      disponible: Boolean(this.puertoReal),
      error: this.error,
    }
  }

  /** Arranca el servicio y espera su anuncio. Nunca lanza: registra el fallo. */
  async arrancar() {
    if (this.proceso) return this.configuracion

    // `spawn` falla con ENOENT si el directorio de trabajo no existe, y el
    // error no diría por qué. En la aplicación instalada lo crea Electron, pero
    // aquí no cuesta nada asegurarlo.
    try {
      fs.mkdirSync(this.datos, { recursive: true })
    } catch (error) {
      this.error = `No se pudo preparar el directorio de datos (${this.datos}): ${error.message}`
      return this.configuracion
    }

    for (const puerto of puertosCandidatos(this.puerto)) {
      this.puertoIntento = puerto
      const listo = await this.intentarEn(puerto)
      if (listo) return this.configuracion

      // Un fallo que no sea el puerto ocupado no se arregla probando otro.
      if (!/puerto .* ya está ocupado/i.test(this.error ?? '')) return this.configuracion
    }

    return this.configuracion
  }

  /**
   * Un intento de arranque en un puerto concreto.
   *
   * @returns `true` si el servicio llegó a anunciarse; `false` si hay que probar
   *   otro puerto (el proceso fallido se descarta antes de devolver).
   */
  async intentarEn(puerto) {
    const orden = this.ordenDeArranque(puerto)

    try {
      this.proceso = spawn(orden[0], orden.slice(1), {
        // La aplicación instalada trabaja desde su directorio de datos: es
        // donde el backend crea la base, el `.env` y `config.json`.
        cwd: this.datos,
        env: this.entornoDeArranque(),
        stdio: ['ignore', 'pipe', 'pipe'],
      })
    } catch (error) {
      this.error = `No se pudo lanzar el servicio local: ${error.message}`
      return false
    }

    VIVOS.add(this.proceso)

    this.proceso.on('error', (error) => {
      this.error = `No se pudo lanzar el servicio local: ${error.message}`
    })

    this.proceso.on('exit', (codigo, senal) => {
      if (this.puertoReal && codigo !== 0) {
        this.error = `El servicio local terminó (código ${codigo}, señal ${senal})`
      }
      VIVOS.delete(this.proceso)
      this.proceso = null
      this.puertoReal = null
    })

    this.proceso.stderr.on('data', (datos) => {
      this.registrar(datos)

      // Un puerto ocupado o un fallo de arranque no deben consumir la espera
      // completa: se informa de inmediato y, si hay otro servicio escuchando,
      // no se le entrega el token a nadie.
      const texto = datos.toString()
      if (/address already in use|error while attempting to bind/i.test(texto)) {
        this.error =
          `El puerto ${puerto} ya está ocupado por otro proceso. ` +
          'Cierra la instancia anterior o define otro puerto (DATENJAGER_PUERTO).'
        this.abortarEspera()
      } else if (/DATENJAGER_ERROR/i.test(texto)) {
        // Fallo anunciado por el propio servicio (p. ej. la base de datos no se
        // pudo abrir). Se muestra su mensaje en vez de un genérico, porque es
        // el único que explica por qué no se puede entrar.
        const anuncio = texto.split('\n').find((linea) => linea.startsWith('DATENJAGER_ERROR'))
        this.error = anuncio ?? 'El servicio local no pudo iniciarse'
        this.abortarEspera()
      } else if (/Traceback|ModuleNotFoundError|ImportError/i.test(texto)) {
        this.error = 'El servicio local no pudo iniciarse (revisa la salida de Python)'
        this.abortarEspera()
      }
    })

    await this.esperarAnuncio()

    if (this.puertoReal) return true

    // El intento falló: se descarta el proceso antes de probar otro puerto.
    const fallido = this.proceso
    this.proceso = null
    this.puertoReal = null
    if (fallido) {
      VIVOS.delete(fallido)
      try {
        fallido.kill('SIGKILL')
      } catch {
        /* el proceso ya no existe */
      }
    }
    return false
  }

  /** Corta la espera del anuncio cuando ya se sabe que el servicio no arranca. */
  abortarEspera() {
    this.puertoReal = null
    this._abortar?.()
  }

  /** Lee la salida estándar hasta el anuncio de arranque o el tiempo límite. */
  esperarAnuncio() {
    return new Promise((resolver) => {
      let terminado = false
      const terminar = () => {
        if (terminado) return
        terminado = true
        clearTimeout(espera)
        resolver()
      }

      this._abortar = terminar

      const espera = setTimeout(() => {
        this.error = this.error ?? `El servicio local no respondió en ${ESPERA_ARRANQUE_MS / 1000} s`
        terminar()
      }, ESPERA_ARRANQUE_MS)

      let pendiente = ''

      const revisar = (datos) => {
        pendiente += datos.toString()
        const lineas = pendiente.split('\n')
        pendiente = lineas.pop() ?? ''

        for (const linea of lineas) {
          if (!linea.startsWith('DATENJAGER_LISTO')) {
            this.registrar(linea)
            continue
          }
          this.puertoReal = Number(linea.match(/puerto=(\d+)/)?.[1] ?? this.puerto)
          this.error = null
          terminar()
        }
      }

      this.proceso.stdout.on('data', revisar)
      this.proceso.stdout.on('close', () => terminar())
    })
  }

  /** Detiene el servicio. Se llama al cerrar la aplicación. */
  detener() {
    if (!this.proceso) return

    const proceso = this.proceso
    this.proceso = null
    this.puertoReal = null

    try {
      VIVOS.delete(proceso)
      proceso.kill('SIGTERM')
      setTimeout(() => {
        if (!proceso.killed) proceso.kill('SIGKILL')
      }, 3000).unref()
    } catch (error) {
      console.error(`[datenjager] no se pudo detener el servicio local: ${error.message}`)
    }
  }

  registrar(datos) {
    const texto = datos.toString().trim()
    if (!texto) return
    this.bitacora.push(texto)
    if (this.bitacora.length > 50) this.bitacora.shift()
    console.log(`[servicio] ${texto}`)
  }
}

module.exports = { ServicioPython, interprete, generarToken, binarioEmpaquetado, directorioDeDatos }