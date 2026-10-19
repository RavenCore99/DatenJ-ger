import { useEffect, useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import Particulas from './Particulas.jsx'

/** Muestra la animación de entrada si el movimiento está habilitado. */
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
        'pointer-events-none fixed inset-0 z-[60] flex items-center justify-center overflow-hidden bg-fondo',
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
