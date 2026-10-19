import { useEffect, useRef } from 'react'

/** Cierra una capa con Escape y enfoca el botón de cierre solo al montarla. */
export function useCerrarConEscape(onCerrar) {
  const cerrar = useRef(null)
  const alCerrar = useRef(onCerrar)

  // Actualizar en cada render (y no dentro del efecto) es lo que permite que la
  // suscripción sea única sin quedarse con una versión vieja del callback.
  alCerrar.current = onCerrar

  useEffect(() => {
    const alPulsar = (evento) => {
      if (evento.key === 'Escape') alCerrar.current?.()
    }

    globalThis.addEventListener('keydown', alPulsar)
    return () => globalThis.removeEventListener('keydown', alPulsar)
  }, [])

  useEffect(() => {
    cerrar.current?.focus()
  }, [])

  return cerrar
}
