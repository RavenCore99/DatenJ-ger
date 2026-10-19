import { animate, stagger } from 'animejs'

/** Animaciones de interacción que respetan el movimiento reducido. */

/** ¿Se permite animar? Respeta la preferencia del usuario y la del sistema. */
export function movimientoActivo() {
  if (typeof document === 'undefined') return false
  if (document.documentElement.classList.contains('sin-animacion')) return false
  return !globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
}

/**
 * Anima un elemento u elementos. Devuelve la animación o `null` si no se
 * permite (o si anime falla), de modo que quien llama no tenga que comprobarlo.
 */
export function animar(objetivo, opciones) {
  if (!objetivo) return null
  if (Array.isArray(objetivo) && objetivo.length === 0) return null
  if (!movimientoActivo()) return null

  try {
    return animate(objetivo, opciones)
  } catch {
    // Si la animación falla, la pantalla ya está en su estado final: se sigue.
    return null
  }
}

/** Entrada escalonada de un conjunto de elementos (lista, tarjetas, filas). */
export function entradaEscalonada(elementos, { retardo = 60, desde = 10 } = {}) {
  return animar(elementos, {
    opacity: [0, 1],
    translateY: [desde, 0],
    duration: 320,
    delay: stagger(retardo),
    ease: 'outQuad',
  })
}

/** Latido de confirmación al pulsar: se hunde un punto y vuelve. */
export function pulso(elemento) {
  return animar(elemento, {
    scale: [1, 0.96, 1],
    duration: 300,
    ease: 'outQuad',
  })
}