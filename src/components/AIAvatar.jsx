import { useApp } from '../estado/ProveedorApp.jsx'
import siluetaClara from '../../assets/chatbot/nousresearch.png'
import siluetaOscura from '../../assets/chatbot/nousresearch_backcontrast.png'

/** Muestra el avatar del asistente según el tema y su estado. */
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