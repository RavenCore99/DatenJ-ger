import Icono from './Icono.jsx'

/**
 * Piezas de interfaz compartidas por las pantallas del sistema (Fase 3).
 *
 * `Panel` es el contenedor con cabecera y cuerpo; el resto son los estados
 * canónicos y las piezas recurrentes del sistema de diseño (tarjetas de
 * métrica, pills de estado, cabecera de página) que varias pantallas comparten
 * en lugar de reimplementar cada una.
 */

/** Contenedor de contenido: título, descripción, acciones y cuerpo. */
export default function Panel({ titulo, descripcion, acciones, children, className = '' }) {
  return (
    <section className={`rounded-panel border border-borde bg-superficie ${className}`}>
      {(titulo || acciones) && (
        <header className="flex items-center justify-between gap-4 border-b border-borde px-5 py-4">
          <div className="min-w-0">
            {titulo && <h2 className="text-titulo-sm">{titulo}</h2>}
            {descripcion && <p className="text-cuerpo-sm text-tenue">{descripcion}</p>}
          </div>
          {acciones && <div className="flex shrink-0 items-center gap-2">{acciones}</div>}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  )
}

/**
 * Cabecera de una pantalla completa: título de marca, subtítulo y acciones.
 * Es la pieza que los mockups dibujan en la parte alta del área de contenido.
 */
export function CabeceraPagina({ titulo, descripcion, acciones }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="font-marca text-titulo-md tracking-tight">{titulo}</h1>
        {descripcion && <p className="text-cuerpo-sm text-tenue">{descripcion}</p>}
      </div>
      {acciones && <div className="flex shrink-0 flex-wrap items-center gap-2">{acciones}</div>}
    </header>
  )
}

/**
 * Tarjeta de métrica (fila de KPI de los mockups). El valor va en
 * monoespaciada —telemetría del sistema— y admite un acento de color por
 * estado.
 */
export function Tarjeta({ etiqueta, valor, nota, acento = 'texto' }) {
  const colores = {
    texto: 'text-texto',
    primario: 'text-primario',
    exito: 'text-exito',
    alerta: 'text-alerta',
    peligro: 'text-peligro',
  }

  return (
    <div className="flex flex-col gap-1 rounded-panel border border-borde bg-superficie px-4 py-3">
      <p className="text-etiqueta-sm uppercase tracking-wider text-tenue">{etiqueta}</p>
      <p className={`font-mono text-titulo-md ${colores[acento] ?? colores.texto}`}>{valor ?? '—'}</p>
      {nota && <p className="text-cuerpo-sm text-tenue">{nota}</p>}
    </div>
  )
}

/** Pill de estado, coloreada por tipo. Reutilizable en tablas y paneles. */
export function Pill({ tipo = 'neutro', children, titulo }) {
  const estilos = {
    exito: 'border-exito/40 bg-exito/5 text-exito',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
    peligro: 'border-peligro/40 bg-peligro/5 text-peligro',
    info: 'border-acento/40 bg-acento/5 text-acento',
    primario: 'border-primario/40 bg-primario/5 text-primario',
    neutro: 'border-borde bg-fondo text-tenue',
  }

  return (
    <span
      title={titulo}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-etiqueta-sm font-medium ${
        estilos[tipo] ?? estilos.neutro
      }`}
    >
      {children}
    </span>
  )
}

/** Estado vacío canónico: nada que mostrar todavía, con acción sugerida. */
export function EstadoVacio({ titulo, mensaje, accion, icono = 'info' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <span
        aria-hidden="true"
        className="mb-1 flex h-11 w-11 items-center justify-center rounded-full border border-borde bg-fondo text-tenue"
      >
        <Icono nombre={icono} tamano={20} />
      </span>
      <p className="text-titulo-sm">{titulo}</p>
      {mensaje && <p className="max-w-md text-cuerpo-sm text-tenue">{mensaje}</p>}
      {accion}
    </div>
  )
}

/**
 * Estado de carga: esqueleto con la forma del contenido final.
 * `variante` elige filas de tabla, tarjetas de métrica o bloques de texto.
 */
export function Esqueleto({ filas = 4, variante = 'filas' }) {
  if (variante === 'tarjetas') {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-busy="true" aria-label="Cargando">
        {Array.from({ length: filas }, (_, indice) => (
          <div key={indice} className="flex flex-col gap-2 rounded-panel border border-borde px-4 py-3">
            <div className="h-3 w-20 animate-pulse rounded bg-fondo-2" />
            <div className="h-6 w-16 animate-pulse rounded bg-fondo-2" />
          </div>
        ))}
      </div>
    )
  }

  if (variante === 'texto') {
    return (
      <div className="flex flex-col gap-2" aria-busy="true" aria-label="Cargando">
        {Array.from({ length: filas }, (_, indice) => (
          <div
            key={indice}
            className="h-4 animate-pulse rounded bg-fondo-2"
            style={{ width: `${90 - indice * 12}%` }}
          />
        ))}
      </div>
    )
  }

  if (variante === 'tabla') {
    // Esqueleto de tabla (SCRUM-69): una franja de cabecera y filas con la
    // forma del listado real, para que el reemplazo no dé un salto visual.
    return (
      <div className="flex flex-col gap-2" aria-busy="true" aria-label="Cargando">
        <div className="mb-1 flex items-center gap-3">
          <div className="h-3 w-24 animate-pulse rounded bg-fondo-2" />
          <div className="h-3 w-40 animate-pulse rounded bg-fondo-2" />
          <div className="ml-auto h-3 w-16 animate-pulse rounded bg-fondo-2" />
        </div>
        {Array.from({ length: filas }, (_, indice) => (
          <div
            key={indice}
            className="h-9 animate-pulse rounded-lg bg-fondo-2"
            style={{ animationDelay: `${Math.min(indice, 8) * 60}ms` }}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2" aria-busy="true" aria-label="Cargando">
      {Array.from({ length: filas }, (_, indice) => (
        <div key={indice} className="h-9 animate-pulse rounded-lg bg-fondo-2" />
      ))}
    </div>
  )
}

/** Bloque de error con el mensaje real del backend. */
export function EstadoError({ mensaje, onReintentar }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-peligro/40 bg-peligro/5 px-4 py-3">
      <p className="text-titulo-sm text-peligro">No se pudo completar la operación</p>
      <p className="font-mono text-codigo text-tenue">{mensaje}</p>
      {onReintentar && (
        <button
          type="button"
          onClick={onReintentar}
          className="rounded-lg border border-borde px-3 py-1.5 text-etiqueta-sm font-medium transition-colors hover:border-primario hover:text-primario"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}

/** Aviso inline de resultado: éxito, alerta o error. */
export function Aviso({ tipo = 'exito', children, onCerrar }) {
  const estilos = {
    exito: 'border-exito/40 bg-exito/5 text-exito',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
    error: 'border-peligro/40 bg-peligro/5 text-peligro',
  }

  return (
    <div
      role={tipo === 'error' ? 'alert' : 'status'}
      className={`aparecer flex items-center justify-between gap-4 rounded-lg border px-4 py-2 text-cuerpo-sm ${
        estilos[tipo] ?? estilos.exito
      }`}
    >
      <span className="min-w-0">{children}</span>
      {onCerrar && (
        <button type="button" onClick={onCerrar} className="shrink-0 font-mono text-etiqueta-sm">
          cerrar
        </button>
      )}
    </div>
  )
}