import { useEffect, useRef } from 'react'

/**
 * Comportamiento común de una capa modal: cerrarse con `Escape` y llevar el foco
 * a su botón de cierre **una sola vez**.
 *
 * Esto corrige un defecto que apareció al probar la aplicación instalada: el
 * formulario de alta de documento dejaba de aceptar texto. Se escribía un
 * carácter y el siguiente ya no llegaba al campo, así que había que volver a
 * hacer clic en la casilla. No era un problema del campo, sino del modal.
 *
 * Los tres modales del sistema (`AltaDocumento`, `ModalDocumento`,
 * `TerminosUso`) juntaban las dos responsabilidades en un mismo efecto:
 *
 *     useEffect(() => {
 *       globalThis.addEventListener('keydown', alPulsar)
 *       cerrar.current?.focus()
 *       return () => globalThis.removeEventListener('keydown', alPulsar)
 *     }, [onCerrar])
 *
 * Y los padres pasan el cierre como una función **nueva en cada render**
 * (`onCerrar={() => setAlta(false)}`). Cada pulsación re-renderiza la pantalla,
 * cambia la identidad de `onCerrar`, el efecto se vuelve a ejecutar y
 * `cerrar.current.focus()` manda el foco del campo de texto al botón de cerrar.
 * El carácter siguiente se perdía.
 *
 * Aquí se separan las dos cosas y el manejador de teclado se suscribe **una
 * sola vez**: lee la última versión del callback desde una referencia, así que
 * la identidad que use el padre deja de importar. El foco se mueve al montar, no
 * en cada render.
 *
 * @param {() => void} onCerrar se llama al pulsar `Escape`.
 * @returns {import('react').RefObject} referencia que va en el botón de cierre.
 */
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
