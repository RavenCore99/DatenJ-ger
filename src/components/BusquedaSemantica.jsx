import { useCallback, useEffect, useRef, useState } from 'react'

import Icono from './Icono.jsx'
import { backend } from '../lib/api.js'

/** Retardo antes de buscar mientras el usuario escribe la consulta semántica. */
const RETARDO_CONSULTA_MS = 400

/**
 * Búsqueda semántica (Fase 6): encuentra documentos por significado.
 *
 * El índice se construye bajo demanda sobre los documentos cifrados del
 * usuario y el modelo de embeddings corre local (CPU), así que la búsqueda no
 * depende de ninguna API externa ni se degrada si el proveedor del asistente
 * falla. El texto mostrado son fragmentos del documento, descifrados del índice
 * solo al responder la consulta.
 */
export default function BusquedaSemantica({ onVerDocumento }) {
  const [indice, setIndice] = useState(null) // null = consultando el estado
  const [consulta, setConsulta] = useState('')
  const [consultando, setConsultando] = useState(false)
  const [indexando, setIndexando] = useState(false)
  const [resultados, setResultados] = useState(null)
  const [error, setError] = useState(null)
  const temporizador = useRef(null)

  const cargarEstado = useCallback(async () => {
    try {
      setIndice(await backend.busqueda.estado())
    } catch (fallo) {
      setError(fallo.message)
    }
  }, [])

  useEffect(() => {
    cargarEstado()
  }, [cargarEstado])

  const indexar = useCallback(async () => {
    setIndexando(true)
    setError(null)
    setResultados(null)
    try {
      await backend.busqueda.indexar()
      await cargarEstado()
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setIndexando(false)
    }
  }, [cargarEstado])

  // Busca con retardo: evita una petición por pulsación.
  useEffect(() => {
    if (!(indice?.indexado) || !consulta.trim()) {
      setResultados(null)
      return undefined
    }

    clearTimeout(temporizador.current)
    setConsultando(true)
    setError(null)

    temporizador.current = setTimeout(async () => {
      try {
        const respuesta = await backend.busqueda.consultar(consulta.trim())
        setResultados(respuesta.resultados)
      } catch (fallo) {
        setError(fallo.message)
        setResultados(null)
      } finally {
        setConsultando(false)
      }
    }, RETARDO_CONSULTA_MS)

    return () => clearTimeout(temporizador.current)
  }, [consulta, indice])

  return (
    <section className="rounded-panel border border-borde bg-superficie">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-borde px-4 py-3">
        <div className="flex items-center gap-2">
          <Icono nombre="chispa" tamano={15} className="text-primario" />
          <h2 className="text-etiqueta-md font-medium">Búsqueda por significado</h2>
        </div>

        {indice && indice.indexado && (
          <span className="text-etiqueta-sm text-tenue">
            {indice.documentos} documento(s) · {indice.fragmentos} fragmento(s)
          </span>
        )}
      </header>

      <div className="flex flex-col gap-3 px-4 py-4">
        {error && (
          <p className="rounded-lg border border-peligro/40 bg-peligro/5 px-3 py-2 text-cuerpo-sm text-peligro">
            {error}
          </p>
        )}

        {indice === null && (
          <p className="text-cuerpo-sm text-tenue">Consultando el índice semántico…</p>
        )}

        {indice && !indice.indexado && (
          <div className="flex flex-col items-start gap-2">
            <p className="text-cuerpo-sm text-tenue">
              Aún no hay índice semántico. Se construye una sola vez a partir de
              tus documentos cifrados y queda en tu equipo.
            </p>
            <button
              type="button"
              onClick={indexar}
              disabled={indexando}
              className="inline-flex items-center gap-2 rounded-lg bg-primario px-3 py-2 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
            >
              <Icono nombre="carpeta" tamano={15} />
              {indexando ? 'Indexando…' : 'Indexar documentos'}
            </button>
          </div>
        )}

        {indice?.indexado && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <input
                type="search"
                value={consulta}
                onChange={(evento) => setConsulta(evento.target.value)}
                placeholder="Ej. «contratos de trabajo en altura»"
                aria-label="Búsqueda semántica"
                className="min-w-0 flex-1 rounded-lg border border-borde bg-fondo-2 px-3 py-2 text-cuerpo-md outline-none transition-colors focus:border-primario"
              />
              {consultando && (
                <span className="shrink-0 text-etiqueta-sm text-tenue">Buscando…</span>
              )}
            </div>

            {resultados !== null && (
              <ul className="flex flex-col gap-2">
                {resultados.length === 0 && (
                  <li className="text-cuerpo-sm text-tenue">
                    Sin coincidencias por significado.
                  </li>
                )}

                {resultados.map((resultado) => {
                  const texto = (resultado.texto || '')
                    .split(/\s+/)
                    .join(' ')
                    .trim()
                  const snippet = texto.length > 180 ? `${texto.slice(0, 180)}…` : texto

                  return (
                    <li
                      key={`${resultado.documento_id}-${resultado.indice}`}
                      className="flex items-start gap-3 rounded-lg border border-borde bg-fondo-2 px-3 py-2.5"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onVerDocumento?.(resultado.documento_id)}
                            className="truncate text-left font-medium text-primario transition-colors hover:text-primario-enfasis"
                            title={resultado.nombre || `Documento ${resultado.documento_id}`}
                          >
                            {resultado.nombre || `Documento ${resultado.documento_id}`}
                          </button>
                          <span className="shrink-0 rounded border border-borde px-1.5 py-0.5 font-mono text-telemetria text-tenue">
                            {Math.round(resultado.score * 100)}%
                          </span>
                        </div>
                        <p className="mt-1 text-cuerpo-sm text-tenue">{snippet || '—'}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onVerDocumento?.(resultado.documento_id)}
                        className="inline-flex shrink-0 items-center gap-1 rounded border border-borde px-2 py-1 text-etiqueta-sm transition-colors hover:border-primario hover:text-primario"
                      >
                        <Icono nombre="ojo" tamano={13} />
                        Ver
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  )
}