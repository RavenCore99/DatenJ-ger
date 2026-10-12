import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl

/** Pinta el documento en canvas: el visor PDF nativo de Electron puede quedar en blanco. */
export default function LectorPdf({ bytes }) {
  const lienzo = useRef(null)
  const contenedor = useRef(null)
  const [pdf, setPdf] = useState(null)
  const [pagina, setPagina] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [ancho, setAncho] = useState(0)
  const [error, setError] = useState(null)

  useEffect(() => {
    const tarea = getDocument({ data: bytes })
    let vigente = true
    tarea.promise.then((documento) => {
      if (vigente) setPdf(documento)
      else documento.destroy()
    }).catch((fallo) => {
      if (vigente) setError(fallo.message)
    })
    return () => {
      vigente = false
      tarea.destroy()
    }
  }, [bytes])

  useEffect(() => {
    if (!contenedor.current) return undefined
    const observador = new ResizeObserver(([entrada]) => setAncho(entrada.contentRect.width))
    observador.observe(contenedor.current)
    return () => observador.disconnect()
  }, [])

  useEffect(() => {
    if (!pdf || !ancho || !lienzo.current) return undefined
    let vigente = true
    let renderizado
    pdf.getPage(pagina).then((hoja) => {
      if (!vigente) return
      const canvas = lienzo.current
      const contexto = canvas.getContext('2d')
      const tamañoBase = hoja.getViewport({ scale: 1 })
      const escala = (Math.max(280, ancho - 32) / tamañoBase.width) * zoom
      const vista = hoja.getViewport({ scale: escala })
      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.floor(vista.width * dpr)
      canvas.height = Math.floor(vista.height * dpr)
      canvas.style.width = `${vista.width}px`
      canvas.style.height = `${vista.height}px`
      renderizado = hoja.render({ canvasContext: contexto, viewport: vista, transform: [dpr, 0, 0, dpr, 0, 0] })
      return renderizado.promise
    }).catch((fallo) => {
      if (vigente && fallo.name !== 'RenderingCancelledException') setError(fallo.message)
    })
    return () => {
      vigente = false
      renderizado?.cancel()
    }
  }, [pdf, pagina, zoom, ancho])

  if (error) return <p role="alert" className="p-6 text-peligro">No se pudo mostrar el PDF: {error}</p>

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-fondo-2">
      <div className="flex shrink-0 items-center justify-center gap-3 border-b border-borde bg-superficie px-3 py-2 text-etiqueta-sm" aria-label="Navegación del PDF">
        <button type="button" aria-label="Página anterior" disabled={!pdf || pagina === 1} onClick={() => setPagina((actual) => actual - 1)} className="rounded border border-borde px-2 py-1 disabled:opacity-40">‹</button>
        <span aria-live="polite">{pagina} / {pdf?.numPages ?? '…'}</span>
        <button type="button" aria-label="Página siguiente" disabled={!pdf || pagina === pdf.numPages} onClick={() => setPagina((actual) => actual + 1)} className="rounded border border-borde px-2 py-1 disabled:opacity-40">›</button>
        <span className="mx-1 h-5 border-l border-borde" />
        <button type="button" aria-label="Reducir PDF" disabled={zoom <= 0.5} onClick={() => setZoom((actual) => Math.max(0.5, actual - 0.25))} className="rounded border border-borde px-2 py-1 disabled:opacity-40">−</button>
        <span>{Math.round(zoom * 100)} %</span>
        <button type="button" aria-label="Ampliar PDF" disabled={zoom >= 2} onClick={() => setZoom((actual) => Math.min(2, actual + 0.25))} className="rounded border border-borde px-2 py-1 disabled:opacity-40">+</button>
      </div>
      <div ref={contenedor} className="min-h-0 flex-1 overflow-auto p-4 text-center" aria-label="Página del PDF">
        {!pdf && <p className="text-tenue">Preparando documento…</p>}
        <canvas key={`${pagina}-${zoom}-${ancho}`} ref={lienzo} className="mx-auto block bg-white shadow-lg" aria-label={`Página ${pagina} del PDF`} role="img" />
      </div>
    </div>
  )
}
