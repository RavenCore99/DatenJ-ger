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

/** Puerto por defecto del backend local (FastAPI + uvicorn, SCRUM-21). */
const PUERTO_BACKEND = Number(process.env.DATENJAGER_PUERTO ?? 8756)

/** Puerto del servidor de desarrollo de Vite (vite.config.js). */
const PUERTO_VITE = 5273

const enDesarrollo = process.argv.includes('--dev') && !app.isPackaged

let ventana = null

function configuracion() {
  return {
    modo: enDesarrollo ? 'desarrollo' : 'produccion',
    puertoBackend: PUERTO_BACKEND,
    urlBackend: `http://127.0.0.1:${PUERTO_BACKEND}`,
    version: app.getVersion(),
  }
}

function aplicarPoliticaDeSeguridad() {
  // En producción el renderer solo debe poder hablar con su propio origen y
  // con el servicio local. En desarrollo se omite: Vite necesita inyectar
  // scripts y abrir un websocket de recarga en caliente (solo en localhost).
  if (enDesarrollo) return

  const politica = [
    "default-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' http://127.0.0.1:${PUERTO_BACKEND}`,
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ].join('; ')

  session.defaultSession.webRequest.onHeadersReceived((detalles, responder) => {
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
    backgroundColor: '#0D0F1A',
    title: 'DatenJäger',
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

app.whenReady().then(() => {
  aplicarPoliticaDeSeguridad()
  crearVentana()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) crearVentana()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})