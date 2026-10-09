// Trazabilidad Jira: SCRUM-59 (DatenJäger — UI / UX).

import { useEffect, useState } from 'react'

import Icono from './Icono.jsx'
import { EstadoError, Esqueleto } from './Panel.jsx'
import { backend } from '../lib/api.js'
import { guardarArchivo } from '../lib/escritorio.js'

/**
 * Visor de PDF dentro de la aplicación (SCRUM-60).
 *
 * Hasta ahora los documentos se descifraban en el backend y se abrían por
 * fuera, con el programa de PDF del sistema. Aquí se descifran igual —el
 * servicio entrega los bytes— y se pintan dentro de la ventana.
 *
 * **Sin dependencias nuevas**: el PDF se convierte en un `Blob` y se entrega a
 * un `<iframe>`, que el motor de Chromium —el de Electron y el del navegador de
 * desarrollo— ya sabe renderizar. Traer `pdf.js` habría añadido una librería
 * entera para algo que la plataforma hace sola.
 *
 * El objeto URL se revoca al cerrar: los bytes descifrados no deben quedarse
 * vivos en memoria más de lo necesario.
 */
export default function VisorPdf({ documento, onCerrar }) {
  const [estado, setEstado] = useState('cargando')
  const [error, setError] = useState(null)
  const [url, setUrl] = useState(null)
  const [descargando, setDescargando] = useState(false)

  // El PDF se pide una vez por documento abierto.
  useEffect(() => {
    let vigente = true
    let creada = null

    setEstado('cargando')
    setError(null)
    setUrl(null)

    backend.documentos
      .descargar(documento.id)
      .then((descarga) => {
        if (!vigente) return

        const binario = base64ABytes(descarga.contenido_b64)
        creada = URL.createObjectURL(new Blob([binario], { type: 'application/pdf' }))
        setUrl(creada)
        setEstado('listo')
      })
      .catch((fallo) => {
        if (!vigente) return
        setError(fallo.message)
        setEstado('error')
      })

    return () => {
      vigente = false
      if (creada) URL.revokeObjectURL(creada)
    }
  }, [documento.id])

  // Cerrar con Escape, como cualquier capa modal del sistema.
  useEffect(() => {
    const alPulsar = (evento) => {
      if (evento.key === 'Escape') onCerrar()
    }
    globalThis.addEventListener('keydown', alPulsar)
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [onCerrar])

  const descargar = async () => {
    setDescargando(true)
    try {
      const descarga = await backend.documentos.descargar(documento.id)
      await guardarArchivo({ nombre: descarga.nombre, contenido_b64: descarga.contenido_b64 })
    } catch (fallo) {
      setError(fallo.message)
      setEstado('error')
    } finally {
      setDescargando(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Visor de ${documento.nombre}`}
      className="aparecer fixed inset-0 z-40 flex flex-col bg-fondo/95 backdrop-blur-sm"
    >
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-borde bg-superficie px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-borde bg-fondo text-primario">
            <Icono nombre="documentos" tamano={16} />
          </span>
          <div className="min-w-0 leading-tight">
            <p className="truncate font-medium" title={documento.nombre}>
              {documento.nombre}
            </p>
            <p className="truncate font-mono text-telemetria text-tenue">
              descifrado en memoria · AES-256-GCM
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={descargar}
            disabled={descargando}
            className="inline-flex items-center gap-1.5 rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario disabled:opacity-50"
          >
            <Icono nombre="descargar" tamano={13} />
            {descargando ? 'Guardando…' : 'Guardar copia'}
          </button>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar el visor"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-borde text-tenue transition-colors hover:border-peligro hover:text-peligro"
          >
            <Icono nombre="cerrar" tamano={16} />
          </button>
        </div>
      </header>

      {/* El área del visor ocupa todo el alto restante. El `<iframe>` es un
          elemento flex (`flex-1`) en lugar de depender de `height: 100 %`, que
          en ciertas cadenas flex puede colapsar al alto por defecto del
          elemento y dejar la página en blanco o en una franja corta. */}
      <div className="flex min-h-0 flex-1 flex-col">
        {estado === 'cargando' && (
          <div className="m-4 flex flex-1 items-center justify-center rounded-panel border border-borde bg-superficie p-6">
            <Esqueleto variante="texto" filas={8} />
          </div>
        )}

        {estado === 'error' && (
          <div className="m-4">
            <EstadoError mensaje={error} onReintentar={onCerrar} />
          </div>
        )}

        {estado === 'listo' && url && (
          <iframe
            src={`${url}#zoom=page-width`}
            title={`Documento ${documento.nombre}`}
            className="min-h-0 flex-1 w-full border-0 bg-white"
          />
        )}
      </div>
    </div>
  )
}

/** base64 → bytes, para construir el `Blob` del PDF. */
function base64ABytes(contenidoB64) {
  const binario = atob(contenidoB64)
  const bytes = new Uint8Array(binario.length)
  for (let indice = 0; indice < binario.length; indice += 1) {
    bytes[indice] = binario.charCodeAt(indice)
  }
  return bytes
}