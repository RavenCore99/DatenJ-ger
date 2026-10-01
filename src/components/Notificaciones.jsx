import { useEffect } from 'react'

import Icono from './Icono.jsx'
import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Notificaciones del sistema (SCRUM-87).
 *
 * La aplicación anterior mostraba un `Notification` —un aviso que aparece y se
 * va solo— al guardar, al fallar y al terminar una operación. Aquí es una pieza
 * del sistema de diseño: la pila vive en el proveedor de la aplicación, así que
 * cualquier pantalla puede emitir un aviso con `notificar(texto, tipo)` sin
 * dibujar nada, y esta capa los pinta y los retira.
 *
 * Se colocan sobre la franja de telemetría, a la derecha, con `aria-live` para
 * que un lector de pantalla los anuncie. Con las notificaciones silenciadas en
 * Ajustes no se pinta ninguno.
 */

/** Lo que dura un aviso en pantalla antes de retirarse solo. */
const DURACION_MS = 5200

export default function Notificaciones() {
  const { avisos, descartarAviso, notificaciones } = useApp()

  if (!notificaciones || avisos.length === 0) return null

  return (
    <div
      role="region"
      aria-label="Notificaciones"
      aria-live="polite"
      className="pointer-events-none fixed bottom-11 right-6 z-40 flex w-[22rem] max-w-[calc(100vw-3rem)] flex-col gap-2"
    >
      {avisos.map((aviso) => (
        <Tarjeta key={aviso.id} aviso={aviso} onCerrar={() => descartarAviso(aviso.id)} />
      ))}
    </div>
  )
}

const ESTILOS = {
  exito: { borde: 'border-exito/40', fondo: 'bg-exito/5', texto: 'text-exito', icono: 'check' },
  alerta: { borde: 'border-alerta/40', fondo: 'bg-alerta/5', texto: 'text-alerta', icono: 'alerta' },
  peligro: { borde: 'border-peligro/40', fondo: 'bg-peligro/5', texto: 'text-peligro', icono: 'alerta' },
  info: { borde: 'border-acento/40', fondo: 'bg-acento/5', texto: 'text-acento', icono: 'info' },
}

function Tarjeta({ aviso, onCerrar }) {
  const estilo = ESTILOS[aviso.tipo] ?? ESTILOS.exito

  // El temporizador se rearma si cambia el aviso; al desmontar se limpia, para
  // que una tarjeta retirada a mano no dispare un cierre tardío.
  useEffect(() => {
    const temporizador = setTimeout(onCerrar, DURACION_MS)
    return () => clearTimeout(temporizador)
  }, [onCerrar])

  return (
    <div
      role={aviso.tipo === 'peligro' ? 'alert' : 'status'}
      className={[
        'aparecer pointer-events-auto flex items-start gap-3 rounded-panel border px-4 py-3',
        'superficie-cristal shadow-flotante',
        estilo.borde,
        estilo.fondo,
      ].join(' ')}
    >
      <span aria-hidden="true" className={`mt-0.5 shrink-0 ${estilo.texto}`}>
        <Icono nombre={estilo.icono} tamano={16} />
      </span>

      <p className="min-w-0 flex-1 text-cuerpo-sm text-texto">{aviso.texto}</p>

      <button
        type="button"
        onClick={onCerrar}
        aria-label="Descartar la notificación"
        className="shrink-0 rounded px-1 text-tenue transition-colors hover:text-texto"
      >
        <Icono nombre="cerrar" tamano={13} />
      </button>
    </div>
  )
}