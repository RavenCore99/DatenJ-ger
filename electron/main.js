// Copyright (c) 2024 DatenJäger. All rights reserved.
// electron/main.js - proceso principal de Electron

/**
 * Proceso principal.
 *
 * Responsabilidades:
 *   1. Crear la ventana del renderer (React).
 *   2. En modo desarrollo apuntar al servidor de Vite; en producción cargar
 *      `dist/index.html` desde el disco.
 *   3. Resolver y publicar la configuración que el renderer necesita
 *      (puerto del backend local, versión, modo).
 *   4. Aplicar una política de seguridad de contenido estricta en producción.
 *
 * El arranque del backend Python se conecta aquí en SCRUM-21.
 */

const path = require('node:path')
const { app, BrowserWindow, ipcMain, session, shell } = require('electron')

const { ServicioPython } = require('./backend')
const { elegirDocumento, guardarDocumento } = require('./archivos')

/** Puerto por defecto del backend local (FastAPI + uvicorn, SCRUM-21). */
const PUERTO_BACKEND = Number(process.env.DATENJAGER_PUERTO ?? 8756)

/** Puerto del servidor de desarrollo de Vite (vite.config.mjs). */
const PUERTO_VITE = 5273

const enDesarrollo = process.argv.includes('--dev') && !app.isPackaged

/** Servicio Python local. Se arranca al estar lista la aplicación. */
const servicio = new ServicioPython({ puerto: PUERTO_BACKEND })

let ventana = null

function configuracion() {
  return {
    modo: enDesarrollo ? 'desarrollo' : 'produccion',
    version: app.getVersion(),
    ...servicio.configuracion,
  }
}

function aplicarPoliticaDeSeguridad() {
  // En producción el renderer solo debe poder hablar con su propio origen y
  // con el servicio local. En desarrollo se omite: Vite necesita inyectar
  // scripts y abrir un websocket de recarga en caliente (solo en localhost).
  if (enDesarrollo) return

  session.defaultSession.webRequest.onHeadersReceived((detalles, responder) => {
    // El puerto se lee en cada respuesta, no al registrar: el servicio puede
    // haber resuelto un puerto distinto al configurado cuando llegue la carga.
    const puerto = servicio.configuracion.puertoBackend

    const politica = [
      "default-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      `connect-src 'self' http://127.0.0.1:${puerto}`,
      "object-src 'none'",
      "base-uri 'none'",
      "form-action 'none'",
    ].join('; ')

    responder({
      responseHeaders: {
        ...detalles.responseHeaders,
        'Content-Security-Policy': [politica],
      },
    })
  })
}

function crearVentana() {
  ventana = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    // Fondo del tema claro del sistema de diseño: evita el destello oscuro
    // antes de que el renderer pinte (el tema por defecto es el claro).
    backgroundColor: '#f8f9ff',
    title: 'DatenJäger',
    icon: path.join(__dirname, '..', 'assets', 'logo', 'logo.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  ventana.once('ready-to-show', () => ventana.show())

  // Los enlaces externos se abren en el navegador, nunca dentro de la app.
  ventana.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url)
    return { action: 'deny' }
  })

  if (enDesarrollo) {
    ventana.loadURL(`http://127.0.0.1:${PUERTO_VITE}`)
  } else {
    ventana.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  // Trazas de carga: sin ellas, un renderer que no monta se ve como una
  // ventana en blanco sin ninguna pista en la terminal.
  ventana.webContents.on('did-finish-load', () => {
    console.log('[datenjager] renderer listo')
  })

  ventana.webContents.on('did-fail-load', (_evento, codigo, descripcion, url) => {
    console.error(`[datenjager] no se pudo cargar el renderer (${codigo}): ${descripcion} — ${url}`)
  })

  ventana.on('closed', () => {
    ventana = null
  })
}

ipcMain.handle('app:configuracion', () => configuracion())

// Operaciones de disco: la ruta la elige siempre la persona por diálogo nativo.
ipcMain.handle('archivo:elegir', () => elegirDocumento(ventana))
ipcMain.handle('archivo:guardar', (_evento, datos) => guardarDocumento(ventana, datos))

app.whenReady().then(async () => {
  aplicarPoliticaDeSeguridad()
  crearVentana()

  // El servicio local se levanta después de la ventana: si tarda o falla, la
  // interfaz ya está visible y muestra el estado «sin conexión».
  const configuracionServicio = await servicio.arrancar()
  console.log(
    configuracionServicio.disponible
      ? `[datenjager] servicio local en ${configuracionServicio.urlBackend}`
      : `[datenjager] servicio local no disponible: ${configuracionServicio.error}`,
  )
  ventana?.webContents.send('app:servicio', configuracionServicio)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) crearVentana()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// El proceso de Python no debe sobrevivir a la aplicación.
app.on('before-quit', () => servicio.detener())