import { useEffect, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import Particulas from './Particulas.jsx'

/**
 * Intro de arranque (SCRUM-67; reelaborada por hallazgo de Raven).
 *
 * Antes era una cortina mínima con el logo que se desvanecía. Ahora **el propio
 * fondo es el protagonista**: el campo de partículas del sistema se superpone a
 * pantalla completa con el nombre **DATENJÄGER** en grande, y al cabo de un
 * instante todo se desvanece con un fundido fluido, dejando ver el fondo del
 * portal y, sobre él, las secciones de acceso y registro.
 *
 * Funciona igual en tema claro y oscuro: los colores salen de los tokens
 * (`bg-fondo`, `text-primario`) y las partículas releen la paleta del tema. Es
 * puramente decorativa —no captura el puntero, así que un clic durante el
 * fundido llega a la interfaz de debajo— y con el movimiento desactivado no
 * llega a aparecer.
 */
export default function Entrada() {
  const { animaciones } = useApp()
  const [visible, setVisible] = useState(animaciones)
  const [saliendo, setSaliendo] = useState(false)

  useEffect(() => {
    if (!animaciones) {
      setVisible(false)
      return undefined
    }

    const salida = setTimeout(() => setSaliendo(true), 1000)
    const fin = setTimeout(() => setVisible(false), 1420)
    return () => {
      clearTimeout(salida)
      clearTimeout(fin)
    }
  }, [animaciones])

  if (!visible) return null

  return (
    <div
      aria-hidden="true"
      className={[
        'pointer-events-none fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-fondo',
        saliendo ? 'entrada-salida' : '',
      ].join(' ')}
    >
      <Particulas className="absolute inset-0 h-full w-full" />

      <span className="entrada-nombre relative select-none px-6 text-center font-marca text-[13vw] font-bold tracking-tighter text-primario">
        DATENJÄGER
      </span>
    </div>
  )
}
