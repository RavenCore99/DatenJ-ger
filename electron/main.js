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
const { elegirDocumento, guardarDocumento, elegirDestino } = require('./archivos')

// Identidad de la aplicación (SCRUM-65): el nombre que muestran el sistema y la
// barra de tareas, y el identificador que Windows usa para agrupar las ventanas
// (sin él, la barra de tareas ignora el icono del logo).
app.setName('DatenJäger')
if (process.platform === 'win32') app.setAppUserModelId('com.datenjager.desktop')

/**
 * Icono de la ventana y de la barra de tareas (SCRUM-65). Windows prefiere el
 * `.ico` multi-resolución —el `.png` suelto se ve borroso al escalar—; Linux y
 * macOS usan el PNG del logo.
 */
function iconoDeAplicacion() {
  const archivo = process.platform === 'win32' ? 'logo.ico' : 'logo.png'
  return path.join(__dirname, '..', 'assets', 'logo', archivo)
}

/** Puerto por defecto del backend local (FastAPI + uvicorn, SCRUM-21). */
const PUERTO_BACKEND = Number(process.env.DATENJAGER_PUERTO ?? 8756)

/** Puerto del servidor de desarrollo de Vite (vite.config.mjs). */
const PUERTO_VITE = 5273

const enDesarrollo = process.argv.includes('--dev') && !app.isPackaged

// En desarrollo el renderer se sirve desde el servidor de Vite, así que su
// origen deja de ser `file://` y las peticiones al servicio pasan a ser de otro
// origen: hay que habilitar CORS para ese origen concreto, o el navegador las
// bloquea y la interfaz se queda en «sin conexión» con el servicio levantado.
// Solo se define en desarrollo; en producción el servicio no habilita CORS.
if (enDesarrollo) {
  process.env.DATENJAGER_CORS_ORIGENES =
    `http://127.0.0.1:${PUERTO_VITE},http://localhost:${PUERTO_VITE}`
}

/** Servicio Python local. Se arranca al estar lista la aplicación. */
const servicio = new ServicioPython({
  puerto: PUERTO_BACKEND,
  // Instalada, la aplicación escribe su estado —base de datos, `.env`,
  // almacenes cifrados— en el directorio de datos del usuario. Junto al
  // programa no puede: en Linux suele ser de solo lectura, y el instalador
  // lleva programa, no estado.
  datos: app.isPackaged ? app.getPath('userData') : undefined,
})

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
    // El puerto se lee en cada respuesta; si cambia tras cargar index.html,
    // se recarga la página para que la política inicial use el puerto real.
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
    frame: false,
    // Fondo del tema claro del sistema de diseño: evita el destello oscuro
    // antes de que el renderer pinte (el tema por defecto es el claro).
    backgroundColor: '#f8f9ff',
    title: 'DatenJäger',
    icon: iconoDeAplicacion(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  ventana.once('ready-to-show', () => ventana.show())

  const informarEstado = () => {
    if (!ventana?.isDestroyed()) {
      ventana.webContents.send('ventana:estado', {
        maximizada: ventana.isMaximized(),
        pantallaCompleta: ventana.isFullScreen(),
      })
    }
  }
  ventana.on('maximize', informarEstado)
  ventana.on('unmaximize', informarEstado)
  ventana.on('enter-full-screen', informarEstado)
  ventana.on('leave-full-screen', informarEstado)

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
// Solo devuelve la ruta elegida: el reporte lo escribe el servicio de Python.
ipcMain.handle('archivo:destino', (_evento, datos) => elegirDestino(ventana, datos))

// Cada petición se limita a la ventana que originó el IPC. El renderer no
// recibe acceso a BrowserWindow ni a acciones arbitrarias del proceso principal.
function ventanaDe(evento) {
  const origen = BrowserWindow.fromWebContents(evento.sender)
  return origen && !origen.isDestroyed() ? origen : null
}

ipcMain.handle('ventana:estado', (evento) => {
  const origen = ventanaDe(evento)
  return {
    maximizada: Boolean(origen?.isMaximized()),
    pantallaCompleta: Boolean(origen?.isFullScreen()),
  }
})
ipcMain.handle('ventana:minimizar', (evento) => ventanaDe(evento)?.minimize())
ipcMain.handle('ventana:maximizar', (evento) => {
  const origen = ventanaDe(evento)
  if (!origen) return false
  if (origen.isMaximized()) origen.unmaximize()
  else origen.maximize()
  return origen.isMaximized()
})
ipcMain.handle('ventana:cerrar', (evento) => ventanaDe(evento)?.close())

/**
 * Alterna la pantalla completa de la ventana (SCRUM-85, atajo `F11`).
 *
 * Se resuelve aquí y no en el renderer porque el estado de la ventana es del
 * proceso principal: el renderer solo pide el cambio y recibe el estado nuevo,
 * que es lo que permite mostrar en Ajustes si está activo o no.
 */
ipcMain.handle('ventana:pantalla-completa', () => {
  if (!ventana) return false
  const completa = !ventana.isFullScreen()
  ventana.setFullScreen(completa)
  return completa
})

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
  // La CSP del documento ya se fijó cuando empezó a cargar. Si el puerto
  // preferido estaba ocupado, una sola recarga instala la política correcta;
  // sin ella la UI queda «sin conexión» aunque el servicio esté sano.
  if (configuracionServicio.disponible &&
      configuracionServicio.puertoBackend !== PUERTO_BACKEND &&
      ventana && !ventana.isDestroyed()) {
    ventana.webContents.reload()
  }
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