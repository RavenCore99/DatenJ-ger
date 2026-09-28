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

contextBridge.exposeInMainWorld('datenjager', {
  /** Configuración resuelta por el proceso principal. */
  configuracion: () => ipcRenderer.invoke(CANAL_CONFIGURACION),

  /** Solo lectura, sin IPC: datos del entorno de Electron. */
  versionElectron: process.versions.electron,
  versionNode: process.versions.node,
  plataforma: process.platform,
})