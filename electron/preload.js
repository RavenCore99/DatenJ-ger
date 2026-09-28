// Copyright (c) 2024 DatenJäger. All rights reserved.
// electron/preload.js - puente seguro entre el proceso principal y React

/**
 * Preload del renderer.
 *
 * `contextIsolation` está activo y `nodeIntegration` desactivado: React no ve
 * Node. Lo único que cruza el puente es la configuración que el proceso
 * principal conoce y el renderer necesita (puerto del backend local, versión,
 * modo de ejecución).
 */

const { contextBridge, ipcRenderer } = require('electron')

const CANAL_CONFIGURACION = 'app:configuracion'
const CANAL_SERVICIO = 'app:servicio'

contextBridge.exposeInMainWorld('datenjager', {
  /**
   * Configuración resuelta por el proceso principal: puerto y token del
   * servicio local. El token vive en el proceso principal; el renderer solo lo
   * reenvía en la cabecera `X-DatenJager-Token`.
   */
  configuracion: () => ipcRenderer.invoke(CANAL_CONFIGURACION),

  /** Aviso del proceso principal cuando el servicio local terminó de arrancar. */
  alCambiarServicio: (escucha) => {
    const manejador = (_evento, configuracion) => escucha(configuracion)
    ipcRenderer.on(CANAL_SERVICIO, manejador)
    return () => ipcRenderer.removeListener(CANAL_SERVICIO, manejador)
  },

  /** Elige un PDF del disco con el diálogo nativo (contenido en base64). */
  elegirArchivo: () => ipcRenderer.invoke('archivo:elegir'),

  /** Guarda en disco, con diálogo nativo, un archivo recibido en base64. */
  guardarArchivo: (datos) => ipcRenderer.invoke('archivo:guardar', datos),

  /** Solo lectura, sin IPC: datos del entorno de Electron. */
  versionElectron: process.versions.electron,
  versionNode: process.versions.node,
  plataforma: process.platform,
})