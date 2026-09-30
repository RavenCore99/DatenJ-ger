import { useEffect, useState } from 'react'

import logo from '../../assets/logo/logo.png'
import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Animación de entrada (SCRUM-67): una cortina mínima con la marca que se
 * desvanece al arrancar la aplicación, en la línea sobria de Hermes Desktop.
 *
 * Es puramente decorativa y no bloquea nada: se retira sola, no captura el
 * puntero —de modo que un clic durante el desvanecido llega a la interfaz de
 * debajo— y con el movimiento desactivado no llega a aparecer.
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

    const salida = setTimeout(() => setSaliendo(true), 620)
    const fin = setTimeout(() => setVisible(false), 960)
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
        'pointer-events-none fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-fondo',
        saliendo ? 'entrada-salida' : '',
      ].join(' ')}
    >
      <span className="relative flex h-20 w-20 items-center justify-center">
        <span className="entrada-anillo absolute inset-0 rounded-full ring-1 ring-primario/30" />
        <img src={logo} alt="" className="h-16 w-16 rounded-full object-contain" />
      </span>

      <p className="font-marca text-titulo-sm tracking-tight text-primario">DatenJäger</p>
    </div>
  )
}