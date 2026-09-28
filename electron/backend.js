// Copyright (c) 2024 DatenJäger. All rights reserved.
// electron/backend.js - ciclo de vida del servicio Python local

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
const { randomBytes } = require('node:crypto')

/** Tiempo máximo de espera del anuncio de arranque. */
const ESPERA_ARRANQUE_MS = 25000

const RAIZ = path.join(__dirname, '..')

/**
 * Intérprete de Python a usar.
 *
 * Prioridad: variable de entorno, entorno virtual del proyecto, `python3`.
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
  constructor({ raiz = RAIZ, puerto = 8756 } = {}) {
    this.raiz = raiz
    this.puerto = puerto
    this.token = generarToken()
    this.proceso = null
    this.puertoReal = null
    this.error = null
    this.bitacora = []
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

    const orden = [
      '-m', 'backend.server',
      '--host', '127.0.0.1',
      '--puerto', String(this.puerto),
      '--token', this.token,
    ]

    try {
      this.proceso = spawn(interprete(this.raiz), orden, {
        cwd: this.raiz,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        stdio: ['ignore', 'pipe', 'pipe'],
      })
    } catch (error) {
      this.error = `No se pudo lanzar Python: ${error.message}`
      return this.configuracion
    }

    this.proceso.on('error', (error) => {
      this.error = `No se pudo lanzar Python: ${error.message}`
    })

    this.proceso.on('exit', (codigo, senal) => {
      if (this.puertoReal && codigo !== 0) {
        this.error = `El servicio local terminó (código ${codigo}, señal ${senal})`
      }
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
          `El puerto ${this.puerto} ya está ocupado por otro proceso. ` +
          'Cierra la instancia anterior o define otro puerto (DATENJAGER_PUERTO).'
        this.abortarEspera()
      } else if (/Traceback|ModuleNotFoundError|ImportError/i.test(texto)) {
        this.error = 'El servicio local no pudo iniciarse (revisa la salida de Python)'
        this.abortarEspera()
      }
    })

    await this.esperarAnuncio()
    return this.configuracion
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

module.exports = { ServicioPython, interprete, generarToken }