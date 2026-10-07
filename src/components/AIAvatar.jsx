/**
 * Avatar del asistente (hallazgo de Raven).
 *
 * Un disco con la marca «IA» que, mientras el modelo trabaja, se rodea de un
 * **aura difusa que late** (`.asistente-aura`, en `index.css`). El halo usa el
 * primario y el acento del sistema, no los colores ajenos de la referencia:
 * el asistente tiene que parecer parte de DatenJäger, no un injerto.
 *
 * Es decorativo; con el movimiento desactivado el aura no aparece y queda el
 * disco con su borde, que es el estado final.
 */
export default function AIAvatar({ pensando = false, tamano = 'md', className = '' }) {
  const caja = tamano === 'lg' ? 'h-11 w-11' : 'h-9 w-9'

  return (
    <span className={`relative flex shrink-0 items-center justify-center ${caja} ${className}`}>
      {pensando && (
        <span
          aria-hidden="true"
          className="asistente-aura absolute inset-0 rounded-full bg-gradient-to-tr from-primario via-acento to-primario blur-md"
        />
      )}

      <span className="relative z-10 flex h-full w-full items-center justify-center rounded-full border border-primario/40 bg-superficie font-marca text-etiqueta-sm font-bold tracking-tight text-primario shadow-flotante">
        IA
      </span>
    </span>
  )
}
