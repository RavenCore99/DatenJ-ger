import { useEffect, useMemo, useRef, useState } from 'react'

import Icono from './Icono.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import { animar } from '../lib/movimiento.js'

/**
 * Búsqueda global (SCRUM-85), en `Ctrl / ⌘ + F`.
 *
 * Consulta de una vez los tres corpus que el sistema tiene indexados
 * —documentos, titulares y empresas— con los mismos filtros que usan sus
 * pantallas, y lleva a la sección correspondiente al elegir un resultado. No
 * hay índice propio: se apoya en las consultas que ya existen, así que lo que
 * encuentra es exactamente lo que el backend sabe buscar.
 *
 * La auditoría queda fuera a propósito: su visor filtra por acción exacta y por
 * fechas, no por texto libre, y anunciar aquí una búsqueda que no puede hacer
 * sería mentir sobre lo que el sistema sabe.
 */

const RETARDO_MS = 250
const MINIMO_CARACTERES = 2

export default function BusquedaGlobal({ onNavegar, onCerrar }) {
  const { conectado, autenticado } = useApp()

  const panel = useRef(null)
  const [termino, setTermino] = useState('')
  const [estado, setEstado] = useState('inactivo')
  const [resultados, setResultados] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    animar(panel.current, {
      opacity: [0, 1],
      translateY: [-10, 0],
      scale: [0.99, 1],
      duration: 200,
      ease: 'outQuad',
    })
  }, [])

  useEffect(() => {
    const alPulsar = (evento) => {
      if (evento.key === 'Escape') onCerrar()
    }
    globalThis.addEventListener('keydown', alPulsar)
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [onCerrar])

  useEffect(() => {
    const buscado = termino.trim()

    if (buscado.length < MINIMO_CARACTERES) {
      setEstado('inactivo')
      setResultados(null)
      return undefined
    }

    let vigente = true
    setEstado('buscando')

    const temporizador = setTimeout(async () => {
      try {
        const [documentos, personas, empresas] = await Promise.all([
          backend.documentos.listar(buscado),
          backend.personas.listar(buscado),
          backend.empresas.listar(buscado),
        ])

        if (!vigente) return
        setResultados({ documentos, personas, empresas })
        setError(null)
        setEstado('listo')
      } catch (fallo) {
        if (!vigente) return
        setError(fallo.message)
        setEstado('error')
      }
    }, RETARDO_MS)

    return () => {
      vigente = false
      clearTimeout(temporizador)
    }
  }, [termino])

  const grupos = useMemo(() => armarGrupos(resultados), [resultados])
  const total = grupos.reduce((suma, grupo) => suma + grupo.elementos.length, 0)

  const elegir = (grupo) => {
    onNavegar?.(grupo.destino)
    onCerrar()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Búsqueda global"
      className="fixed inset-0 z-50 flex items-start justify-center px-6 pt-[12vh]"
    >
      <button
        type="button"
        aria-label="Cerrar la búsqueda"
        onClick={onCerrar}
        className="absolute inset-0 cursor-default bg-texto/40 backdrop-blur-sm"
      />

      <div
        ref={panel}
        className="superficie-cristal relative flex max-h-[70vh] w-full max-w-2xl flex-col overflow-hidden rounded-panel border border-borde shadow-flotante"
      >
        <div className="flex shrink-0 items-center gap-3 border-b border-borde px-4 py-3">
          <span aria-hidden="true" className="text-tenue">
            <Icono nombre="buscar" tamano={16} />
          </span>

          <input
            autoFocus
            type="search"
            value={termino}
            onChange={(evento) => setTermino(evento.target.value)}
            placeholder="Buscar documentos, titulares y empresas"
            aria-label="Término de búsqueda"
            className="min-w-0 flex-1 bg-transparent text-cuerpo-md outline-none"
          />

          <kbd className="shrink-0 rounded border border-borde bg-fondo px-2 py-0.5 font-mono text-codigo text-tenue">
            Esc
          </kbd>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {!conectado || !autenticado ? (
            <Mensaje texto="Sin conexión o sin sesión: la búsqueda consulta al servicio local." />
          ) : estado === 'inactivo' ? (
            <Mensaje
              texto={`Escribe al menos ${MINIMO_CARACTERES} caracteres. Se buscan documentos, titulares y empresas.`}
            />
          ) : estado === 'buscando' ? (
            <Mensaje texto="Buscando…" />
          ) : estado === 'error' ? (
            <Mensaje texto={error} tipo="peligro" />
          ) : total === 0 ? (
            <Mensaje texto={`Nada coincide con «${termino.trim()}».`} />
          ) : (
            grupos.map((grupo) => (
              <section key={grupo.clave} className="mb-2 last:mb-0">
                <h3 className="px-3 py-1.5 text-etiqueta-sm uppercase tracking-wider text-tenue">
                  {grupo.titulo} · {grupo.elementos.length}
                </h3>

                <ul className="flex flex-col">
                  {grupo.elementos.map((elemento) => (
                    <li key={`${grupo.clave}-${elemento.id}`}>
                      <button
                        type="button"
                        onClick={() => elegir(grupo)}
                        className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-fondo-2"
                      >
                        <span aria-hidden="true" className="shrink-0 text-tenue">
                          <Icono nombre={grupo.icono} tamano={15} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-cuerpo-md">{elemento.titulo}</span>
                          {elemento.detalle && (
                            <span className="block truncate text-cuerpo-sm text-tenue">
                              {elemento.detalle}
                            </span>
                          )}
                        </span>
                        <span className="shrink-0 text-etiqueta-sm text-tenue">
                          ir a {grupo.destinoTitulo}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function Mensaje({ texto, tipo = 'tenue' }) {
  return (
    <p className={`px-4 py-6 text-center text-cuerpo-sm ${tipo === 'peligro' ? 'text-peligro' : 'text-tenue'}`}>
      {texto}
    </p>
  )
}

/**
 * Convierte las tres listas en grupos listos para pintar. Se muestran los
 * primeros de cada uno: es una búsqueda para llegar a una pantalla, no para
 * recorrer un inventario entero.
 */
function armarGrupos(resultados) {
  if (!resultados) return []

  const { documentos = [], personas = [], empresas = [] } = resultados
  const LIMITE = 6

  return [
    {
      clave: 'documentos',
      titulo: 'Documentos',
      icono: 'documentos',
      destino: 'documentos',
      destinoTitulo: 'Documentos',
      elementos: documentos.slice(0, LIMITE).map((fila) => ({
        id: fila.id,
        titulo: fila.nombre,
        detalle: [fila.nombres || 'sin titular', fila.empresa].filter(Boolean).join(' · '),
      })),
    },
    {
      clave: 'personas',
      titulo: 'Titulares',
      icono: 'personas',
      destino: 'personas',
      destinoTitulo: 'Personas',
      elementos: personas.slice(0, LIMITE).map((fila) => ({
        id: fila.id,
        titulo: fila.nombres,
        detalle: [fila.cedula, fila.empresa].filter(Boolean).join(' · '),
      })),
    },
    {
      clave: 'empresas',
      titulo: 'Empresas',
      icono: 'edificio',
      destino: 'personas',
      destinoTitulo: 'Personas',
      elementos: empresas.slice(0, LIMITE).map((fila) => ({
        id: fila.id,
        titulo: fila.nombre,
        detalle: `${fila.personas ?? 0} titular(es) · ${fila.documentos ?? 0} documento(s)`,
      })),
    },
  ].filter((grupo) => grupo.elementos.length > 0)
}