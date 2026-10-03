import { useEffect, useState } from 'react'

import { movimientoActivo } from '../lib/movimiento.js'

/**
 * Estados de la burbuja del asistente mientras responde.
 *
 * 1. Espera: shimmer + puntos en pulso y la fase (Razonando…).
 * 2. Flujo: typewriter — el texto se revela carácter a carácter, con cursor.
 * 3. Cierre: cuando ya alcanzó el texto, el cursor se retira.
 *
 * El typewriter sigue hasta ponerse al día aunque el SSE ya haya cerrado:
 * si se saltara al texto completo al llegar `fin`, la escritura no se vería.
 */

const FASES = ['Razonando', 'Analizando', 'Formulando', 'Redactando']
const CADA_FASE_MS = 1400

export default function PensandoAsistente({ texto = '', enCurso = true }) {
  if (enCurso && !texto) return <EsperaConShimmer />
  return <TextoEnFlujo texto={texto} enCurso={enCurso} />
}

function Puntos({ tamano = 'h-2 w-2' }) {
  return (
    <span aria-hidden="true" className="flex items-center gap-1">
      <span className={`asistente-rebote rounded-full bg-primario ${tamano}`} />
      <span className={`asistente-rebote-2 rounded-full bg-primario ${tamano}`} />
      <span className={`asistente-rebote-3 rounded-full bg-primario ${tamano}`} />
    </span>
  )
}

function EsperaConShimmer() {
  const [fase, setFase] = useState(0)
  const anima = movimientoActivo()

  useEffect(() => {
    if (!anima) return undefined
    const temporizador = setInterval(() => {
      setFase((actual) => (actual + 1) % FASES.length)
    }, CADA_FASE_MS)
    return () => clearInterval(temporizador)
  }, [anima])

  return (
    <div role="status" aria-live="polite" className="flex min-w-[16rem] flex-col gap-3 py-0.5">
      <span className="sr-only">El asistente está preparando la respuesta</span>

      <span className="flex items-center gap-2.5">
        <Puntos />
        <span className="text-etiqueta-md font-medium text-primario">{FASES[fase]}…</span>
      </span>

      <span aria-hidden="true" className="flex flex-col gap-2">
        <BarraShimmer clase="w-56" />
        <BarraShimmer clase="w-44" retardo="180ms" />
        <BarraShimmer clase="w-52" retardo="320ms" />
      </span>
    </div>
  )
}

function BarraShimmer({ clase, retardo = '0ms' }) {
  return (
    <span className={`relative block h-3 overflow-hidden rounded-md bg-primario/20 ${clase}`}>
      <span
        className="asistente-shimmer-barra absolute inset-y-0 left-0 block w-1/2 bg-gradient-to-r from-transparent via-primario/70 to-transparent"
        style={{ animationDelay: retardo }}
      />
    </span>
  )
}

function TextoEnFlujo({ texto, enCurso }) {
  const anima = movimientoActivo()
  const [visibles, setVisibles] = useState(() => (anima ? 0 : texto.length))

  useEffect(() => {
    if (!anima) {
      setVisibles(texto.length)
      return undefined
    }

    if (visibles > texto.length) {
      setVisibles(texto.length)
      return undefined
    }

    if (visibles >= texto.length) return undefined

    const atras = texto.length - visibles
    const paso = atras > 120 ? 5 : atras > 40 ? 2 : 1
    const espera = atras > 40 ? 16 : 28
    const temporizador = setTimeout(
      () => setVisibles((n) => Math.min(n + paso, texto.length)),
      espera,
    )
    return () => clearTimeout(temporizador)
  }, [texto, visibles, anima])

  const alDia = visibles >= texto.length
  const mostrarCursor = enCurso || !alDia
  const mostrado = texto.slice(0, visibles)

  return (
    <div className="flex flex-col gap-1.5">
      {enCurso && (
        <span className="flex items-center gap-2 text-cuerpo-sm font-medium text-primario">
          <Puntos tamano="h-1.5 w-1.5" />
          Escribiendo
        </span>
      )}
      <span className="whitespace-pre-wrap">
        {mostrado}
        {mostrarCursor && (
          <span
            aria-hidden="true"
            className="asistente-cursor ml-0.5 inline-block h-4 w-[2px] translate-y-px bg-primario align-text-bottom"
          />
        )}
      </span>
    </div>
  )
}
