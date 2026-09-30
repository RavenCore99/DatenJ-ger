/** Formato de presentación: tamaños, fechas y etiquetas cortas. */

/** Tamaño legible, con la misma escala que usaba el panel de CustomTkinter. */
export function tamanoLegible(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) return '—'

  const valor = Number(bytes)
  const unidades = ['B', 'KB', 'MB', 'GB']
  let indice = 0
  let cantidad = valor

  while (cantidad >= 1024 && indice < unidades.length - 1) {
    cantidad /= 1024
    indice += 1
  }

  return `${indice === 0 ? cantidad : cantidad.toFixed(1)} ${unidades[indice]}`
}

/** Fecha y hora cortas. Acepta ISO y el formato usado por el backend. */
export function fechaCorta(valor) {
  if (!valor) return '—'

  const fecha = new Date(String(valor).replace(' ', 'T'))
  if (Number.isNaN(fecha.getTime())) return String(valor)

  return fecha.toLocaleString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Nombre del titular, con el marcador que usa el servicio cuando no hay. */
export function titular(fila) {
  const nombre = fila?.nombres?.trim()
  if (!nombre) return 'Sin titular'
  return fila.empresa?.trim() ? `${nombre} · ${fila.empresa}` : nombre
}