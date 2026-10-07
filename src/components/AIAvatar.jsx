import { useApp } from '../estado/ProveedorApp.jsx'
import siluetaClara from '../../assets/chatbot/nousresearch.png'
import siluetaOscura from '../../assets/chatbot/nousresearch_backcontrast.png'

/**
 * Avatar del asistente (hallazgo de Raven).
 *
 * El disco con la marca «IA» se sustituye por la **imagen del asistente**
 * (`assets/chatbot/`). Las dos versiones del archivo no son capricho: son la
 * misma silueta con el trazo en negro (`nousresearch.png`) y en blanco
 * (`nousresearch_backcontrast.png`), ambas con fondo **transparente**, pensadas
 * para contrastar sobre fondo claro y oscuro. Aquí se elige según el tema, así
 * que el avatar se lee bien en los dos modos.
 *
 * Mientras el modelo trabaja, el disco se rodea de un **aura difusa que late**
 * (`.asistente-aura`, en `estilos/complementos.css`), con el primario y el
 * acento del sistema. Es decorativo: con el movimiento desactivado no aparece y
 * queda el disco con su imagen, que es el estado final.
 */
export default function AIAvatar({ pensando = false, tamano = 'md', className = '' }) {
  const { tema } = useApp()
  const caja = tamano === 'lg' ? 'h-11 w-11' : 'h-9 w-9'
  const silueta = tema === 'oscuro' ? siluetaOscura : siluetaClara

  return (
    <span className={`relative flex shrink-0 items-center justify-center ${caja} ${className}`}>
      {pensando && (
        <span
          aria-hidden="true"
          className="asistente-aura absolute inset-0 rounded-full bg-gradient-to-tr from-primario via-acento to-primario blur-md"
        />
      )}

      <span className="relative z-10 flex h-full w-full items-center justify-center overflow-hidden rounded-full border border-primario/40 bg-superficie shadow-flotante">
        <img src={silueta} alt="" className="h-full w-full object-cover" />
        <span className="sr-only">Asistente</span>
      </span>
    </span>
  )
}