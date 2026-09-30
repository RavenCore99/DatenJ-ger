// Copyright (c) 2024 DatenJäger. All rights reserved.
// electron/archivos.js - lectura y escritura de archivos desde el renderer

/**
 * El renderer no ve el sistema de archivos (`contextIsolation` activo y
 * `nodeIntegration` desactivado). Estas dos operaciones son las únicas que
 * necesitan tocar disco, y pasan por el diálogo nativo del sistema para que la
 * ruta la elija siempre la persona que usa la aplicación.
 */

const fs = require('node:fs/promises')
const path = require('node:path')

const { dialog } = require('electron')

const TAMANO_MAXIMO = 50 * 1024 * 1024

const FILTROS_PDF = [
  { name: 'Documentos PDF', extensions: ['pdf'] },
  { name: 'Todos los archivos', extensions: ['*'] },
]

/** Abre un PDF del disco y devuelve su contenido en base64. */
async function elegirDocumento(ventana) {
  const { canceled, filePaths } = await dialog.showOpenDialog(ventana, {
    title: 'Seleccionar documento PDF',
    properties: ['openFile'],
    filters: FILTROS_PDF,
  })

  if (canceled || filePaths.length === 0) return { cancelado: true }

  const ruta = filePaths[0]
  const informacion = await fs.stat(ruta)

  if (informacion.size > TAMANO_MAXIMO) {
    return { error: `El archivo supera el límite de ${TAMANO_MAXIMO / (1024 * 1024)} MB` }
  }

  const contenido = await fs.readFile(ruta)
  return {
    cancelado: false,
    nombre: path.basename(ruta),
    ruta,
    tamano: informacion.size,
    contenido_b64: contenido.toString('base64'),
  }
}

/** Guarda en disco un archivo que llega en base64 desde el servicio. */
async function guardarDocumento(ventana, { nombre, contenido_b64: contenidoB64 } = {}) {
  const { canceled, filePath } = await dialog.showSaveDialog(ventana, {
    title: 'Guardar documento',
    defaultPath: nombre || 'documento.pdf',
    filters: FILTROS_PDF,
  })

  if (canceled || !filePath) return { cancelado: true }

  await fs.writeFile(filePath, Buffer.from(contenidoB64, 'base64'))
  return { cancelado: false, destino: filePath }
}

/**
 * Elige una ruta de destino sin escribir nada (SCRUM-61).
 *
 * Los reportes los genera el servicio de Python en su propio proceso, así que
 * el renderer solo necesita la ruta: pedirla con el diálogo nativo es lo que
 * mantiene al usuario eligiendo dónde queda el archivo.
 */
async function elegirDestino(ventana, { nombre, formato = 'pdf' } = {}) {
  const filtros =
    formato === 'csv'
      ? [{ name: 'Valores separados por comas', extensions: ['csv'] }]
      : FILTROS_PDF

  const { canceled, filePath } = await dialog.showSaveDialog(ventana, {
    title: 'Guardar reporte',
    defaultPath: nombre || `reporte.${formato}`,
    filters: filtros,
  })

  if (canceled || !filePath) return { cancelado: true }
  return { cancelado: false, destino: filePath }
}

module.exports = { elegirDocumento, guardarDocumento, elegirDestino }