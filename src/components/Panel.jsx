/** Contenedor de contenido: título, acciones y cuerpo. */
export default function Panel({ titulo, descripcion, acciones, children, className = '' }) {
  return (
    <section
      className={`rounded-panel border border-borde bg-superficie ${className}`}
    >
      {(titulo || acciones) && (
        <header className="flex items-center justify-between gap-4 border-b border-borde px-5 py-4">
          <div>
            {titulo && <h2 className="text-sm font-semibold">{titulo}</h2>}
            {descripcion && <p className="text-xs text-tenue">{descripcion}</p>}
          </div>
          {acciones && <div className="flex items-center gap-2">{acciones}</div>}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  )
}

/** Estado vacío canónico: nada que mostrar todavía. */
export function EstadoVacio({ titulo, mensaje, accion }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <p className="text-sm font-medium">{titulo}</p>
      {mensaje && <p className="max-w-md text-xs text-tenue">{mensaje}</p>}
      {accion}
    </div>
  )
}

/** Estado de carga: esqueleto neutro, sin saltos de layout. */
export function Esqueleto({ filas = 4 }) {
  return (
    <div className="flex flex-col gap-2" aria-busy="true">
      {Array.from({ length: filas }, (_, indice) => (
        <div
          key={indice}
          className="h-9 animate-pulse rounded-lg bg-fondo"
        />
      ))}
    </div>
  )
}

/** Bloque de error con el mensaje real del backend. */
export function EstadoError({ mensaje, onReintentar }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-peligro/40 bg-peligro/5 px-4 py-3">
      <p className="text-sm font-medium text-peligro">No se pudo completar la operación</p>
      <p className="font-mono text-xs text-tenue">{mensaje}</p>
      {onReintentar && (
        <button
          type="button"
          onClick={onReintentar}
          className="rounded-lg border border-borde px-3 py-1.5 text-xs font-medium hover:bg-fondo"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}